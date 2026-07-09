from functools import lru_cache

from llama_index.core.response_synthesizers import get_response_synthesizer

from src.core.config import settings
from src.documents.matching import best_matching_section
from src.rag.index import current_vector_index, has_openai_key, section_version_signature
from src.rag.prompts import QA_PROMPT


@lru_cache(maxsize=1)
def get_query_engine(version_signature: tuple[tuple[str, int], ...]):
    index = current_vector_index()

    response_synthesizer = get_response_synthesizer(
        response_mode="compact",
        text_qa_template=QA_PROMPT,
    )

    return index.as_query_engine(
        similarity_top_k=settings.top_k,
        response_synthesizer=response_synthesizer,
    )


def ask_document(question: str) -> dict:
    if not has_openai_key():
        return fallback_document_answer(question)

    query_engine = get_query_engine(section_version_signature())
    response = query_engine.query(question)
    source_nodes = compact_source_nodes(response.source_nodes)

    if not source_nodes:
        return {
            "answer": (
                "I could not find support for that in the document. "
                "Ask for external information explicitly if you want a web-backed answer."
            ),
            "source_nodes": [],
        }

    return {
        "answer": str(response),
        "source_nodes": source_nodes,
    }


def fallback_document_answer(question: str) -> dict:
    best = best_matching_section(question)
    if best is None:
        return {
            "answer": (
                "I could not find support for that in the document. "
                "Ask for external information explicitly if you want a web-backed answer."
            ),
            "source_nodes": [],
        }

    return {
        "answer": (
            f"The most relevant section is `{best.section_id}` ({best.title}). "
            f"From the document: {best.content}"
        ),
        "source_nodes": [
            {
                "score": None,
                "section_id": best.section_id,
                "title": best.title,
                "version": best.version,
            }
        ],
    }


def compact_source_nodes(source_nodes) -> list[dict]:
    compacted: list[dict] = []

    for node in source_nodes:
        if node.score is not None and node.score < 0.15:
            continue

        metadata = node.node.metadata
        compacted.append(
            {
                "score": node.score,
                "section_id": metadata.get("section_id"),
                "title": metadata.get("title"),
                "version": metadata.get("version"),
            }
        )

    return compacted
