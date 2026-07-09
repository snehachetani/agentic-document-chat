from dataclasses import dataclass
from pathlib import Path

from markdown_it import MarkdownIt

from src.core.config import settings


@dataclass(frozen=True)
class Section:
    section_id: str
    title: str
    content: str


def load_sections(path: Path = settings.document_path) -> dict[str, Section]:
    tokens = MarkdownIt("commonmark").parse(path.read_text(encoding="utf-8"))

    sections: dict[str, Section] = {}
    i = 0

    while i < len(tokens):
        if _is_section_heading(tokens, i):
            section_id = _first_inline_code(tokens[i + 1])
            block_tokens = []
            i += 3

            while i < len(tokens) and not _is_next_section(tokens, i):
                block_tokens.append(tokens[i])
                i += 1

            title, content = _section_text(block_tokens)
            sections[section_id] = Section(section_id, title, content)
            continue

        i += 1

    return sections


def get_section(section_id: str) -> Section:
    sections = load_sections()

    if section_id not in sections:
        raise KeyError(f"Unknown section_id: {section_id}")

    return sections[section_id]


def section_id_from_message(message: str) -> str | None:
    for word in message.split():
        if word.startswith("@"):
            return word[1:].strip(".,:;!?")
    return None


def _is_section_heading(tokens, index: int) -> bool:
    return (
        tokens[index].type == "heading_open"
        and tokens[index].tag == "h2"
        and index + 1 < len(tokens)
        and tokens[index + 1].type == "inline"
        and tokens[index + 1].content.startswith("Section:")
    )


def _is_next_section(tokens, index: int) -> bool:
    return tokens[index].type == "heading_open" and tokens[index].tag == "h2"


def _first_inline_code(token) -> str:
    for child in token.children or []:
        if child.type == "code_inline":
            return child.content
    raise ValueError("Expected inline code value in DOCUMENT.md")


def _section_text(tokens) -> tuple[str, str]:
    title = ""
    body: list[str] = []

    for token in tokens:
        if token.type != "inline":
            continue

        if token.content.startswith("Title:"):
            title = _first_inline_code(token)
        elif token.content.strip():
            body.append(token.content.strip())

    return title, "\n\n".join(body)