from src.db.models import SectionRecord, SectionVersionRecord
from src.db.session import SessionLocal
from src.documents.models import DocumentSection, SectionVersion


class SQLiteDocumentStore:
    def get_section(self, section_id: str) -> DocumentSection:
        with SessionLocal() as db:
            section = db.get(SectionRecord, section_id)
            if section is None:
                raise KeyError(f"Unknown section_id: {section_id}")

            return DocumentSection(
                section_id=section.section_id,
                title=section.title,
                content=section.content,
                version=section.version,
                history=self.get_section_history(section_id),
            )

    def list_sections(self) -> list[DocumentSection]:
        with SessionLocal() as db:
            sections = db.query(SectionRecord).order_by(SectionRecord.section_id).all()

            return [
                DocumentSection(
                    section_id=section.section_id,
                    title=section.title,
                    content=section.content,
                    version=section.version,
                    history=[],
                )
                for section in sections
            ]

    def get_section_history(self, section_id: str) -> list[SectionVersion]:
        with SessionLocal() as db:
            rows = (
                db.query(SectionVersionRecord)
                .filter(SectionVersionRecord.section_id == section_id)
                .order_by(SectionVersionRecord.version)
                .all()
            )

            return [
                SectionVersion(
                    version=row.version,
                    content=row.content,
                    change_id=row.change_id,
                )
                for row in rows
            ]

document_store = SQLiteDocumentStore()


def get_document_store() -> SQLiteDocumentStore:
    return document_store
