from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, ValidationError
from app.core.logging import OrganizationContext
from app.integrations.factory import get_einvoice_provider
from app.models.entities import EInvoice, Invoice, InvoiceStatus, InvoiceType, Organization, Party


class EInvoiceService:
    def __init__(self, db: Session):
        self.db = db

    async def request_einvoice(self, ctx: OrganizationContext, invoice_id: UUID) -> EInvoice:
        inv = (
            self.db.query(Invoice)
            .filter(
                Invoice.id == invoice_id,
                Invoice.organization_id == ctx.organization_id,
            )
            .first()
        )
        if not inv:
            raise NotFoundError("Invoice not found")
        if inv.invoice_type != InvoiceType.sales:
            raise ValidationError("E-invoice applies to sales invoices only")
        if inv.status != InvoiceStatus.posted:
            raise ValidationError("Invoice must be posted before e-invoice generation")

        existing = (
            self.db.query(EInvoice)
            .filter(
                EInvoice.invoice_id == invoice_id,
                EInvoice.status == "generated",
            )
            .first()
        )
        if existing:
            return existing

        org = self.db.get(Organization, ctx.organization_id)
        party = self.db.get(Party, inv.party_id)
        payload = {
            "invoice_number": inv.invoice_number,
            "invoice_date": inv.invoice_date.isoformat(),
            "seller_gstin": org.gstin if org else None,
            "buyer_gstin": party.gstin if party else None,
            "taxable_value": float(inv.subtotal),
            "tax_total": float(inv.tax_total),
            "total": float(inv.total),
        }

        provider = get_einvoice_provider()
        result = await provider.generate_einvoice(invoice_id, payload)

        record = EInvoice(
            organization_id=ctx.organization_id,
            invoice_id=invoice_id,
            irn=result.get("irn"),
            ack_no=result.get("ack_no"),
            status=result.get("status", "generated"),
            response_data=result,
        )
        self.db.add(record)
        self.db.flush()
        return record
