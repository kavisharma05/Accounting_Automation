from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, ValidationError
from app.core.logging import OrganizationContext
from app.domain.accounting.engine import AccountingEngine
from app.domain.tax.engine import TaxEngine
from app.models.entities import Payment, TdsDeduction


class TdsService:
    def __init__(self, db: Session):
        self.db = db
        self.tax = TaxEngine(db)
        self.accounting = AccountingEngine(db)

    def compute(
        self,
        ctx: OrganizationContext,
        *,
        taxable_amount: Decimal,
        section: str,
        as_of: date,
    ) -> dict:
        if taxable_amount <= 0:
            raise ValidationError("Taxable amount must be positive")
        return self.tax.compute_tds(
            organization_id=ctx.organization_id,
            as_of=as_of,
            taxable_amount=taxable_amount,
            section=section,
        )

    def apply_to_payment(
        self,
        ctx: OrganizationContext,
        payment_id: UUID,
        *,
        section: str,
        tds_payable_account_id: UUID,
        payable_account_id: UUID,
    ) -> TdsDeduction:
        payment = (
            self.db.query(Payment)
            .filter(
                Payment.id == payment_id,
                Payment.organization_id == ctx.organization_id,
            )
            .first()
        )
        if not payment:
            raise NotFoundError("Payment not found")
        if not payment.journal_entry_id:
            raise ValidationError("Payment must be posted before TDS application")

        existing = (
            self.db.query(TdsDeduction)
            .filter(TdsDeduction.payment_id == payment_id)
            .first()
        )
        if existing:
            return existing

        snap = self.tax.compute_tds(
            organization_id=ctx.organization_id,
            as_of=payment.payment_date,
            taxable_amount=Decimal(str(payment.amount)),
            section=section,
        )
        if not snap.get("applicable"):
            raise ValidationError(snap.get("reason", "TDS not applicable"))

        tds_amount = Decimal(str(snap["tds_amount"]))
        if tds_amount <= 0:
            raise ValidationError("TDS amount is zero")

        rule_id = snap.get("tax_rule_version_id")
        deduction = TdsDeduction(
            organization_id=ctx.organization_id,
            payment_id=payment.id,
            party_id=payment.party_id,
            tds_section=section,
            taxable_amount=payment.amount,
            tds_rate=snap["rate"],
            tds_amount=tds_amount,
            tax_rule_version_id=UUID(rule_id) if rule_id else None,
            computation_snapshot=snap,
        )
        self.db.add(deduction)
        self.db.flush()

        entry = self.accounting.create_draft_entry(
            ctx,
            entry_date=payment.payment_date,
            description=f"TDS {section} on payment {payment.reference or payment.id}",
            lines=[
                {
                    "chart_of_account_id": payable_account_id,
                    "debit": tds_amount,
                    "credit": 0,
                    "description": "TDS on vendor payment",
                },
                {
                    "chart_of_account_id": tds_payable_account_id,
                    "debit": 0,
                    "credit": tds_amount,
                    "description": f"TDS {section} payable",
                },
            ],
            source_type="tds_deduction",
            source_id=deduction.id,
            idempotency_key=f"tds-{deduction.id}",
        )
        self.accounting.post_entry(ctx, entry.id)
        deduction.journal_entry_id = entry.id
        self.db.flush()
        return deduction

    def list_deductions(self, ctx: OrganizationContext) -> list[dict]:
        rows = (
            self.db.query(TdsDeduction)
            .filter(TdsDeduction.organization_id == ctx.organization_id)
            .order_by(TdsDeduction.created_at.desc())
            .limit(100)
            .all()
        )
        return [
            {
                "id": str(r.id),
                "payment_id": str(r.payment_id),
                "tds_section": r.tds_section,
                "taxable_amount": str(r.taxable_amount),
                "tds_rate": float(r.tds_rate),
                "tds_amount": str(r.tds_amount),
                "journal_entry_id": str(r.journal_entry_id) if r.journal_entry_id else None,
            }
            for r in rows
        ]
