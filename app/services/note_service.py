from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, ValidationError
from app.core.logging import OrganizationContext
from app.domain.accounting.engine import AccountingEngine
from app.models.entities import (
    AuditLogEntry,
    CreditNote,
    DebitNote,
    Invoice,
    InvoiceStatus,
    InvoiceType,
    NoteApplication,
    NoteStatus,
)


class NoteService:
    def __init__(self, db: Session):
        self.db = db
        self.accounting = AccountingEngine(db)

    def create_credit_note(
        self,
        ctx: OrganizationContext,
        *,
        original_invoice_id: UUID,
        note_number: str,
        note_date: date,
        subtotal: Decimal,
        tax_total: Decimal,
        reason: str | None = None,
    ) -> CreditNote:
        inv = self._get_posted_invoice(ctx, original_invoice_id)
        total = subtotal + tax_total
        self._validate_note_amount(inv, total, is_credit=True)

        note = CreditNote(
            organization_id=ctx.organization_id,
            party_id=inv.party_id,
            original_invoice_id=inv.id,
            note_number=note_number,
            note_date=note_date,
            subtotal=subtotal,
            tax_total=tax_total,
            total=total,
            reason=reason,
            status=NoteStatus.pending_approval,
        )
        self.db.add(note)
        self.db.flush()
        return note

    def create_debit_note(
        self,
        ctx: OrganizationContext,
        *,
        original_invoice_id: UUID,
        note_number: str,
        note_date: date,
        subtotal: Decimal,
        tax_total: Decimal,
        reason: str | None = None,
    ) -> DebitNote:
        inv = self._get_posted_invoice(ctx, original_invoice_id)
        total = subtotal + tax_total

        note = DebitNote(
            organization_id=ctx.organization_id,
            party_id=inv.party_id,
            original_invoice_id=inv.id,
            note_number=note_number,
            note_date=note_date,
            subtotal=subtotal,
            tax_total=tax_total,
            total=total,
            reason=reason,
            status=NoteStatus.pending_approval,
        )
        self.db.add(note)
        self.db.flush()
        return note

    def post_credit_note(
        self,
        ctx: OrganizationContext,
        note_id: UUID,
        *,
        expense_account_id: UUID | None = None,
        payable_account_id: UUID | None = None,
        input_tax_account_id: UUID | None = None,
        receivable_account_id: UUID | None = None,
        revenue_account_id: UUID | None = None,
        output_tax_account_id: UUID | None = None,
    ) -> CreditNote:
        note = self._get_credit_note(ctx, note_id)
        if note.status == NoteStatus.posted:
            return note
        if note.status != NoteStatus.pending_approval:
            raise ValidationError("Credit note is not pending approval")

        inv = self._get_posted_invoice(ctx, note.original_invoice_id)
        lines = self._credit_note_lines(
            inv,
            note,
            expense_account_id,
            payable_account_id,
            input_tax_account_id,
            receivable_account_id,
            revenue_account_id,
            output_tax_account_id,
        )

        entry = self.accounting.create_draft_entry(
            ctx,
            entry_date=note.note_date,
            description=f"Credit note {note.note_number}",
            lines=lines,
            source_type="credit_note",
            source_id=note.id,
            idempotency_key=f"credit-note-{note.id}",
        )
        self.accounting.post_entry(ctx, entry.id)
        note.status = NoteStatus.posted
        note.journal_entry_id = entry.id

        self.db.add(
            NoteApplication(
                organization_id=ctx.organization_id,
                note_type="credit",
                note_id=note.id,
                invoice_id=inv.id,
                amount_applied=note.total,
            )
        )
        self.db.add(
            AuditLogEntry(
                organization_id=ctx.organization_id,
                entity_type="credit_note",
                entity_id=note.id,
                action="posted",
                actor_id=ctx.user_id,
                details={"journal_entry_id": str(entry.id)},
            )
        )
        self.db.flush()
        return note

    def post_debit_note(
        self,
        ctx: OrganizationContext,
        note_id: UUID,
        *,
        expense_account_id: UUID | None = None,
        payable_account_id: UUID | None = None,
        input_tax_account_id: UUID | None = None,
        receivable_account_id: UUID | None = None,
        revenue_account_id: UUID | None = None,
        output_tax_account_id: UUID | None = None,
    ) -> DebitNote:
        note = self._get_debit_note(ctx, note_id)
        if note.status == NoteStatus.posted:
            return note
        if note.status != NoteStatus.pending_approval:
            raise ValidationError("Debit note is not pending approval")

        inv = self._get_posted_invoice(ctx, note.original_invoice_id)
        lines = self._debit_note_lines(
            inv,
            note,
            expense_account_id,
            payable_account_id,
            input_tax_account_id,
            receivable_account_id,
            revenue_account_id,
            output_tax_account_id,
        )

        entry = self.accounting.create_draft_entry(
            ctx,
            entry_date=note.note_date,
            description=f"Debit note {note.note_number}",
            lines=lines,
            source_type="debit_note",
            source_id=note.id,
            idempotency_key=f"debit-note-{note.id}",
        )
        self.accounting.post_entry(ctx, entry.id)
        note.status = NoteStatus.posted
        note.journal_entry_id = entry.id

        self.db.add(
            NoteApplication(
                organization_id=ctx.organization_id,
                note_type="debit",
                note_id=note.id,
                invoice_id=inv.id,
                amount_applied=note.total,
            )
        )
        self.db.add(
            AuditLogEntry(
                organization_id=ctx.organization_id,
                entity_type="debit_note",
                entity_id=note.id,
                action="posted",
                actor_id=ctx.user_id,
                details={"journal_entry_id": str(entry.id)},
            )
        )
        self.db.flush()
        return note

    def invoice_adjusted_outstanding(self, invoice_id: UUID) -> Decimal:
        inv = self.db.get(Invoice, invoice_id)
        if not inv:
            raise NotFoundError("Invoice not found")

        from app.services.payment_service import PaymentService

        payment_outstanding = PaymentService(self.db).invoice_outstanding(invoice_id)

        credit_applied = sum(
            Decimal(str(a.amount_applied))
            for a in self.db.query(NoteApplication)
            .filter(
                NoteApplication.invoice_id == invoice_id,
                NoteApplication.note_type == "credit",
            )
            .all()
        )
        debit_applied = sum(
            Decimal(str(a.amount_applied))
            for a in self.db.query(NoteApplication)
            .filter(
                NoteApplication.invoice_id == invoice_id,
                NoteApplication.note_type == "debit",
            )
            .all()
        )
        return payment_outstanding - credit_applied + debit_applied

    def _credit_note_lines(
        self,
        inv: Invoice,
        note: CreditNote,
        expense_account_id: UUID | None,
        payable_account_id: UUID | None,
        input_tax_account_id: UUID | None,
        receivable_account_id: UUID | None,
        revenue_account_id: UUID | None,
        output_tax_account_id: UUID | None,
    ) -> list[dict]:
        if inv.invoice_type == InvoiceType.purchase:
            if not payable_account_id or not expense_account_id:
                raise ValidationError("Purchase credit note requires payable and expense accounts")
            lines = [
                {
                    "chart_of_account_id": payable_account_id,
                    "debit": note.total,
                    "credit": 0,
                    "description": "Reduce payables",
                },
                {
                    "chart_of_account_id": expense_account_id,
                    "debit": 0,
                    "credit": note.subtotal,
                    "description": "Reduce expense",
                },
            ]
            if input_tax_account_id and note.tax_total:
                lines.append(
                    {
                        "chart_of_account_id": input_tax_account_id,
                        "debit": 0,
                        "credit": note.tax_total,
                        "description": "Reduce input GST",
                    }
                )
            return lines

        if not revenue_account_id or not receivable_account_id:
            raise ValidationError("Sales credit note requires revenue and receivable accounts")
        lines = [
            {
                "chart_of_account_id": revenue_account_id,
                "debit": note.subtotal,
                "credit": 0,
                "description": "Reduce revenue",
            },
            {
                "chart_of_account_id": receivable_account_id,
                "debit": 0,
                "credit": note.total,
                "description": "Reduce receivables",
            },
        ]
        if output_tax_account_id and note.tax_total:
            lines.insert(
                1,
                {
                    "chart_of_account_id": output_tax_account_id,
                    "debit": note.tax_total,
                    "credit": 0,
                    "description": "Reduce output GST",
                },
            )
        return lines

    def _debit_note_lines(
        self,
        inv: Invoice,
        note: DebitNote,
        expense_account_id: UUID | None,
        payable_account_id: UUID | None,
        input_tax_account_id: UUID | None,
        receivable_account_id: UUID | None,
        revenue_account_id: UUID | None,
        output_tax_account_id: UUID | None,
    ) -> list[dict]:
        if inv.invoice_type == InvoiceType.purchase:
            if not expense_account_id or not payable_account_id:
                raise ValidationError("Purchase debit note requires expense and payable accounts")
            lines = [
                {
                    "chart_of_account_id": expense_account_id,
                    "debit": note.subtotal,
                    "credit": 0,
                    "description": "Additional expense",
                },
                {
                    "chart_of_account_id": payable_account_id,
                    "debit": 0,
                    "credit": note.total,
                    "description": "Increase payables",
                },
            ]
            if input_tax_account_id and note.tax_total:
                lines.insert(
                    1,
                    {
                        "chart_of_account_id": input_tax_account_id,
                        "debit": note.tax_total,
                        "credit": 0,
                        "description": "Additional input GST",
                    }
                )
            return lines

        if not receivable_account_id or not revenue_account_id:
            raise ValidationError("Sales debit note requires receivable and revenue accounts")
        lines = [
            {
                "chart_of_account_id": receivable_account_id,
                "debit": note.total,
                "credit": 0,
                "description": "Increase receivables",
            },
            {
                "chart_of_account_id": revenue_account_id,
                "debit": 0,
                "credit": note.subtotal,
                "description": "Additional revenue",
            },
        ]
        if output_tax_account_id and note.tax_total:
            lines.append(
                {
                    "chart_of_account_id": output_tax_account_id,
                    "debit": 0,
                    "credit": note.tax_total,
                    "description": "Additional output GST",
                }
            )
        return lines

    def _validate_note_amount(self, inv: Invoice, note_total: Decimal, *, is_credit: bool) -> None:
        if note_total <= 0:
            raise ValidationError("Note amount must be positive")
        if is_credit:
            outstanding = self.invoice_adjusted_outstanding(inv.id)
            if note_total > outstanding:
                raise ValidationError(
                    f"Credit note {note_total} exceeds adjusted outstanding {outstanding}"
                )

    def _get_posted_invoice(self, ctx: OrganizationContext, invoice_id: UUID | None) -> Invoice:
        if not invoice_id:
            raise ValidationError("Original invoice required")
        inv = (
            self.db.query(Invoice)
            .filter(
                Invoice.id == invoice_id,
                Invoice.organization_id == ctx.organization_id,
                Invoice.status == InvoiceStatus.posted,
            )
            .first()
        )
        if not inv:
            raise NotFoundError("Posted invoice not found")
        return inv

    def _get_credit_note(self, ctx: OrganizationContext, note_id: UUID) -> CreditNote:
        note = (
            self.db.query(CreditNote)
            .filter(
                CreditNote.id == note_id,
                CreditNote.organization_id == ctx.organization_id,
            )
            .first()
        )
        if not note:
            raise NotFoundError("Credit note not found")
        return note

    def _get_debit_note(self, ctx: OrganizationContext, note_id: UUID) -> DebitNote:
        note = (
            self.db.query(DebitNote)
            .filter(
                DebitNote.id == note_id,
                DebitNote.organization_id == ctx.organization_id,
            )
            .first()
        )
        if not note:
            raise NotFoundError("Debit note not found")
        return note
