from collections import Counter
import math
import os

from src.core.text import terms
from src.documents.models import DocumentSection
from src.documents.sections import section_id_from_message
from src.documents.store import get_document_store


def resolve_section_id(message: str) -> str | None:
    explicit_section_id = section_id_from_message(message)
    if explicit_section_id:
        return explicit_section_id

    if has_openai_key():
        return resolve_section_id_with_retriever(message)

    section = best_matching_section(message)
    return section.section_id if section else None


def resolve_section_id_with_retriever(message: str) -> str | None:
    from src.rag.index import current_vector_index

    retriever = current_vector_index().as_retriever(similarity_top_k=1)
    nodes = retriever.retrieve(message)

    if not nodes:
        return None

    section_id = nodes[0].node.metadata.get("section_id")
    return str(section_id) if section_id else None


def has_openai_key() -> bool:
    return bool(os.getenv("OPENAI_API_KEY"))


def best_matching_section(message: str) -> DocumentSection | None:
    sections = get_document_store().list_sections()
    scores = local_section_scores(message, sections)

    if not scores:
        return None

    best_section, best_score = max(scores, key=lambda item: item[1])
    return best_section if best_score > 0 else None


def local_section_scores(
    message: str,
    sections: list[DocumentSection],
) -> list[tuple[DocumentSection, float]]:
    query_terms = terms(message)
    if not query_terms:
        return []

    document_terms = {
        section.section_id: set(terms(f"{section.title} {section.content}"))
        for section in sections
    }

    section_count = len(sections)
    query_counts = Counter(query_terms)

    scores: list[tuple[DocumentSection, float]] = []
    for section in sections:
        section_terms = document_terms[section.section_id]
        score = 0.0

        for term, query_count in query_counts.items():
            if term not in section_terms:
                continue

            document_frequency = sum(
                1 for values in document_terms.values() if term in values
            )
            inverse_document_frequency = math.log(
                (1 + section_count) / (1 + document_frequency)
            ) + 1
            score += query_count * inverse_document_frequency

        scores.append((section, score))

    return scores
