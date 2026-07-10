from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException

from src.api.changes import (
    CreateChangeRequest,
    accept_change,
    compare_change,
    create_change,
    reject_change,
)
from src.api.chat import ChatRequest, chat
from src.api.documents import get_section, get_section_history, list_sections
from src.api.evidence import list_tool_calls
from src.api.verification import VerifySectionRequest, verify
from src.core.config import settings
from src.db.bootstrap import bootstrap_database
from src.db.session import configure_database


@dataclass
class EvaluationContext:
    document_id: str
    rewrite_change_id: str | None = None
    audience_change_id: str | None = None


class Evaluation:
    def __init__(self) -> None:
        self.passed = 0
        self.failed = 0

    def check(self, name: str, condition: bool, detail: dict | str) -> None:
        status = "PASS" if condition else "FAIL"
        self.passed += int(condition)
        self.failed += int(not condition)

        print(f"\n[{status}] {name}")
        print(detail)

    def finish(self) -> None:
        total = self.passed + self.failed
        print("\n=== Sample Request Evaluation Summary ===")
        print({"passed": self.passed, "failed": self.failed, "total": total})

        if self.failed:
            raise SystemExit(1)


def main() -> None:
    configure_isolated_database()
    context = EvaluationContext(document_id=settings.document_id)
    evaluator = Evaluation()

    run_document_checks(evaluator, context)
    run_summary_checks(evaluator, context)
    run_change_proposal_checks(evaluator, context)
    run_change_review_checks(evaluator, context)
    run_verification_checks(evaluator, context)
    run_negative_case_checks(evaluator, context)
    run_trace_checks(evaluator, context)

    evaluator.finish()


def configure_isolated_database() -> None:
    database_path = Path("src/data") / f"sample_requests_{uuid4().hex}.db"
    configure_database(f"sqlite:///{database_path.as_posix()}")
    bootstrap_database(settings.document_path)


def run_document_checks(
    evaluator: Evaluation,
    context: EvaluationContext,
) -> None:
    check_section_listing(evaluator, context)
    check_document_qa(evaluator, context)
    check_section_lookup(evaluator, context)


def check_section_listing(
    evaluator: Evaluation,
    context: EvaluationContext,
) -> None:
    sections = list_sections(context.document_id)
    evaluator.check(
        "List document sections",
        len(sections.sections) == 7,
        {"section_count": len(sections.sections)},
    )


def check_document_qa(
    evaluator: Evaluation,
    context: EvaluationContext,
) -> None:
    response = chat(
        ChatRequest(
            document_id=context.document_id,
            message="Explain @cloud_formation in simple words.",
        )
    )

    evaluator.check(
        "Document Q&A uses section and no external tools",
        has_source(response.sources, "cloud_formation")
        and not response.external_tools_used
        and not response.created_change_proposal,
        {"answer": response.answer, "sources": response.sources},
    )


def check_section_lookup(
    evaluator: Evaluation,
    context: EvaluationContext,
) -> None:
    response = chat(
        ChatRequest(
            document_id=context.document_id,
            message="Which section talks about condensation?",
        )
    )

    evaluator.check(
        "Section lookup identifies cloud_formation",
        has_source(response.sources, "cloud_formation")
        and not response.external_tools_used
        and not response.created_change_proposal,
        {"answer": response.answer, "sources": response.sources},
    )


def run_summary_checks(
    evaluator: Evaluation,
    context: EvaluationContext,
) -> None:
    response = chat(
        ChatRequest(
            document_id=context.document_id,
            message="Summarize @cloud_classification in 3 bullets.",
        )
    )

    evaluator.check(
        "Summary does not create proposal or use external tools",
        "cloud" in response.answer.lower()
        and not response.external_tools_used
        and not response.created_change_proposal,
        {"answer": response.answer},
    )


def run_change_proposal_checks(
    evaluator: Evaluation,
    context: EvaluationContext,
) -> None:
    context.rewrite_change_id = check_shorten_proposal(evaluator, context)
    context.audience_change_id = check_audience_proposal(evaluator, context)


def check_shorten_proposal(
    evaluator: Evaluation,
    context: EvaluationContext,
) -> str:
    before = get_section(context.document_id, "cloud_formation")
    response = create_change(
        document_id=context.document_id,
        section_id="cloud_formation",
        request=CreateChangeRequest(
            instruction="Shorten @cloud_formation to around 100 words."
        ),
    )
    after = get_section(context.document_id, "cloud_formation")

    evaluator.check(
        "Rewrite creates pending proposal without modifying section",
        str(response.change.status) == "pending"
        and before.content == after.content
        and not response.section_was_modified,
        {
            "change_id": response.change.change_id,
            "status": response.change.status,
        },
    )

    return response.change.change_id


def check_audience_proposal(
    evaluator: Evaluation,
    context: EvaluationContext,
) -> str:
    response = create_change(
        document_id=context.document_id,
        section_id="cloud_classification",
        request=CreateChangeRequest(
            instruction="Rewrite @cloud_classification for a middle-school audience."
        ),
    )

    evaluator.check(
        "Audience rewrite creates proposal and preserves original",
        str(response.change.status) == "pending"
        and bool(response.change.original_text)
        and bool(response.change.proposed_text),
        {
            "change_id": response.change.change_id,
            "reason": response.change.reason_for_change,
        },
    )

    return response.change.change_id


def run_change_review_checks(
    evaluator: Evaluation,
    context: EvaluationContext,
) -> None:
    if not context.rewrite_change_id or not context.audience_change_id:
        evaluator.check(
            "Change review prerequisites",
            False,
            "Expected change IDs from proposal checks.",
        )
        return

    check_compare_change(evaluator, context, context.rewrite_change_id)
    check_accept_change(evaluator, context, context.rewrite_change_id)
    check_reject_change(evaluator, context, context.audience_change_id)


def check_compare_change(
    evaluator: Evaluation,
    context: EvaluationContext,
    change_id: str,
) -> None:
    response = compare_change(context.document_id, change_id)
    evaluator.check(
        "Compare returns original, proposed, and diff",
        bool(response.original_text)
        and bool(response.proposed_text)
        and "--- original" in response.diff,
        {
            "change_id": response.change_id,
            "diff_preview": response.diff[:500],
        },
    )


def check_accept_change(
    evaluator: Evaluation,
    context: EvaluationContext,
    change_id: str,
) -> None:
    accepted = accept_change(context.document_id, change_id)
    history = get_section_history(context.document_id, "cloud_formation")

    evaluator.check(
        "Accept applies proposal and preserves history",
        accepted.status == "accepted"
        and accepted.new_version == 2
        and len(history.versions) == 2
        and history.versions[-1].is_current,
        {
            "accepted": accepted.model_dump(),
            "history_count": len(history.versions),
        },
    )


def check_reject_change(
    evaluator: Evaluation,
    context: EvaluationContext,
    change_id: str,
) -> None:
    rejected = reject_change(context.document_id, change_id)
    current = get_section(context.document_id, "cloud_classification")

    evaluator.check(
        "Reject keeps section unchanged",
        rejected.status == "rejected" and current.version == 1,
        rejected.model_dump(),
    )


def run_verification_checks(
    evaluator: Evaluation,
    context: EvaluationContext,
) -> None:
    check_verify_without_proposal(evaluator, context)
    check_verify_with_proposal(evaluator, context)
    check_evidence_without_explicit_section(evaluator, context)


def check_verify_without_proposal(
    evaluator: Evaluation,
    context: EvaluationContext,
) -> None:
    response = verify(
        document_id=context.document_id,
        section_id="cloud_classification",
        request=VerifySectionRequest(
            instruction="Check if @cloud_classification is accurate using external sources."
        ),
    )

    evaluator.check(
        "Verification returns evidence and no proposal",
        bool(response.external_tools_used)
        and bool(response.evidence_used)
        and not response.created_change_proposal,
        {
            "tools": response.external_tools_used,
            "evidence_count": len(response.evidence_used),
        },
    )


def check_verify_with_proposal(
    evaluator: Evaluation,
    context: EvaluationContext,
) -> None:
    response = verify(
        document_id=context.document_id,
        section_id="clouds_climate_change",
        request=VerifySectionRequest(
            instruction=(
                "Review @clouds_climate_change using NASA or NOAA sources "
                "and suggest a more precise version."
            )
        ),
    )

    evaluator.check(
        "Evidence-backed update creates pending proposal with evidence",
        response.created_change_proposal
        and response.change is not None
        and str(response.change.status) == "pending"
        and bool(response.evidence_used),
        {
            "change_id": response.change.change_id if response.change else None,
            "evidence_count": len(response.evidence_used),
        },
    )


def check_evidence_without_explicit_section(
    evaluator: Evaluation,
    context: EvaluationContext,
) -> None:
    response = chat(
        ChatRequest(
            document_id=context.document_id,
            message="Find evidence for the claim that clouds affect climate.",
        )
    )

    evaluator.check(
        "Evidence request without section finds climate section",
        bool(response.external_tools_used)
        and bool(response.evidence_used)
        and has_source(response.sources, "clouds_climate_change"),
        {"tools": response.external_tools_used, "sources": response.sources},
    )


def run_negative_case_checks(
    evaluator: Evaluation,
    context: EvaluationContext,
) -> None:
    check_missing_change(evaluator, context)
    check_repeat_accept(evaluator, context)
    check_outside_document_question(evaluator, context)


def check_missing_change(
    evaluator: Evaluation,
    context: EvaluationContext,
) -> None:
    ok, detail = expect_http_error(
        lambda: accept_change(context.document_id, "change_999"),
        expected_status_code=404,
    )
    evaluator.check("Missing change returns clear 404", ok, detail)


def check_repeat_accept(
    evaluator: Evaluation,
    context: EvaluationContext,
) -> None:
    if not context.rewrite_change_id:
        evaluator.check(
            "Accepting same change twice returns conflict",
            False,
            "Missing accepted rewrite change ID.",
        )
        return

    ok, detail = expect_http_error(
        lambda: accept_change(context.document_id, context.rewrite_change_id),
        expected_status_code=409,
    )
    evaluator.check("Accepting same change twice returns conflict", ok, detail)


def check_outside_document_question(
    evaluator: Evaluation,
    context: EvaluationContext,
) -> None:
    response = chat(
        ChatRequest(
            document_id=context.document_id,
            message="What is CRISPR-Cas9?",
        )
    )

    evaluator.check(
        "Outside-document question does not call external tools",
        "could not find support" in response.answer.lower()
        and not response.external_tools_used
        and not response.sources,
        {"answer": response.answer},
    )


def run_trace_checks(
    evaluator: Evaluation,
    context: EvaluationContext,
) -> None:
    traces = list_tool_calls(context.document_id)
    evaluator.check(
        "Tool traces are persisted",
        bool(traces.tool_call_trace),
        {"trace_count": len(traces.tool_call_trace)},
    )


def expect_http_error(
    operation,
    expected_status_code: int,
) -> tuple[bool, dict | str]:
    try:
        operation()
    except HTTPException as exc:
        return (
            exc.status_code == expected_status_code,
            {"status_code": exc.status_code, "detail": exc.detail},
        )

    return False, "Unexpected success"


def has_source(sources: list[dict], section_id: str) -> bool:
    return any(source.get("section_id") == section_id for source in sources)


if __name__ == "__main__":
    main()
