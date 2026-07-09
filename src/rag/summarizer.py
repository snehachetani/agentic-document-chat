import os
import re

from llama_index.core import Document, SummaryIndex
from llama_index.core import Settings as LlamaSettings
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.openai import OpenAI

from src.core.config import settings
from src.core.text import split_sentences
from src.documents.models import DocumentSection
from src.documents.store import get_document_store


def summarize_section(
    section_id: str,
    instruction: str | None = None,
) -> dict:
    section = get_document_store().get_section(section_id)

    query = instruction or (
        f"Summarize section `{section.section_id}` clearly and concisely."
    )

    if os.getenv("OPENAI_API_KEY"):
        configure_llamaindex()
        index = build_summary_index(section)
        query_engine = index.as_query_engine(response_mode="tree_summarize")

        summary = str(
            query_engine.query(_summary_prompt(section=section, instruction=query))
        )
    else:
        summary = fallback_summary(section=section, instruction=query)

    return {
        "section_id": section.section_id,
        "title": section.title,
        "summary": summary,
        "external_tools_used": [],
        "created_change_proposal": False,
    }


def configure_llamaindex() -> None:
    LlamaSettings.llm = OpenAI(model=settings.llm_model)
    LlamaSettings.embed_model = OpenAIEmbedding(model=settings.embedding_model)


def build_summary_index(section: DocumentSection) -> SummaryIndex:
    document = Document(
        text=section.content,
        metadata={
            "section_id": section.section_id,
            "title": section.title,
        },
    )

    return SummaryIndex.from_documents([document])


def _summary_prompt(section: DocumentSection, instruction: str) -> str:
    return f"""
Summarize only the document section below.

Rules:
- Use only this section text.
- Do not use external knowledge.
- Do not call external search tools.
- Do not create or suggest a document change proposal.
- Mention the section ID used: {section.section_id}.

Section title:
{section.title}

Section text:
{section.content}

User instruction:
{instruction}
"""


def fallback_summary(section: DocumentSection, instruction: str) -> str:
    sentences = split_sentences(section.content)
    requested_bullets = _requested_bullet_count(instruction)

    if requested_bullets:
        selected = sentences[:requested_bullets]
        return "\n".join(f"- {sentence}" for sentence in selected)

    return (
        f"Summary of `{section.section_id}`: "
        + " ".join(sentences[: min(3, len(sentences))])
    )


def _requested_bullet_count(instruction: str) -> int | None:
    match = re.search(r"(\d+)\s+bullets?", instruction.lower())
    if not match:
        return None
    return max(1, min(int(match.group(1)), 5))
