from pydantic import BaseModel
from fastapi import APIRouter, HTTPException

from src.changes.diff import build_text_diff
from src.changes.store import InvalidChangeStateError, StaleChangeError, change_store
from src.core.config import settings
from src.documents.matching import resolve_section_id
from src.documents.store import get_document_store
from src.rag.intent import classify_chat_intent
from src.rag.section_lookup import answer_section_lookup, is_section_lookup_request

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    document_id: str = "clouds_doc_v1"
    message: str


class ChatResponse(BaseModel):
    answer: str
    document_id: str
    external_tools_used: list[str]
    sources: list[dict] = []
    evidence_used: list[dict] = []
    tool_call_trace: list[dict] = []
    created_change_proposal: bool = False
    change_id: str | None = None


@router.post("", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    if request.document_id != settings.document_id:
        raise HTTPException(status_code=404, detail="Document not found")

    classified_intent = classify_chat_intent(request.message)

    if classified_intent.intent == "section_lookup" or is_section_lookup_request(request.message):
        result = answer_section_lookup(request.message)

        return ChatResponse(
            answer=result["answer"],
            document_id=request.document_id,
            external_tools_used=[],
            sources=result["sources"],
            created_change_proposal=False,
        )

    if classified_intent.intent in {"compare_change", "accept_change", "reject_change"}:
        return handle_change_review_intent(
            intent=classified_intent.intent,
            document_id=request.document_id,
            change_id=classified_intent.change_id,
        )

    if classified_intent.intent in {"verify", "verify_and_rewrite"}:
        from src.rag.verifier import (
            verify_and_create_change_proposal,
            verify_section,
        )

        section_id = resolve_existing_section_id(
            classified_intent.section_id,
            request.message,
        )

        if not section_id:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Please specify a section for verification, "
                    "for example @clouds_climate_change."
                ),
            )

        try:
            if classified_intent.intent == "verify_and_rewrite":
                result = verify_and_create_change_proposal(
                    section_id=section_id,
                    instruction=request.message,
                )
            else:
                result = verify_section(
                    section_id=section_id,
                    instruction=request.message,
                )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

        change = result["change"]

        return ChatResponse(
            answer=result["fact_check_summary"],
            document_id=request.document_id,
            external_tools_used=result["external_tools_used"],
            sources=[
                {
                    "section_id": result["section_id"],
                    "title": result["title"],
                }
            ],
            evidence_used=[
                item.model_dump() for item in result["evidence_used"]
            ],
            tool_call_trace=[
                item.model_dump() for item in result["tool_call_trace"]
            ],
            created_change_proposal=result["created_change_proposal"],
            change_id=change.change_id if change else None,
        )

    if classified_intent.intent == "rewrite":
        from src.rag.rewriter import create_rewrite_proposal

        section_id = resolve_existing_section_id(
            classified_intent.section_id,
            request.message,
        )

        if not section_id:
            raise HTTPException(
                status_code=400,
                detail="Please specify a section, for example @cloud_formation.",
            )

        try:
            proposal = create_rewrite_proposal(
                section_id=section_id,
                instruction=request.message,
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        return ChatResponse(
            answer=(
                f"Created pending change proposal `{proposal.change_id}` for "
                f"`{proposal.section_id}`. The section text was not modified."
            ),
            document_id=request.document_id,
            external_tools_used=[],
            sources=[
                {
                    "section_id": proposal.section_id,
                    "source": "DOCUMENT.md",
                }
            ],
            created_change_proposal=True,
            change_id=proposal.change_id,
        )

    if classified_intent.intent == "summary":
        from src.rag.summarizer import summarize_section

        section_id = resolve_existing_section_id(
            classified_intent.section_id,
            request.message,
        )

        if not section_id:
            raise HTTPException(
                status_code=400,
                detail="Please specify a section, for example @cloud_classification.",
            )

        result = summarize_section(
            section_id=section_id,
            instruction=request.message,
        )

        return ChatResponse(
            answer=result["summary"],
            document_id=request.document_id,
            external_tools_used=[],
            sources=[
                {
                    "section_id": result["section_id"],
                    "title": result["title"],
                }
            ],
            created_change_proposal=False,
        )

    if classified_intent.intent == "unsupported":
        return ChatResponse(
            answer=(
                "I cannot safely handle that request for this document. "
                "Try asking a document question, requesting a section summary, "
                "or creating/reviewing a change proposal."
            ),
            document_id=request.document_id,
            external_tools_used=[],
            created_change_proposal=False,
        )

    from src.rag.engine import ask_document

    result = ask_document(request.message)

    return ChatResponse(
        answer=result["answer"],
        document_id=request.document_id,
        external_tools_used=[],
        sources=result["source_nodes"],
        created_change_proposal=False,
    )


def resolve_existing_section_id(
    candidate_section_id: str | None,
    message: str,
) -> str | None:
    if candidate_section_id:
        try:
            get_document_store().get_section(candidate_section_id)
            return candidate_section_id
        except KeyError:
            pass

    return resolve_section_id(message)


def handle_change_review_intent(
    intent: str,
    document_id: str,
    change_id: str | None,
) -> ChatResponse:
    if not change_id:
        raise HTTPException(
            status_code=400,
            detail="Please specify a change ID, for example change_001.",
        )

    try:
        if intent == "compare_change":
            proposal = change_store.get(change_id)
            diff = build_text_diff(
                original_text=proposal.original_text,
                proposed_text=proposal.proposed_text,
            )
            return ChatResponse(
                answer=(
                    f"Comparison for `{proposal.change_id}` on `{proposal.section_id}`:\n\n"
                    f"{diff}"
                ),
                document_id=document_id,
                external_tools_used=[],
                created_change_proposal=False,
                change_id=proposal.change_id,
            )

        if intent == "accept_change":
            proposal, new_version = change_store.accept(change_id)
            return ChatResponse(
                answer=(
                    f"Accepted `{proposal.change_id}` for `{proposal.section_id}`. "
                    f"The section is now version {new_version}."
                ),
                document_id=document_id,
                external_tools_used=[],
                created_change_proposal=False,
                change_id=proposal.change_id,
            )

        proposal = change_store.reject(change_id)
        return ChatResponse(
            answer=(
                f"Rejected `{proposal.change_id}` for `{proposal.section_id}`. "
                "The section text was not modified."
            ),
            document_id=document_id,
            external_tools_used=[],
            created_change_proposal=False,
            change_id=proposal.change_id,
        )

    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (InvalidChangeStateError, StaleChangeError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
