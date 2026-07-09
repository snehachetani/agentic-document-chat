from pathlib import Path

from src.db.models import SectionRecord
from src.db.session import SessionLocal, init_db
from src.documents.sections import load_sections


def bootstrap_database(document_path: Path) -> None:
    init_db()

    with SessionLocal() as db:
        existing_count = db.query(SectionRecord).count()
        if existing_count:
            return

        sections = load_sections(document_path)

        for section in sections.values():
            db.add(
                SectionRecord(
                    section_id=section.section_id,
                    title=section.title,
                    content=section.content,
                    version=1,
                )
            )

        db.commit()