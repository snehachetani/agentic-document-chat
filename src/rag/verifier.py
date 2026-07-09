import os
from urllib.parse import urlparse

from openai import OpenAI

from src.changes.models import ChangeProposal, EvidenceUsed, ToolCallTrace
from src.changes.store import change_store
from src.core.text import same_normalized_text, split_sentences
from src.documents.store import get_document_store
from src.evidence.store import tool_trace_store
from src.tools.search_client import (
    general_web_search_tool,
    nasa_search_tool,
    noaa_climate_search_tool,
)


NASA_TERMS = [
    "nasa",
    "cloud",
    "clouds",
    "radiation",
    "earth system",
    "climate",
]

NOAA_TERMS = [
    "noaa",
    "weather",
    "climate",
    "atmosphere",
    "classification",
    "long-term",
    "temperature",
]

CHANGE_TERMS = [
    "improve",
    "rewrite",
    "revise",
    "update",
    "suggest",
    "more precise",
    "better version",
]


def verify_section(
    section_id: str,
    instruction: str,
) -> dict:
    section = get_document_store().get_section(section_id)

    tool_results, tool_traces = run_evidence_tools(
        section_id=section.section_id,
        title=section.title,
        content=section.content,
        instruction=instruction,
    )

    evidence = normalize_evidence(tool_results)

    summary = generate_fact_check_summary(
        section_id=section.section_id,
        title=section.title,
        content=section.content,
        instruction=instruction,
        evidence=evidence,
    )

    return {
        "section_id": section.section_id,
        "title": section.title,
        "fact_check_summary": summary,
        "evidence_used": evidence,
        "tool_call_trace": tool_traces,
        "external_tools_used": [trace.tool_name for trace in tool_traces],
        "created_change_proposal": False,
        "change": None,
    }


def verify_and_create_change_proposal(
    section_id: str,
    instruction: str,
) -> dict:
    section = get_document_store().get_section(section_id)

    verification = verify_section(
        section_id=section_id,
        instruction=instruction,
    )

    evidence = verification["evidence_used"]
    if not evidence:
        raise RuntimeError(
            "No external evidence was retrieved, so no evidence-backed proposal was created."
        )

    proposed_text = generate_evidence_based_revision(
        section_id=section.section_id,
        title=section.title,
        original_text=section.content,
        instruction=instruction,
        evidence=evidence,
    )

    if same_normalized_text(proposed_text, section.content):
        raise RuntimeError(
            "External evidence was retrieved, but no distinct revision could be generated."
        )

    proposal = change_store.create(
        section_id=section.section_id,
        original_text=section.content,
        proposed_text=proposed_text,
        reason_for_change=(
            "Created an evidence-backed pending proposal from an external "
            f"verification request: {instruction}"
        ),
        evidence_used=evidence,
    )

    verification["created_change_proposal"] = True
    verification["change"] = proposal
    return verification


def run_evidence_tools(
    section_id: str,
    title: str,
    content: str,
    instruction: str,
) -> tuple[list[dict], list[ToolCallTrace]]:
    query = build_evidence_query(
        title=title,
        content=content,
        instruction=instruction,
    )

    selected_tools = choose_evidence_tools(f"{instruction}\n{title}")

    results: list[dict] = []
    traces: list[ToolCallTrace] = []

    for tool_name in selected_tools:
        tool_input = build_tool_input(
            tool_name=tool_name,
            query=query,
            section_id=section_id,
        )

        try:
            output = call_tool(tool_name=tool_name, tool_input=tool_input)
            result_count = len(output.get("results", []))

            trace = ToolCallTrace(
                tool_name=tool_name,
                query=query,
                input=tool_input,
                result_count=result_count,
                status="success",
            )

            results.append(
                {
                    "tool_name": tool_name,
                    "output": output,
                }
            )

        except RuntimeError as exc:
            trace = ToolCallTrace(
                tool_name=tool_name,
                query=query,
                input=tool_input,
                result_count=0,
                status="error",
                error=str(exc),
            )

        tool_trace_store.add(trace)
        traces.append(trace)

    return results, traces


def build_tool_input(
    tool_name: str,
    query: str,
    section_id: str,
) -> dict:
    if tool_name == "nasa_search_tool":
        return {
            "query": query,
            "section_id": section_id,
            "max_results": 3,
        }

    if tool_name == "noaa_climate_search_tool":
        return {
            "query": query,
            "section_id": section_id,
            "max_results": 3,
        }

    return {
        "query": query,
        "allowed_domains": ["nasa.gov", "noaa.gov"],
        "max_results": 3,
    }


def call_tool(tool_name: str, tool_input: dict) -> dict:
    if tool_name == "nasa_search_tool":
        return nasa_search_tool(**tool_input)

    if tool_name == "noaa_climate_search_tool":
        return noaa_climate_search_tool(**tool_input)

    return general_web_search_tool(**tool_input)


def choose_evidence_tools(instruction: str) -> list[str]:
    normalized = instruction.lower()

    if "nasa" in normalized and "noaa" in normalized:
        return ["nasa_search_tool", "noaa_climate_search_tool"]

    if "nasa" in normalized:
        return ["nasa_search_tool"]

    if "noaa" in normalized:
        return ["noaa_climate_search_tool"]

    if any(term in normalized for term in NOAA_TERMS):
        return ["noaa_climate_search_tool"]

    if any(term in normalized for term in NASA_TERMS):
        return ["nasa_search_tool"]

    return ["general_web_search_tool"]


def build_evidence_query(
    title: str,
    content: str,
    instruction: str,
) -> str:
    supporting_excerpt = " ".join(content.split())[:500]

    return (
        f"{instruction}\n\n"
        f"Section title: {title}\n\n"
        f"Section excerpt: {supporting_excerpt}"
    )


def normalize_evidence(tool_results: list[dict]) -> list[EvidenceUsed]:
    evidence: list[EvidenceUsed] = []

    for tool_result in tool_results:
        tool_name = tool_result["tool_name"]
        output = tool_result["output"]

        for item in output.get("results", []):
            source_url = item.get("source_url") or item.get("url", "")

            evidence.append(
                EvidenceUsed(
                    source_title=item.get("source_title") or item.get("title", ""),
                    source_url=source_url,
                    source_domain=domain_from_url(source_url),
                    supporting_text=(
                        item.get("retrieved_text")
                        or item.get("snippet")
                        or ""
                    ),
                    tool_name=tool_name,
                )
            )

    return evidence


def generate_fact_check_summary(
    section_id: str,
    title: str,
    content: str,
    instruction: str,
    evidence: list[EvidenceUsed],
) -> str:
    if not evidence or not os.getenv("OPENAI_API_KEY"):
        return fallback_fact_check_summary(
            section_id=section_id,
            evidence=evidence,
        )

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    response = client.responses.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
        instructions=(
            "You are a scientific fact-checking assistant. "
            "Use only the provided section text and external evidence. "
            "Do not add unsupported claims. "
            "Every factual conclusion must be grounded in the evidence list."
        ),
        input=f"""
Section ID:
{section_id}

Section title:
{title}

Section text:
{content}

User verification request:
{instruction}

External evidence:
{format_evidence(evidence)}

Write a concise fact-check summary. Mention the section ID and cite the source titles.
""",
    )

    return response.output_text.strip()


def generate_evidence_based_revision(
    section_id: str,
    title: str,
    original_text: str,
    instruction: str,
    evidence: list[EvidenceUsed],
) -> str:
    if not evidence:
        return original_text

    if not os.getenv("OPENAI_API_KEY"):
        return fallback_evidence_based_revision(
            original_text=original_text,
            evidence=evidence,
        )

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    response = client.responses.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
        instructions=(
            "You revise document sections using only the original section text "
            "and provided external evidence. Do not add unsupported claims. "
            "Return only the proposed replacement text."
        ),
        input=f"""
Section ID:
{section_id}

Section title:
{title}

Original section text:
{original_text}

User request:
{instruction}

External evidence:
{format_evidence(evidence)}

Create a more precise proposed replacement text.
""",
    )

    return response.output_text.strip()


def format_evidence(evidence: list[EvidenceUsed]) -> str:
    return "\n\n".join(
        (
            f"Source title: {item.source_title}\n"
            f"Source URL: {item.source_url}\n"
            f"Tool: {item.tool_name}\n"
            f"Supporting text: {item.supporting_text}"
        )
        for item in evidence
    )


def fallback_fact_check_summary(
    section_id: str,
    evidence: list[EvidenceUsed],
) -> str:
    if not evidence:
        return (
            f"No external evidence was retrieved for `{section_id}`. "
            "The section could not be verified."
        )

    source_list = ", ".join(item.source_title for item in evidence)

    return (
        f"External evidence was retrieved for `{section_id}` from: "
        f"{source_list}. See `evidence_used` for source URLs and supporting text."
    )


def domain_from_url(url: str) -> str:
    return urlparse(url).netloc


def fallback_evidence_based_revision(
    original_text: str,
    evidence: list[EvidenceUsed],
) -> str:
    evidence_sentences: list[str] = []

    for item in evidence:
        evidence_sentences.extend(split_sentences(item.supporting_text))

    for sentence in evidence_sentences:
        if sentence.lower() not in original_text.lower():
            return f"{original_text.rstrip()} {sentence}"

    return original_text


def asks_for_evidence_based_change(message: str) -> bool:
    normalized = message.lower()
    return any(term in normalized for term in CHANGE_TERMS)


def is_verification_request(message: str) -> bool:
    normalized = message.lower()

    return any(
        term in normalized
        for term in [
            "verify",
            "fact-check",
            "fact check",
            "check if",
            "accurate",
            "evidence",
            "source",
            "sources",
            "nasa",
            "noaa",
            "external",
        ]
    )
