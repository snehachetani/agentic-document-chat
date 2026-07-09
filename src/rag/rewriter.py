import os
import re

from openai import OpenAI

from src.changes.models import ChangeProposal
from src.changes.store import change_store
from src.core.text import same_normalized_text, split_sentences
from src.documents.store import get_document_store


EXTERNAL_EVIDENCE_TERMS = [
    "external",
    "evidence",
    "source",
    "sources",
    "verify",
    "fact-check",
    "fact check",
    "nasa",
    "noaa",
    "web",
    "internet",
]


def create_rewrite_proposal(
    section_id: str,
    instruction: str,
) -> ChangeProposal:
    if asks_for_external_evidence(instruction):
        raise ValueError(
            "This request asks for external evidence. That belongs to Objective 4. "
            "Objective 3 only rewrites from the existing section text."
        )

    section = get_document_store().get_section(section_id)

    proposed_text = generate_proposed_text(
        section_id=section.section_id,
        title=section.title,
        original_text=section.content,
        instruction=instruction,
    )

    if same_normalized_text(proposed_text, section.content):
        raise ValueError(
            "The generated proposal matched the current section text. "
            "Please provide a more specific rewrite instruction."
        )

    reason = generate_reason_for_change(
        section_id=section.section_id,
        instruction=instruction,
    )

    return change_store.create(
        section_id=section.section_id,
        original_text=section.content,
        proposed_text=proposed_text,
        reason_for_change=reason,
    )

def asks_for_external_evidence(instruction: str) -> bool:
    normalized = instruction.lower()
    return any(term in normalized for term in EXTERNAL_EVIDENCE_TERMS)


def generate_proposed_text(
    section_id: str,
    title: str,
    original_text: str,
    instruction: str,
) -> str:
    if not os.getenv("OPENAI_API_KEY"):
        return fallback_proposed_text(
            original_text=original_text,
            instruction=instruction,
        )

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    response = client.responses.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
        instructions=(
            "You rewrite document sections. "
            "Use only the original section text. "
            "Do not add new facts. "
            "Do not use external knowledge. "
            "Do not mention citations or sources. "
            "Return only the proposed replacement text."
        ),
        input=f"""
Section ID:
{section_id}

Section title:
{title}

Original section text:
{original_text}

User rewrite instruction:
{instruction}

Create the proposed replacement text.
""",
    )

    return response.output_text.strip()


def generate_reason_for_change(section_id: str, instruction: str) -> str:
    return (
        f"Created a pending rewrite proposal for `{section_id}` based on the user "
        f"instruction: {instruction}"
    )


def fallback_proposed_text(original_text: str, instruction: str) -> str:
    normalized = instruction.lower()
    sentences = split_sentences(original_text)

    if any(term in normalized for term in ["shorten", "make shorter"]):
        words = original_text.split()
        requested = _requested_word_count(instruction)
        target = requested or max(1, int(len(words) * 0.65))
        target = min(target, max(1, int(len(words) * 0.85)))
        return " ".join(words[:target]).rstrip(" ,;:") + "."

    if any(
        term in normalized
        for term in ["rewrite", "improve", "simplify", "make clearer", "revise", "update"]
    ):
        selected = sentences[: max(1, min(3, len(sentences) - 1))]
        return " ".join(selected)

    return original_text


def _requested_word_count(instruction: str) -> int | None:
    match = re.search(r"around\s+(\d+)\s+words?|(\d+)\s+words?", instruction.lower())
    if not match:
        return None
    value = next(group for group in match.groups() if group)
    return int(value)

