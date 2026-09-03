from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, ValidationError
from app.core.logging import OrganizationContext
from app.domain.accounting.engine import AccountingEngine
from app.domain.tax.engine import TaxEngine
from app.integrations.protocols import DocumentExtraction
from app.models.entities import (
    ApprovalRequest,
    AuditLogEntry,
    Invoice,
    InvoiceLineItem,
    InvoiceStatus,
    InvoiceType,
    Party,
    PartyType,
)


class InvoiceService:
    def __init__(self, db: Session):
        self.db = db
        self.accounting = AccountingEngine(db)
        self.tax = TaxEngine(db)

    def create_from_extraction(
        self,
        ctx: OrganizationContext,
        extraction: DocumentExtraction,
        *,
        expense_account_id: UUID,
        payable_account_id: UUID,
        input_tax_account_id: UUID | None = None,
    ) -> Invoice:
        inv_type = InvoiceType(extraction.invoice_type)
        party = self._get_or_create_party(ctx, extraction, inv_type)
        inv_number = extraction.invoice_number or "UNKNOWN"
        inv_date = extraction.invoice_date or date.today()
        self._check_duplicate_invoice(ctx, party.id, inv_number, inv_date)

        inv = Invoice(
            organization_id=ctx.organization_id,
            party_id=party.id,
            invoice_type=inv_type,
            invoice_number=inv_number,
            invoice_date=inv_date,
            subtotal=extraction.subtotal,
            tax_total=extraction.tax_total,
            total=extraction.total,
            status=InvoiceStatus.pending_approval,
        )
        self.db.add(inv)
        self.db.flush()

        for item in extraction.line_items:
            self.db.add(
                InvoiceLineItem(
                    invoice_id=inv.id,
                    description=item.description,
                    quantity=item.quantity,
                    unit_price=item.unit_price,
                    tax_rate=item.tax_rate,
                    line_total=item.line_total,
                )
            )

        tax_snap = self.tax.compute_gst(
            organization_id=ctx.organization_id,
            as_of=inv.invoice_date,
            taxable_amount=Decimal(str(inv.subtotal)),
            is_interstate=False,
        )
        inv.tax_computation_snapshot = tax_snap
        if tax_snap.get("tax_rule_version_id"):
            inv.tax_rule_version_id = UUID(tax_snap["tax_rule_version_id"])

        self.db.add(
            ApprovalRequest(
                organization_id=ctx.organization_id,
                entity_type="invoice",
                entity_id=inv.id,
                status="pending",
                requested_by_id=ctx.user_id,
            )
        )
        self.db.flush()
        return inv

    def confirm_and_post(
        self,
        ctx: OrganizationContext,
        invoice_id: UUID,
        *,
        expense_account_id: UUID | None = None,
        payable_account_id: UUID | None = None,
        input_tax_account_id: UUID | None = None,
        receivable_account_id: UUID | None = None,
        revenue_account_id: UUID | None = None,
        output_tax_account_id: UUID | None = None,
        idempotency_key: str | None = None,
    ) -> Invoice:
        inv = self._get_invoice(ctx, invoice_id)
        if inv.status == InvoiceStatus.posted:
            return inv
        if inv.status != InvoiceStatus.pending_approval:
            raise ValidationError("Invoice is not pending approval")

        if inv.invoice_type == InvoiceType.sales:
            lines, description = self._sales_journal_lines(
                inv, receivable_account_id, revenue_account_id, output_tax_account_id
            )
        else:
            lines, description = self._purchase_journal_lines(
                inv, expense_account_id, payable_account_id, input_tax_account_id
            )

        entry = self.accounting.create_draft_entry(
            ctx,
            entry_date=inv.invoice_date,
            description=description,
            lines=lines,
            source_type="invoice",
            source_id=inv.id,
            idempotency_key=idempotency_key or f"invoice-{inv.id}",
        )
        self.accounting.post_entry(ctx, entry.id)
        inv.status = InvoiceStatus.posted
        inv.journal_entry_id = entry.id

        approval = (
            self.db.query(ApprovalRequest)
            .filter(
                ApprovalRequest.entity_type == "invoice",
                ApprovalRequest.entity_id == inv.id,
            )
            .first()
        )
        if approval:
            approval.status = "approved"
            approval.resolved_at = entry.posted_at

        self.db.add(
            AuditLogEntry(
                organization_id=ctx.organization_id,
                entity_type="invoice",
                entity_id=inv.id,
                action="posted",
                actor_id=ctx.user_id,
                details={"journal_entry_id": str(entry.id)},
            )
        )
        self.db.flush()
        return inv

    def _purchase_journal_lines(
        self,
        inv: Invoice,
        expense_account_id: UUID | None,
        payable_account_id: UUID | None,
        input_tax_account_id: UUID | None,
    ) -> tuple[list[dict], str]:
        if not expense_account_id or not payable_account_id:
            raise ValidationError("Purchase accounts (expense, payable) required")
        lines = [
            {
                "chart_of_account_id": expense_account_id,
                "debit": inv.subtotal,
                "credit": 0,
                "description": f"Expense {inv.invoice_number}",
            },
            {
                "chart_of_account_id": payable_account_id,
                "debit": 0,
                "credit": inv.total,
                "description": f"Payable {inv.invoice_number}",
            },
        ]
        if input_tax_account_id and inv.tax_total:
            lines.insert(
                1,
                {
                    "chart_of_account_id": input_tax_account_id,
                    "debit": inv.tax_total,
                    "credit": 0,
                    "description": "Input GST",
                },
            )
        return lines, f"Purchase invoice {inv.invoice_number}"

    def _sales_journal_lines(
        self,
        inv: Invoice,
        receivable_account_id: UUID | None,
        revenue_account_id: UUID | None,
        output_tax_account_id: UUID | None,
    ) -> tuple[list[dict], str]:
        if not receivable_account_id or not revenue_account_id:
            raise ValidationError("Sales accounts (receivable, revenue) required")
        lines = [
            {
                "chart_of_account_id": receivable_account_id,
                "debit": inv.total,
                "credit": 0,
                "description": f"AR {inv.invoice_number}",
            },
            {
                "chart_of_account_id": revenue_account_id,
                "debit": 0,
                "credit": inv.subtotal,
                "description": f"Revenue {inv.invoice_number}",
            },
        ]
        if output_tax_account_id and inv.tax_total:
            lines.append(
                {
                    "chart_of_account_id": output_tax_account_id,
                    "debit": 0,
                    "credit": inv.tax_total,
                    "description": "Output GST",
                }
            )
        return lines, f"Sales invoice {inv.invoice_number}"

    def _get_or_create_party(
        self,
        ctx: OrganizationContext,
        extraction: DocumentExtraction,
        inv_type: InvoiceType,
    ) -> Party:
        gstin = extraction.vendor_gstin
        if gstin:
            existing = (
                self.db.query(Party)
                .filter(
                    Party.organization_id == ctx.organization_id,
                    Party.gstin == gstin,
                )
                .first()
            )
            if existing:
                return existing
        if inv_type == InvoiceType.sales:
            party_type = PartyType.customer
            name = extraction.vendor_name or "Unknown Customer"
        else:
            party_type = PartyType.vendor
            name = extraction.vendor_name or "Unknown Vendor"
        party = Party(
            organization_id=ctx.organization_id,
            party_type=party_type,
            name=name,
            gstin=gstin,
        )
        self.db.add(party)
        self.db.flush()
        return party

    def _get_invoice(self, ctx: OrganizationContext, invoice_id: UUID) -> Invoice:
        inv = (
            self.db.query(Invoice)
            .filter(Invoice.id == invoice_id, Invoice.organization_id == ctx.organization_id)
            .first()
        )
        if not inv:
            raise NotFoundError("Invoice not found")
        return inv

    def _check_duplicate_invoice(
        self,
        ctx: OrganizationContext,
        party_id: UUID,
        invoice_number: str,
        invoice_date: date,
    ) -> None:
        existing = (
            self.db.query(Invoice)
            .filter(
                Invoice.organization_id == ctx.organization_id,
                Invoice.party_id == party_id,
                Invoice.invoice_number == invoice_number,
                Invoice.invoice_date == invoice_date,
                Invoice.deleted_at.is_(None),
            )
            .first()
        )
        if existing:
            raise ValidationError(
                f"Duplicate invoice: {invoice_number} from party on {invoice_date}"
            )
