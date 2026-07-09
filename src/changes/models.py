from datetime import datetime
from enum import StrEnum
from pydantic import BaseModel, Field


class ChangeStatus(StrEnum):
    pending = "pending"
    accepted = "accepted"
    rejected = "rejected"


class EvidenceUsed(BaseModel):
    source_title: str
    source_url: str
    supporting_text: str
    tool_name: str | None = None
    source_domain: str | None = None
    retrieved_at: datetime = Field(default_factory=datetime.utcnow)


class ToolCallTrace(BaseModel):
    tool_name: str
    query: str
    input: dict
    result_count: int
    status: str
    error: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ChangeProposal(BaseModel):
    change_id: str
    section_id: str
    original_text: str
    proposed_text: str
    reason_for_change: str
    evidence_used: list[EvidenceUsed] = Field(default_factory=list)
    status: ChangeStatus = ChangeStatus.pending
    created_at: datetime = Field(default_factory=datetime.utcnow)