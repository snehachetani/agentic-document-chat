from pydantic import BaseModel
from fastapi import APIRouter, HTTPException

from src.changes.models import ChangeProposal, EvidenceUsed, ToolCallTrace
from src.core.config import settings
from src.rag.verifier import (
    asks_for_evidence_based_change,
    verify_and_create_change_proposal,
    verify_section,
)

router = APIRouter(tags=["verification"])


class VerifySectionRequest(BaseModel):
    instruction: str


class VerifySectionResponse(BaseModel):
    document_id: str
    section_id: str
    title: str
    fact_check_summary: str
    evidence_used: list[EvidenceUsed]
    tool_call_trace: list[ToolCallTrace]
    external_tools_used: list[str]
    created_change_proposal: bool
    change: ChangeProposal | None = None


@router.post(
    "/documents/{document_id}/sections/{section_id}/verify",
    response_model=VerifySectionResponse,
)
def verify(
    document_id: str,
    section_id: str,
    request: VerifySectionRequest,
) -> VerifySectionResponse:
    if document_id != settings.document_id:
        raise HTTPException(status_code=404, detail="Document not found")

    try:
        if asks_for_evidence_based_change(request.instruction):
            result = verify_and_create_change_proposal(
                section_id=section_id,
                instruction=request.instruction,
            )
        else:
            result = verify_section(
                section_id=section_id,
                instruction=request.instruction,
            )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return VerifySectionResponse(
        document_id=document_id,
        **result,
    )