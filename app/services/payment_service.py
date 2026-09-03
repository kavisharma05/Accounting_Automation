from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import IdempotencyConflict, NotFoundError, ValidationError
from app.core.logging import OrganizationContext
from app.domain.accounting.engine import AccountingEngine
from app.models.entities import (
    AuditLogEntry,
    Invoice,
    InvoiceStatus,
    Payment,
    PaymentApplication,
)


class PaymentService:
    def __init__(self, db: Session):
        self.db = db
        self.accounting = AccountingEngine(db)

    def invoice_outstanding(self, invoice_id: UUID) -> Decimal:
        inv = self.db.get(Invoice, invoice_id)
        if not inv:
            raise NotFoundError("Invoice not found")
        applied = (
            self.db.query(PaymentApplication)
            .filter(PaymentApplication.invoice_id == invoice_id)
            .all()
        )
        total_applied = sum(Decimal(str(a.amount_applied)) for a in applied)
        return Decimal(str(inv.total)) - total_applied

    def create_and_post_payment(
        self,
        ctx: OrganizationContext,
        *,
        party_id: UUID,
        amount: Decimal,
        payment_date: date,
        payable_account_id: UUID,
        bank_account_id: UUID,
        reference: str | None = None,
        idempotency_key: str | None = None,
        applications: list[dict] | None = None,
    ) -> Payment:
        if amount <= 0:
            raise ValidationError("Payment amount must be positive")

        self._check_duplicate(ctx, party_id, amount, payment_date, reference)
        if idempotency_key:
            existing = (
                self.db.query(Payment)
                .filter(
                    Payment.organization_id == ctx.organization_id,
                    Payment.idempotency_key == idempotency_key,
                )
                .first()
            )
            if existing:
                raise IdempotencyConflict(f"Payment already exists: {existing.id}")

        payment = Payment(
            organization_id=ctx.organization_id,
            party_id=party_id,
            amount=amount,
            payment_date=payment_date,
            reference=reference,
            idempotency_key=idempotency_key,
        )
        self.db.add(payment)
        self.db.flush()

        if applications:
            apply_total = self._validate_and_create_applications(
                ctx, payment, applications
            )
            if apply_total > amount:
                raise ValidationError("Applied amount exceeds payment")

        entry = self.accounting.create_draft_entry(
            ctx,
            entry_date=payment_date,
            description=f"Payment {reference or payment.id}",
            lines=[
                {
                    "chart_of_account_id": payable_account_id,
                    "debit": amount,
                    "credit": 0,
                    "description": "Reduce payables",
                },
                {
                    "chart_of_account_id": bank_account_id,
                    "debit": 0,
                    "credit": amount,
                    "description": "Bank payment",
                },
            ],
            source_type="payment",
            source_id=payment.id,
            idempotency_key=idempotency_key or f"payment-{payment.id}",
        )
        self.accounting.post_entry(ctx, entry.id)
        payment.journal_entry_id = entry.id

        self.db.add(
            AuditLogEntry(
                organization_id=ctx.organization_id,
                entity_type="payment",
                entity_id=payment.id,
                action="posted",
                actor_id=ctx.user_id,
                details={"amount": str(amount), "reference": reference},
            )
        )
        self.db.flush()
        return payment

    def apply_to_invoices(
        self,
        ctx: OrganizationContext,
        payment_id: UUID,
        applications: list[dict],
    ) -> Payment:
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

        existing_total = sum(
            Decimal(str(a.amount_applied))
            for a in self.db.query(PaymentApplication)
            .filter(PaymentApplication.payment_id == payment.id)
            .all()
        )
        new_total = self._validate_and_create_applications(ctx, payment, applications)
        if existing_total + new_total > Decimal(str(payment.amount)):
            raise ValidationError("Total applied exceeds payment amount")
        self.db.flush()
        return payment

    def _validate_and_create_applications(
        self,
        ctx: OrganizationContext,
        payment: Payment,
        applications: list[dict],
    ) -> Decimal:
        new_total = Decimal("0")
        for app in applications:
            invoice_id = app["invoice_id"]
            amount_applied = Decimal(str(app["amount_applied"]))
            if amount_applied <= 0:
                raise ValidationError("Application amount must be positive")

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
                raise ValidationError(f"Invoice {invoice_id} not posted or not found")
            if inv.party_id != payment.party_id:
                raise ValidationError("Invoice party must match payment party")

            outstanding = self.invoice_outstanding(invoice_id)
            if amount_applied > outstanding:
                raise ValidationError(
                    f"Cannot apply {amount_applied}; outstanding is {outstanding}"
                )

            self.db.add(
                PaymentApplication(
                    payment_id=payment.id,
                    invoice_id=invoice_id,
                    amount_applied=amount_applied,
                )
            )
            new_total += amount_applied
        return new_total

    def _check_duplicate(
        self,
        ctx: OrganizationContext,
        party_id: UUID,
        amount: Decimal,
        payment_date: date,
        reference: str | None,
    ) -> None:
        if not reference:
            return
        dup = (
            self.db.query(Payment)
            .filter(
                Payment.organization_id == ctx.organization_id,
                Payment.party_id == party_id,
                Payment.amount == amount,
                Payment.payment_date == payment_date,
                Payment.reference == reference,
            )
            .first()
        )
        if dup:
            raise ValidationError("Duplicate payment detected")
