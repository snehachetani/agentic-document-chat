from pydantic import BaseModel
from fastapi import APIRouter, HTTPException

from src.changes.diff import build_text_diff
from src.changes.models import ChangeProposal
from src.changes.store import (
    InvalidChangeStateError,
    StaleChangeError,
    change_store,
)
from src.core.config import settings
from src.rag.rewriter import create_rewrite_proposal

router = APIRouter(tags=["changes"])


class CreateChangeRequest(BaseModel):
    instruction: str


class CreateChangeResponse(BaseModel):
    document_id: str
    change: ChangeProposal
    external_tools_used: list[str]
    section_was_modified: bool


class CompareChangeResponse(BaseModel):
    change_id: str
    section_id: str
    diff: str
    original_text: str
    proposed_text: str


class AcceptChangeResponse(BaseModel):
    change_id: str
    section_id: str
    status: str
    new_version: int


class RejectChangeResponse(BaseModel):
    change_id: str
    section_id: str
    status: str


@router.post(
    "/documents/{document_id}/sections/{section_id}/changes",
    response_model=CreateChangeResponse,
)
def create_change(
    document_id: str,
    section_id: str,
    request: CreateChangeRequest,
) -> CreateChangeResponse:
    if document_id != settings.document_id:
        raise HTTPException(status_code=404, detail="Document not found")

    try:
        proposal = create_rewrite_proposal(
            section_id=section_id,
            instruction=request.instruction,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return CreateChangeResponse(
        document_id=document_id,
        change=proposal,
        external_tools_used=[],
        section_was_modified=False,
    )


@router.get(
    "/documents/{document_id}/changes/{change_id}",
    response_model=ChangeProposal,
)
def get_change(document_id: str, change_id: str) -> ChangeProposal:
    if document_id != settings.document_id:
        raise HTTPException(status_code=404, detail="Document not found")

    try:
        return change_store.get(change_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get(
    "/documents/{document_id}/changes/{change_id}/compare",
    response_model=CompareChangeResponse,
)
def compare_change(
    document_id: str,
    change_id: str,
) -> CompareChangeResponse:
    if document_id != settings.document_id:
        raise HTTPException(status_code=404, detail="Document not found")

    try:
        proposal = change_store.get(change_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return CompareChangeResponse(
        change_id=proposal.change_id,
        section_id=proposal.section_id,
        diff=build_text_diff(
            original_text=proposal.original_text,
            proposed_text=proposal.proposed_text,
        ),
        original_text=proposal.original_text,
        proposed_text=proposal.proposed_text,
    )


@router.post(
    "/documents/{document_id}/changes/{change_id}/accept",
    response_model=AcceptChangeResponse,
)
def accept_change(
    document_id: str,
    change_id: str,
) -> AcceptChangeResponse:
    if document_id != settings.document_id:
        raise HTTPException(status_code=404, detail="Document not found")

    try:
        proposal, new_version = change_store.accept(change_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except InvalidChangeStateError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except StaleChangeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    return AcceptChangeResponse(
        change_id=proposal.change_id,
        section_id=proposal.section_id,
        status=proposal.status,
        new_version=new_version,
    )


@router.post(
    "/documents/{document_id}/changes/{change_id}/reject",
    response_model=RejectChangeResponse,
)
def reject_change(
    document_id: str,
    change_id: str,
) -> RejectChangeResponse:
    if document_id != settings.document_id:
        raise HTTPException(status_code=404, detail="Document not found")

    try:
        proposal = change_store.reject(change_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except InvalidChangeStateError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    return RejectChangeResponse(
        change_id=proposal.change_id,
        section_id=proposal.section_id,
        status=proposal.status,
    )