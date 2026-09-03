from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.core.exceptions import IdempotencyConflict, ValidationError
from app.core.logging import OrganizationContext
from app.domain.accounting.engine import AccountingEngine
from app.domain.accounting.validation import validate_balanced_lines
from app.models.entities import (
    AccountType,
    ChartOfAccount,
    JournalEntryLine,
    Organization,
)


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    org = Organization(name="Test Org")
    session.add(org)
    session.commit()
    yield session, org
    session.close()


@pytest.fixture
def accounts(db):
    session, org = db
    expense = ChartOfAccount(
        organization_id=org.id, code="5000", name="Expenses", account_type=AccountType.expense
    )
    payable = ChartOfAccount(
        organization_id=org.id, code="2000", name="Payables", account_type=AccountType.liability
    )
    session.add_all([expense, payable])
    session.commit()
    return expense, payable


def test_debit_must_equal_credit(db, accounts):
    session, org = db
    expense, payable = accounts
    ctx = OrganizationContext(organization_id=org.id)
    engine = AccountingEngine(session)

    with pytest.raises(ValidationError, match="Debits .* must equal credits"):
        engine.create_draft_entry(
            ctx,
            entry_date=date.today(),
            description="Unbalanced",
            lines=[
                {"chart_of_account_id": expense.id, "debit": Decimal("100"), "credit": 0},
                {"chart_of_account_id": payable.id, "debit": 0, "credit": Decimal("50")},
            ],
        )


def test_balanced_entry_posts(db, accounts):
    session, org = db
    expense, payable = accounts
    ctx = OrganizationContext(organization_id=org.id)
    engine = AccountingEngine(session)

    entry = engine.create_draft_entry(
        ctx,
        entry_date=date.today(),
        description="Balanced",
        lines=[
            {"chart_of_account_id": expense.id, "debit": Decimal("100"), "credit": 0},
            {"chart_of_account_id": payable.id, "debit": 0, "credit": Decimal("100")},
        ],
        idempotency_key="test-key-1",
    )
    posted = engine.post_entry(ctx, entry.id)
    session.commit()
    assert posted.status.value == "posted"


def test_idempotency_prevents_duplicate_post(db, accounts):
    session, org = db
    expense, payable = accounts
    ctx = OrganizationContext(organization_id=org.id)
    engine = AccountingEngine(session)
    lines = [
        {"chart_of_account_id": expense.id, "debit": Decimal("100"), "credit": 0},
        {"chart_of_account_id": payable.id, "debit": 0, "credit": Decimal("100")},
    ]
    engine.create_draft_entry(
        ctx, entry_date=date.today(), description="First", lines=lines, idempotency_key="dup-key"
    )
    session.commit()

    with pytest.raises(IdempotencyConflict):
        engine.create_draft_entry(
            ctx, entry_date=date.today(), description="Duplicate", lines=lines, idempotency_key="dup-key"
        )


def test_tenant_isolation_on_coa(db, accounts):
    session, org = db
    expense, _ = accounts
    other_org = Organization(name="Other")
    session.add(other_org)
    session.commit()
    ctx = OrganizationContext(organization_id=other_org.id)
    engine = AccountingEngine(session)

    with pytest.raises(ValidationError, match="Invalid chart of account"):
        engine.create_draft_entry(
            ctx,
            entry_date=date.today(),
            description="Cross tenant",
            lines=[
                {"chart_of_account_id": expense.id, "debit": Decimal("10"), "credit": 0},
                {"chart_of_account_id": expense.id, "debit": 0, "credit": Decimal("10")},
            ],
        )


def test_validate_balanced_lines_minimum():
    with pytest.raises(ValidationError, match="at least two"):
        validate_balanced_lines([JournalEntryLine(debit=10, credit=0)])
