from src.changes.models import ChangeProposal, ChangeStatus, EvidenceUsed
from src.db.models import ChangeRecord, EvidenceRecord, SectionRecord, SectionVersionRecord
from src.db.session import SessionLocal


class InvalidChangeStateError(Exception):
    pass


class StaleChangeError(Exception):
    pass


class SQLiteChangeStore:
    def create(
        self,
        section_id: str,
        original_text: str,
        proposed_text: str,
        reason_for_change: str,
        evidence_used: list[EvidenceUsed] | None = None,
    ) -> ChangeProposal:
        with SessionLocal() as db:
            change_id = self._next_change_id(db)

            record = ChangeRecord(
                change_id=change_id,
                section_id=section_id,
                original_text=original_text,
                proposed_text=proposed_text,
                reason_for_change=reason_for_change,
                status=ChangeStatus.pending,
            )
            db.add(record)

            for item in evidence_used or []:
                db.add(
                    EvidenceRecord(
                        change_id=change_id,
                        source_title=item.source_title,
                        source_url=item.source_url,
                        supporting_text=item.supporting_text,
                        tool_name=item.tool_name,
                        source_domain=item.source_domain,
                        retrieved_at=item.retrieved_at,
                    )
                )

            db.commit()
            return self.get(change_id)

    def get(self, change_id: str) -> ChangeProposal:
        with SessionLocal() as db:
            record = db.get(ChangeRecord, change_id)
            if record is None:
                raise KeyError(f"Unknown change_id: {change_id}")
            return self._to_proposal(db, record)

    def list(self) -> list[ChangeProposal]:
        with SessionLocal() as db:
            records = db.query(ChangeRecord).order_by(ChangeRecord.created_at).all()
            return [self._to_proposal(db, record) for record in records]

    def accept(self, change_id: str) -> tuple[ChangeProposal, int]:
        with SessionLocal() as db:
            record = db.get(ChangeRecord, change_id)
            if record is None:
                raise KeyError(f"Unknown change_id: {change_id}")

            if record.status != ChangeStatus.pending:
                raise InvalidChangeStateError(
                    f"Change `{change_id}` is already {record.status}."
                )

            section = db.get(SectionRecord, record.section_id)
            if section is None:
                raise KeyError(f"Unknown section_id: {record.section_id}")

            if section.content != record.original_text:
                raise StaleChangeError(
                    f"Change `{change_id}` was created from an older section version."
                )

            db.add(
                SectionVersionRecord(
                    section_id=section.section_id,
                    version=section.version,
                    content=section.content,
                    change_id=record.change_id,
                )
            )

            section.content = record.proposed_text
            section.version += 1
            record.status = ChangeStatus.accepted

            new_version = section.version
            db.commit()

            return self.get(change_id), new_version

    def reject(self, change_id: str) -> ChangeProposal:
        with SessionLocal() as db:
            record = db.get(ChangeRecord, change_id)
            if record is None:
                raise KeyError(f"Unknown change_id: {change_id}")

            if record.status != ChangeStatus.pending:
                raise InvalidChangeStateError(
                    f"Change `{change_id}` is already {record.status}."
                )

            record.status = ChangeStatus.rejected
            db.commit()

            return self.get(change_id)

    def _next_change_id(self, db) -> str:
        count = db.query(ChangeRecord).count() + 1
        while db.get(ChangeRecord, f"change_{count:03d}") is not None:
            count += 1
        return f"change_{count:03d}"

    def _to_proposal(self, db, record: ChangeRecord) -> ChangeProposal:
        evidence_rows = (
            db.query(EvidenceRecord)
            .filter(EvidenceRecord.change_id == record.change_id)
            .order_by(EvidenceRecord.id)
            .all()
        )

        return ChangeProposal(
            change_id=record.change_id,
            section_id=record.section_id,
            original_text=record.original_text,
            proposed_text=record.proposed_text,
            reason_for_change=record.reason_for_change,
            evidence_used=[
                EvidenceUsed(
                    source_title=row.source_title,
                    source_url=row.source_url,
                    supporting_text=row.supporting_text,
                    tool_name=row.tool_name,
                    source_domain=row.source_domain,
                    retrieved_at=row.retrieved_at,
                )
                for row in evidence_rows
            ],
            status=ChangeStatus(record.status),
            created_at=record.created_at,
        )


change_store = SQLiteChangeStore()