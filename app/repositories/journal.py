from uuid import UUID

from sqlalchemy.orm import Session

from app.models.entities import JournalEntry


class JournalRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, organization_id: UUID, entry_id: UUID) -> JournalEntry | None:
        return (
            self.db.query(JournalEntry)
            .filter(
                JournalEntry.organization_id == organization_id,
                JournalEntry.id == entry_id,
            )
            .first()
        )

    def find_by_idempotency(
        self, organization_id: UUID, idempotency_key: str
    ) -> JournalEntry | None:
        return (
            self.db.query(JournalEntry)
            .filter(
                JournalEntry.organization_id == organization_id,
                JournalEntry.idempotency_key == idempotency_key,
            )
            .first()
        )

    def find_by_source(
        self, organization_id: UUID, source_type: str, source_id: UUID
    ) -> JournalEntry | None:
        return (
            self.db.query(JournalEntry)
            .filter(
                JournalEntry.organization_id == organization_id,
                JournalEntry.source_type == source_type,
                JournalEntry.source_id == source_id,
            )
            .first()
        )

    def next_entry_number(self, organization_id: UUID) -> str:
        count = (
            self.db.query(JournalEntry)
            .filter(JournalEntry.organization_id == organization_id)
            .count()
        )
        return f"JE-{count + 1:06d}"
