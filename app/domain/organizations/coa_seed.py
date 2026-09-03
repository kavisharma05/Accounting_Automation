"""Seed minimal Indian SMB chart of accounts on organization creation."""

from uuid import UUID

from sqlalchemy.orm import Session

from app.models.entities import AccountType, ChartOfAccount

DEFAULT_ACCOUNTS = [
    ("1000", "Cash", AccountType.asset),
    ("1010", "Bank", AccountType.asset),
    ("1100", "Accounts Receivable", AccountType.asset),
    ("1400", "Input GST", AccountType.asset),
    ("2000", "Accounts Payable", AccountType.liability),
    ("2100", "Output GST", AccountType.liability),
    ("2200", "TDS Payable", AccountType.liability),
    ("3000", "Owner's Equity", AccountType.equity),
    ("4000", "Sales Revenue", AccountType.revenue),
    ("5000", "General Expense", AccountType.expense),
]


def seed_chart_of_accounts(db: Session, organization_id: UUID) -> list[ChartOfAccount]:
    accounts = []
    for code, name, account_type in DEFAULT_ACCOUNTS:
        coa = ChartOfAccount(
            organization_id=organization_id,
            code=code,
            name=name,
            account_type=account_type,
        )
        db.add(coa)
        accounts.append(coa)
    db.flush()
    return accounts
