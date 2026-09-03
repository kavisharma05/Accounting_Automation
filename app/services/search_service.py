from decimal import Decimal

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.logging import OrganizationContext
from app.models.entities import Invoice, InvoiceStatus, Party
from app.services.payment_service import PaymentService


class SearchService:
    """Invoice search with ILIKE (Postgres-compatible; FTS upgrade path in Phase 5)."""

    def __init__(self, db: Session):
        self.db = db
        self.payments = PaymentService(db)

    def search_invoices(
        self,
        ctx: OrganizationContext,
        *,
        q: str,
        invoice_type: str | None = None,
        limit: int = 50,
    ) -> list[dict]:
        pattern = f"%{q}%"
        query = (
            self.db.query(Invoice, Party)
            .join(Party, Party.id == Invoice.party_id)
            .filter(
                Invoice.organization_id == ctx.organization_id,
                Invoice.deleted_at.is_(None),
                or_(
                    Invoice.invoice_number.ilike(pattern),
                    Party.name.ilike(pattern),
                    Party.gstin.ilike(pattern),
                ),
            )
        )
        if invoice_type:
            query = query.filter(Invoice.invoice_type == invoice_type)

        rows = query.order_by(Invoice.invoice_date.desc()).limit(limit).all()
        result = []
        for inv, party in rows:
            outstanding = (
                self.payments.invoice_outstanding(inv.id)
                if inv.status == InvoiceStatus.posted
                else Decimal(str(inv.total))
            )
            result.append({
                "id": str(inv.id),
                "invoice_number": inv.invoice_number,
                "invoice_date": inv.invoice_date.isoformat(),
                "invoice_type": inv.invoice_type.value,
                "party_id": str(inv.party_id),
                "party_name": party.name,
                "party_gstin": party.gstin,
                "total": str(inv.total),
                "status": inv.status.value,
                "outstanding": str(outstanding),
            })
        return result
