from pydantic import BaseModel, Field


class SectionVersion(BaseModel):
    version: int
    content: str
    change_id: str | None = None


class DocumentSection(BaseModel):
    section_id: str
    title: str
    content: str
    version: int = 1
    history: list[SectionVersion] = Field(default_factory=list)