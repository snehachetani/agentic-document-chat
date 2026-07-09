import json
import os
import re
from typing import Literal

from openai import OpenAI
from pydantic import BaseModel, Field

from src.core.config import settings
from src.documents.sections import section_id_from_message


IntentName = Literal[
    "qa",
    "section_lookup",
    "summary",
    "rewrite",
    "verify",
    "verify_and_rewrite",
    "compare_change",
    "accept_change",
    "reject_change",
    "unsupported",
]


class ChatIntent(BaseModel):
    intent: IntentName
    section_id: str | None = None
    change_id: str | None = None
    needs_external_evidence: bool = False
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


def classify_chat_intent(message: str) -> ChatIntent:
    if os.getenv("OPENAI_API_KEY"):
        try:
            return classify_chat_intent_with_openai(message)
        except Exception:
            return classify_chat_intent_locally(message)

    return classify_chat_intent_locally(message)


def classify_chat_intent_with_openai(message: str) -> ChatIntent:
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    response = client.responses.create(
        model=os.getenv("OPENAI_MODEL", settings.llm_model),
        instructions=(
            "Classify the user's document-chat request. "
            "Return JSON only. Do not answer the request. "
            "Allowed intents: qa, section_lookup, summary, rewrite, verify, "
            "verify_and_rewrite, compare_change, accept_change, reject_change, unsupported. "
            "Use summary only for summarization. "
            "Use rewrite for shorten, improve, simplify, revise, or rewrite requests that do not need external evidence. "
            "Use verify for fact-checking or evidence lookup without a requested text update. "
            "Use verify_and_rewrite when the user asks to verify/review with sources and also asks to improve, update, suggest, or rewrite. "
            "Use section_lookup when the user asks which section discusses a topic. "
            "Extract section IDs without '@'. Extract change IDs like change_001. "
            "Set needs_external_evidence true only for verify or verify_and_rewrite."
        ),
        input=json.dumps(
            {
                "message": message,
                "schema": {
                    "intent": "string",
                    "section_id": "string or null",
                    "change_id": "string or null",
                    "needs_external_evidence": "boolean",
                    "confidence": "number from 0 to 1",
                },
            }
        ),
    )

    return validate_intent(parse_json_object(response.output_text), message)


def classify_chat_intent_locally(message: str) -> ChatIntent:
    normalized = message.lower()
    section_id = section_id_from_message(message)
    change_id = change_id_from_message(message)

    if any(phrase in normalized for phrase in ["which section", "what section"]):
        return ChatIntent(
            intent="section_lookup",
            section_id=section_id,
            change_id=change_id,
            confidence=0.85,
        )

    if change_id and "compare" in normalized:
        return ChatIntent(intent="compare_change", change_id=change_id, confidence=0.95)

    if change_id and "accept" in normalized:
        return ChatIntent(intent="accept_change", change_id=change_id, confidence=0.95)

    if change_id and "reject" in normalized:
        return ChatIntent(intent="reject_change", change_id=change_id, confidence=0.95)

    verification_terms = [
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
    rewrite_terms = [
        "rewrite",
        "improve",
        "shorten",
        "make shorter",
        "simplify",
        "make clearer",
        "revise",
        "update",
        "suggest",
        "more precise",
        "better version",
    ]

    asks_for_verification = any(term in normalized for term in verification_terms)
    asks_for_rewrite = any(term in normalized for term in rewrite_terms)

    if asks_for_verification and asks_for_rewrite:
        return ChatIntent(
            intent="verify_and_rewrite",
            section_id=section_id,
            needs_external_evidence=True,
            confidence=0.9,
        )

    if asks_for_verification:
        return ChatIntent(
            intent="verify",
            section_id=section_id,
            needs_external_evidence=True,
            confidence=0.9,
        )

    if any(phrase in normalized for phrase in ["summarize", "summary", "give me a summary"]):
        return ChatIntent(intent="summary", section_id=section_id, confidence=0.9)

    if asks_for_rewrite:
        return ChatIntent(intent="rewrite", section_id=section_id, confidence=0.9)

    return ChatIntent(intent="qa", section_id=section_id, confidence=0.7)


def validate_intent(raw_intent: dict, message: str) -> ChatIntent:
    fallback = classify_chat_intent_locally(message)
    allowed_intents = set(IntentName.__args__)
    intent = raw_intent.get("intent")

    if intent not in allowed_intents:
        return fallback

    section_id = raw_intent.get("section_id") or fallback.section_id
    change_id = raw_intent.get("change_id") or fallback.change_id
    confidence = raw_intent.get("confidence", fallback.confidence)

    try:
        confidence = float(confidence)
    except (TypeError, ValueError):
        confidence = fallback.confidence

    return ChatIntent(
        intent=intent,
        section_id=str(section_id).lstrip("@") if section_id else None,
        change_id=str(change_id) if change_id else None,
        needs_external_evidence=bool(raw_intent.get("needs_external_evidence", fallback.needs_external_evidence)),
        confidence=max(0.0, min(confidence, 1.0)),
    )


def change_id_from_message(message: str) -> str | None:
    match = re.search(r"\bchange_\d+\b", message.lower())
    return match.group(0) if match else None


def parse_json_object(text: str) -> dict:
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
