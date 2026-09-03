from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import IdempotencyConflict, NotFoundError, PostingError, ValidationError
from app.core.logging import OrganizationContext
from app.domain.accounting.validation import validate_balanced_lines, validate_line_amounts
from app.models.entities import (
    AuditLogEntry,
    ChartOfAccount,
    JournalEntry,
    JournalEntryLine,
    JournalEntryStatus,
)
from app.repositories.journal import JournalRepository


class AccountingEngine:
    def __init__(self, db: Session):
        self.db = db
        self.repo = JournalRepository(db)

    def create_draft_entry(
        self,
        ctx: OrganizationContext,
        *,
        entry_date,
        description: str,
        lines: list[dict],
        source_type: str | None = None,
        source_id: UUID | None = None,
        idempotency_key: str | None = None,
    ) -> JournalEntry:
        if idempotency_key:
            existing = self.repo.find_by_idempotency(ctx.organization_id, idempotency_key)
            if existing:
                raise IdempotencyConflict(f"Journal entry already exists: {existing.id}")

        if source_type and source_id:
            existing_source = self.repo.find_by_source(ctx.organization_id, source_type, source_id)
            if existing_source:
                raise IdempotencyConflict(f"Source already posted: {existing_source.id}")

        entry_number = self.repo.next_entry_number(ctx.organization_id)
        entry = JournalEntry(
            organization_id=ctx.organization_id,
            entry_number=entry_number,
            entry_date=entry_date,
            description=description,
            status=JournalEntryStatus.draft,
            source_type=source_type,
            source_id=source_id,
            idempotency_key=idempotency_key,
        )
        self.db.add(entry)
        self.db.flush()

        je_lines: list[JournalEntryLine] = []
        for line in lines:
            debit = Decimal(str(line.get("debit", 0)))
            credit = Decimal(str(line.get("credit", 0)))
            validate_line_amounts(debit, credit)
            coa_id = line["chart_of_account_id"]
            coa = self.db.get(ChartOfAccount, coa_id)
            if not coa or coa.organization_id != ctx.organization_id:
                raise ValidationError("Invalid chart of account for organization")
            je_line = JournalEntryLine(
                journal_entry_id=entry.id,
                chart_of_account_id=coa_id,
                debit=debit,
                credit=credit,
                description=line.get("description"),
            )
            je_lines.append(je_line)
            self.db.add(je_line)

        validate_balanced_lines(je_lines)
        return entry

    def post_entry(self, ctx: OrganizationContext, entry_id: UUID) -> JournalEntry:
        entry = self.repo.get(ctx.organization_id, entry_id)
        if not entry:
            raise NotFoundError("Journal entry not found")

        if entry.status == JournalEntryStatus.posted:
            return entry

        if entry.status == JournalEntryStatus.reversed:
            raise PostingError("Cannot post a reversed entry")

        lines = list(entry.lines)
        validate_balanced_lines(lines)

        entry.status = JournalEntryStatus.posted
        entry.posted_at = datetime.now(UTC)
        entry.posted_by_id = ctx.user_id

        self.db.add(
            AuditLogEntry(
                organization_id=ctx.organization_id,
                entity_type="journal_entry",
                entity_id=entry.id,
                action="posted",
                actor_id=ctx.user_id,
                details={"entry_number": entry.entry_number},
            )
        )
        self.db.flush()
        return entry

    def reverse_entry(
        self, ctx: OrganizationContext, entry_id: UUID, *, reason: str = "Reversal"
    ) -> JournalEntry:
        original = self.repo.get(ctx.organization_id, entry_id)
        if not original:
            raise NotFoundError("Journal entry not found")
        if original.status != JournalEntryStatus.posted:
            raise PostingError("Only posted entries can be reversed")
        if original.reversed_by_id:
            raise PostingError("Entry already reversed")

        reversal_lines = [
            {
                "chart_of_account_id": line.chart_of_account_id,
                "debit": line.credit,
                "credit": line.debit,
                "description": f"Reversal: {line.description or ''}",
            }
            for line in original.lines
        ]
        reversal = self.create_draft_entry(
            ctx,
            entry_date=original.entry_date,
            description=f"{reason}: {original.description}",
            lines=reversal_lines,
            source_type="reversal",
            source_id=original.id,
        )
        self.post_entry(ctx, reversal.id)
        original.status = JournalEntryStatus.reversed
        original.reversed_by_id = reversal.id
        self.db.flush()
        return reversal
