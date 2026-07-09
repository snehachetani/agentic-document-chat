from pydantic import BaseModel
from fastapi import APIRouter, HTTPException

from src.core.config import settings
from src.documents.models import DocumentSection, SectionVersion
from src.documents.store import get_document_store

router = APIRouter(tags=["documents"])


class SectionListItem(BaseModel):
    section_id: str
    title: str
    version: int


class SectionListResponse(BaseModel):
    document_id: str
    sections: list[SectionListItem]


class SectionHistoryItem(BaseModel):
    version: int
    content: str
    change_id: str | None = None
    is_current: bool = False


class SectionHistoryResponse(BaseModel):
    document_id: str
    section_id: str
    title: str
    current_version: int
    versions: list[SectionHistoryItem]


@router.get(
    "/documents/{document_id}/sections",
    response_model=SectionListResponse,
)
def list_sections(document_id: str) -> SectionListResponse:
    if document_id != settings.document_id:
        raise HTTPException(status_code=404, detail="Document not found")

    sections = get_document_store().list_sections()

    return SectionListResponse(
        document_id=document_id,
        sections=[
            SectionListItem(
                section_id=section.section_id,
                title=section.title,
                version=section.version,
            )
            for section in sections
        ],
    )


@router.get(
    "/documents/{document_id}/sections/{section_id}",
    response_model=DocumentSection,
)
def get_section(document_id: str, section_id: str) -> DocumentSection:
    if document_id != settings.document_id:
        raise HTTPException(status_code=404, detail="Document not found")

    try:
        return get_document_store().get_section(section_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get(
    "/documents/{document_id}/sections/{section_id}/history",
    response_model=SectionHistoryResponse,
)
def get_section_history(
    document_id: str,
    section_id: str,
) -> SectionHistoryResponse:
    if document_id != settings.document_id:
        raise HTTPException(status_code=404, detail="Document not found")

    try:
        section = get_document_store().get_section(section_id)
        previous_versions = get_document_store().get_section_history(section_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    versions = [
        SectionHistoryItem(
            version=item.version,
            content=item.content,
            change_id=item.change_id,
            is_current=False,
        )
        for item in previous_versions
    ]

    versions.append(
        SectionHistoryItem(
            version=section.version,
            content=section.content,
            change_id=None,
            is_current=True,
        )
    )

    return SectionHistoryResponse(
        document_id=document_id,
        section_id=section.section_id,
        title=section.title,
        current_version=section.version,
        versions=versions,
    )