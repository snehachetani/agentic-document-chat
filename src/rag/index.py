from functools import lru_cache
import os

from llama_index.core import Document, Settings as LlamaSettings
from llama_index.core import VectorStoreIndex
from llama_index.core.node_parser import MarkdownNodeParser
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.openai import OpenAI

from src.core.config import settings
from src.documents.store import get_document_store


def has_openai_key() -> bool:
    return bool(os.getenv("OPENAI_API_KEY"))


def configure_llamaindex() -> None:
    LlamaSettings.llm = OpenAI(model=settings.llm_model)
    LlamaSettings.embed_model = OpenAIEmbedding(model=settings.embedding_model)


@lru_cache(maxsize=1)
def get_vector_index(version_signature: tuple[tuple[str, int], ...]) -> VectorStoreIndex:
    configure_llamaindex()
    documents = load_documents()
    nodes = build_nodes(documents)
    return VectorStoreIndex(nodes)


def current_vector_index() -> VectorStoreIndex:
    return get_vector_index(section_version_signature())


def section_version_signature() -> tuple[tuple[str, int], ...]:
    return tuple(
        (section.section_id, section.version)
        for section in get_document_store().list_sections()
    )


def load_documents() -> list[Document]:
    sections = get_document_store().list_sections()

    return [
        Document(
            text=(
                f"Section ID: {section.section_id}\n"
                f"Title: {section.title}\n\n"
                f"{section.content}"
            ),
            metadata={
                "section_id": section.section_id,
                "title": section.title,
                "version": section.version,
            },
        )
        for section in sections
    ]


def build_nodes(documents: list[Document]):
    parser = MarkdownNodeParser()
    return parser.get_nodes_from_documents(documents)
