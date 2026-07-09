from pydantic import BaseModel
from fastapi import APIRouter, HTTPException

from src.changes.models import ToolCallTrace
from src.core.config import settings
from src.evidence.store import tool_trace_store

router = APIRouter(tags=["evidence"])


class ToolTraceListResponse(BaseModel):
    document_id: str
    tool_call_trace: list[ToolCallTrace]


@router.get(
    "/documents/{document_id}/tool-calls",
    response_model=ToolTraceListResponse,
)
def list_tool_calls(document_id: str) -> ToolTraceListResponse:
    if document_id != settings.document_id:
        raise HTTPException(status_code=404, detail="Document not found")

    return ToolTraceListResponse(
        document_id=document_id,
        tool_call_trace=tool_trace_store.list(),
    )