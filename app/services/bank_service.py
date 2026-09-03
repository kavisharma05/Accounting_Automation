import csv
from datetime import date
from decimal import Decimal, InvalidOperation
from io import StringIO
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, ValidationError
from app.core.logging import OrganizationContext
from app.models.entities import (
    BankAccount,
    BankStatementTransaction,
    Payment,
    ReconciliationMatch,
)


class BankService:
    def __init__(self, db: Session):
        self.db = db

    def create_bank_account(
        self,
        ctx: OrganizationContext,
        *,
        name: str,
        chart_of_account_id: UUID,
        account_number: str | None = None,
        ifsc: str | None = None,
    ) -> BankAccount:
        coa_check = chart_of_account_id  # validated by caller or FK
        acct = BankAccount(
            organization_id=ctx.organization_id,
            chart_of_account_id=coa_check,
            name=name,
            account_number=account_number,
            ifsc=ifsc,
        )
        self.db.add(acct)
        self.db.flush()
        return acct

    def import_csv(
        self,
        ctx: OrganizationContext,
        bank_account_id: UUID,
        csv_content: str,
    ) -> list[BankStatementTransaction]:
        acct = self._get_bank_account(ctx, bank_account_id)
        reader = csv.DictReader(StringIO(csv_content))
        required = {"date", "description", "amount"}
        if not reader.fieldnames or not required.issubset(set(reader.fieldnames)):
            raise ValidationError("CSV must have columns: date, description, amount")

        imported: list[BankStatementTransaction] = []
        for row in reader:
            try:
                txn_date = date.fromisoformat(row["date"].strip())
                amount = Decimal(row["amount"].strip())
            except (ValueError, InvalidOperation) as e:
                raise ValidationError(f"Invalid row: {row}") from e

            ext_ref = row.get("reference") or row.get("ref")
            if ext_ref:
                exists = (
                    self.db.query(BankStatementTransaction)
                    .filter(
                        BankStatementTransaction.bank_account_id == acct.id,
                        BankStatementTransaction.external_ref == ext_ref,
                    )
                    .first()
                )
                if exists:
                    continue

            txn = BankStatementTransaction(
                organization_id=ctx.organization_id,
                bank_account_id=acct.id,
                transaction_date=txn_date,
                description=row.get("description", "")[:512],
                amount=amount,
                external_ref=ext_ref,
            )
            self.db.add(txn)
            imported.append(txn)

        self.db.flush()
        return imported

    def auto_match(
        self,
        ctx: OrganizationContext,
        bank_account_id: UUID,
    ) -> list[ReconciliationMatch]:
        """Match unreconciled bank debits to payments by amount+date."""
        txns = (
            self.db.query(BankStatementTransaction)
            .filter(
                BankStatementTransaction.organization_id == ctx.organization_id,
                BankStatementTransaction.bank_account_id == bank_account_id,
                BankStatementTransaction.is_reconciled.is_(False),
            )
            .all()
        )
        matches: list[ReconciliationMatch] = []
        for txn in txns:
            amt = abs(Decimal(str(txn.amount)))
            payment = (
                self.db.query(Payment)
                .filter(
                    Payment.organization_id == ctx.organization_id,
                    Payment.amount == amt,
                    Payment.payment_date == txn.transaction_date,
                )
                .first()
            )
            if payment:
                match = ReconciliationMatch(
                    organization_id=ctx.organization_id,
                    bank_statement_transaction_id=txn.id,
                    matched_entity_type="payment",
                    matched_entity_id=payment.id,
                    match_confidence=Decimal("0.9"),
                )
                txn.is_reconciled = True
                self.db.add(match)
                matches.append(match)

        self.db.flush()
        return matches

    def _get_bank_account(self, ctx: OrganizationContext, bank_account_id: UUID) -> BankAccount:
        acct = (
            self.db.query(BankAccount)
            .filter(
                BankAccount.id == bank_account_id,
                BankAccount.organization_id == ctx.organization_id,
            )
            .first()
        )
        if not acct:
            raise NotFoundError("Bank account not found")
        return acct
