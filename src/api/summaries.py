from pydantic import BaseModel
from fastapi import APIRouter, HTTPException

from src.core.config import settings
from src.rag.summarizer import summarize_section

router = APIRouter(tags=["summaries"])


class SummaryRequest(BaseModel):
    instruction: str | None = None


class SummaryResponse(BaseModel):
    document_id: str
    section_id: str
    title: str
    summary: str
    external_tools_used: list[str]
    created_change_proposal: bool


@router.post(
    "/documents/{document_id}/sections/{section_id}/summary",
    response_model=SummaryResponse,
)
def summarize(
    document_id: str,
    section_id: str,
    request: SummaryRequest,
) -> SummaryResponse:
    if document_id != settings.document_id:
        raise HTTPException(status_code=404, detail="Document not found")

    try:
        result = summarize_section(
            section_id=section_id,
            instruction=request.instruction,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return SummaryResponse(
        document_id=document_id,
        **result,
    )