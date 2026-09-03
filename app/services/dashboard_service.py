from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.logging import OrganizationContext
from app.models.entities import (
    ApprovalRequest,
    Invoice,
    InvoiceStatus,
    InvoiceType,
    JournalEntry,
    JournalEntryStatus,
    Party,
    Payment,
)
from app.services.payment_service import PaymentService


class DashboardService:
    def __init__(self, db: Session):
        self.db = db
        self.payments = PaymentService(db)

    def summary(self, ctx: OrganizationContext) -> dict:
        pending_approvals = (
            self.db.query(ApprovalRequest)
            .filter(
                ApprovalRequest.organization_id == ctx.organization_id,
                ApprovalRequest.status == "pending",
            )
            .count()
        )
        posted_invoices = (
            self.db.query(Invoice)
            .filter(
                Invoice.organization_id == ctx.organization_id,
                Invoice.status == InvoiceStatus.posted,
            )
            .all()
        )
        outstanding_total = Decimal("0")
        outstanding_count = 0
        for inv in posted_invoices:
            out = self.payments.invoice_outstanding(inv.id)
            if out > 0:
                outstanding_total += out
                outstanding_count += 1

        recent_entries = (
            self.db.query(JournalEntry)
            .filter(
                JournalEntry.organization_id == ctx.organization_id,
                JournalEntry.status == JournalEntryStatus.posted,
            )
            .order_by(JournalEntry.posted_at.desc())
            .limit(10)
            .all()
        )

        return {
            "pending_approvals": pending_approvals,
            "outstanding_invoices_count": outstanding_count,
            "outstanding_total": str(outstanding_total),
            "recent_journal_entries": [
                {
                    "id": str(e.id),
                    "entry_number": e.entry_number,
                    "entry_date": e.entry_date.isoformat(),
                    "description": e.description,
                }
                for e in recent_entries
            ],
        }

    def list_invoices(
        self,
        ctx: OrganizationContext,
        *,
        status: str | None = None,
        invoice_type: str | None = None,
    ) -> list[dict]:
        q = self.db.query(Invoice).filter(Invoice.organization_id == ctx.organization_id)
        if status:
            q = q.filter(Invoice.status == InvoiceStatus(status))
        if invoice_type:
            q = q.filter(Invoice.invoice_type == InvoiceType(invoice_type))
        invoices = q.order_by(Invoice.invoice_date.desc()).limit(100).all()
        result = []
        for inv in invoices:
            outstanding = (
                self.payments.invoice_outstanding(inv.id)
                if inv.status == InvoiceStatus.posted
                else Decimal(str(inv.total))
            )
            party_row = self.db.get(Party, inv.party_id)
            result.append({
                "id": str(inv.id),
                "invoice_number": inv.invoice_number,
                "invoice_date": inv.invoice_date.isoformat(),
                "invoice_type": inv.invoice_type.value,
                "party_id": str(inv.party_id),
                "party_name": party_row.name if party_row else "",
                "total": str(inv.total),
                "status": inv.status.value,
                "outstanding": str(outstanding),
            })
        return result

    def list_payments(self, ctx: OrganizationContext) -> list[dict]:
        payments = (
            self.db.query(Payment)
            .filter(Payment.organization_id == ctx.organization_id)
            .order_by(Payment.payment_date.desc())
            .limit(100)
            .all()
        )
        return [
            {
                "id": str(p.id),
                "amount": str(p.amount),
                "payment_date": p.payment_date.isoformat(),
                "reference": p.reference,
                "journal_entry_id": str(p.journal_entry_id) if p.journal_entry_id else None,
            }
            for p in payments
        ]
