import json
import os
import re
from dataclasses import dataclass
from typing import Any

from openai import OpenAI

from src.documents.matching import local_section_scores
from src.documents.models import DocumentSection
from src.documents.store import get_document_store


@dataclass(frozen=True)
class SectionCandidate:
    section: DocumentSection
    score: float | None


def is_section_lookup_request(message: str) -> bool:
    normalized = message.lower()
    return any(
        phrase in normalized
        for phrase in [
            "which section",
            "what section",
            "where does it talk about",
            "where is",
        ]
    )


def answer_section_lookup(message: str) -> dict:
    candidates = retrieve_section_candidates(message=message, top_k=5)

    if not candidates:
        return {
            "answer": "I could not identify a matching section in the document.",
            "primary_section_id": None,
            "related_section_ids": [],
            "sources": [],
        }

    if has_openai_key():
        result = rerank_sections_with_llm(message=message, candidates=candidates)
    else:
        result = fallback_lookup_result(message=message, candidates=candidates)

    selected_candidates = ordered_selected_candidates(
        result=result,
        candidates=candidates,
    )

    return {
        **result,
        "sources": [
            {
                "section_id": candidate.section.section_id,
                "title": candidate.section.title,
                "version": candidate.section.version,
                "score": candidate.score,
            }
            for candidate in selected_candidates
        ],
    }


def retrieve_section_candidates(message: str, top_k: int) -> list[SectionCandidate]:
    if has_openai_key():
        return retrieve_section_candidates_with_llamaindex(message=message, top_k=top_k)

    sections = get_document_store().list_sections()
    return [
        SectionCandidate(section=section, score=score)
        for section, score in sorted(
            local_section_scores(message, sections),
            key=lambda item: item[1],
            reverse=True,
        )
        if score > 0
    ][:top_k]


def retrieve_section_candidates_with_llamaindex(
    message: str,
    top_k: int,
) -> list[SectionCandidate]:
    from src.rag.index import current_vector_index

    retriever = current_vector_index().as_retriever(similarity_top_k=top_k)
    nodes = retriever.retrieve(message)
    store = get_document_store()

    candidates: list[SectionCandidate] = []
    seen_section_ids: set[str] = set()

    for node in nodes:
        section_id = node.node.metadata.get("section_id")
        if not section_id or section_id in seen_section_ids:
            continue

        try:
            candidates.append(
                SectionCandidate(
                    section=store.get_section(str(section_id)),
                    score=node.score,
                )
            )
            seen_section_ids.add(str(section_id))
        except KeyError:
            continue

    return candidates


def has_openai_key() -> bool:
    return bool(os.getenv("OPENAI_API_KEY"))


def rerank_sections_with_llm(
    message: str,
    candidates: list[SectionCandidate],
) -> dict:
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    candidate_payload = [
        {
            "section_id": candidate.section.section_id,
            "title": candidate.section.title,
            "content": candidate.section.content,
            "retrieval_score": candidate.score,
        }
        for candidate in candidates
    ]

    response = client.responses.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
        instructions=(
            "You select document sections for section-lookup questions. "
            "Choose only from the provided candidate section IDs. "
            "The primary_section_id must be the section that most directly answers "
            "the user's intent, not necessarily the section with the closest title. "
            "For questions like 'which section talks about X', prefer the section "
            "that defines or explains X over a section that only mentions X. "
            "related_section_ids should include only sections that directly help "
            "answer the user's question; omit broad or incidental matches. "
            "Return at most two related_section_ids. "
            "Return JSON only with keys: answer, primary_section_id, related_section_ids."
        ),
        input=json.dumps(
            {
                "user_message": message,
                "candidate_sections": candidate_payload,
            }
        ),
    )

    return validate_lookup_result(
        raw_result=parse_json_object(response.output_text),
        candidates=candidates,
        message=message,
    )


def validate_lookup_result(
    raw_result: dict[str, Any],
    candidates: list[SectionCandidate],
    message: str,
) -> dict:
    candidate_ids = {candidate.section.section_id for candidate in candidates}
    primary_section_id = raw_result.get("primary_section_id")

    if primary_section_id not in candidate_ids:
        return fallback_lookup_result(message=message, candidates=candidates)

    related_section_ids = [
        section_id
        for section_id in raw_result.get("related_section_ids", [])
        if section_id in candidate_ids and section_id != primary_section_id
    ][:2]

    answer = str(raw_result.get("answer") or "").strip()
    if not answer:
        primary = next(
            candidate.section
            for candidate in candidates
            if candidate.section.section_id == primary_section_id
        )
        answer = f"The main section is `{primary.section_id}`: {primary.title}."

    return {
        "answer": answer,
        "primary_section_id": primary_section_id,
        "related_section_ids": related_section_ids,
    }


def ordered_selected_candidates(
    result: dict,
    candidates: list[SectionCandidate],
) -> list[SectionCandidate]:
    by_id = {
        candidate.section.section_id: candidate
        for candidate in candidates
    }
    ordered_ids = [
        result["primary_section_id"],
        *result["related_section_ids"],
    ]

    return [
        by_id[section_id]
        for section_id in ordered_ids
        if section_id in by_id
    ]


def fallback_lookup_result(
    message: str,
    candidates: list[SectionCandidate],
) -> dict:
    primary = candidates[0].section
    related = [candidate.section.section_id for candidate in candidates[1:2]]

    return {
        "answer": build_fallback_answer(primary=primary, related_section_ids=related),
        "primary_section_id": primary.section_id,
        "related_section_ids": related,
    }


def build_fallback_answer(
    primary: DocumentSection,
    related_section_ids: list[str],
) -> str:
    answer = f"The main section is `{primary.section_id}`: {primary.title}."
    if related_section_ids:
        related = ", ".join(f"`{section_id}`" for section_id in related_section_ids)
        answer += f" Related section(s): {related}."
    return answer


def parse_json_object(text: str) -> dict[str, Any]:
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.S)
        if not match:
            return {}
        try:
            parsed = json.loads(match.group(0))
        except json.JSONDecodeError:
            return {}

    return parsed if isinstance(parsed, dict) else {}
