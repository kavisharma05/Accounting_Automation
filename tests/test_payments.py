"""Phase 2: payments, partial application, period lock."""

from datetime import date
from decimal import Decimal

import pytest

from app.core.exceptions import PostingError, ValidationError
from app.core.logging import OrganizationContext
from app.domain.accounting.engine import AccountingEngine
from app.domain.organizations.coa_seed import seed_chart_of_accounts
from app.domain.organizations.pilot_config import configure_pilot_accounts
from app.models.entities import (
    Invoice,
    InvoiceStatus,
    InvoiceType,
    Party,
    PartyType,
)
from app.services.payment_service import PaymentService


@pytest.fixture
def payment_setup(db):
    session, org = db
    seed_chart_of_accounts(session, org.id)
    configure_pilot_accounts(session, org.id, auto_from_coa=True)
    session.flush()
    session.refresh(org)

    party = Party(
        organization_id=org.id,
        party_type=PartyType.vendor,
        name="Vendor",
        gstin="29AABCU9603R1ZM",
    )
    session.add(party)
    session.flush()

    from app.models.entities import ChartOfAccount

    expense = session.query(ChartOfAccount).filter_by(code="5000").first()
    payable = session.query(ChartOfAccount).filter_by(code="2000").first()
    gst = session.query(ChartOfAccount).filter_by(code="1400").first()
    bank = session.query(ChartOfAccount).filter_by(code="1010").first()

    inv = Invoice(
        organization_id=org.id,
        party_id=party.id,
        invoice_type=InvoiceType.purchase,
        invoice_number="INV-PAY-1",
        invoice_date=date.today(),
        subtotal=Decimal("10000"),
        tax_total=Decimal("1800"),
        total=Decimal("11800"),
        status=InvoiceStatus.posted,
    )
    session.add(inv)
    session.flush()

    ctx = OrganizationContext(organization_id=org.id)
    engine = AccountingEngine(session)
    entry = engine.create_draft_entry(
        ctx,
        entry_date=date.today(),
        description="Invoice",
        lines=[
            {"chart_of_account_id": expense.id, "debit": Decimal("10000"), "credit": 0},
            {"chart_of_account_id": gst.id, "debit": Decimal("1800"), "credit": 0},
            {"chart_of_account_id": payable.id, "debit": 0, "credit": Decimal("11800")},
        ],
        source_type="invoice",
        source_id=inv.id,
    )
    engine.post_entry(ctx, entry.id)
    session.commit()

    return session, org, party, inv, payable, bank, ctx


def test_partial_payment(payment_setup):
    session, org, party, inv, payable, bank, ctx = payment_setup
    svc = PaymentService(session)

    payment = svc.create_and_post_payment(
        ctx,
        party_id=party.id,
        amount=Decimal("5000"),
        payment_date=date.today(),
        payable_account_id=payable.id,
        bank_account_id=bank.id,
        reference="UTR123",
        applications=[{"invoice_id": inv.id, "amount_applied": Decimal("5000")}],
    )
    session.commit()

    assert payment.journal_entry_id is not None
    outstanding = svc.invoice_outstanding(inv.id)
    assert outstanding == Decimal("6800")


def test_over_application_rejected(payment_setup):
    session, org, party, inv, payable, bank, ctx = payment_setup
    svc = PaymentService(session)

    with pytest.raises(ValidationError, match="outstanding"):
        svc.create_and_post_payment(
            ctx,
            party_id=party.id,
            amount=Decimal("5000"),
            payment_date=date.today(),
            payable_account_id=payable.id,
            bank_account_id=bank.id,
            applications=[{"invoice_id": inv.id, "amount_applied": Decimal("20000")}],
        )


def test_period_lock_blocks_posting(payment_setup):
    session, org, party, inv, payable, bank, ctx = payment_setup
    org.locked_through_date = date.today()
    session.commit()

    engine = AccountingEngine(session)
    entry = engine.create_draft_entry(
        ctx,
        entry_date=date.today(),
        description="Blocked",
        lines=[
            {"chart_of_account_id": payable.id, "debit": Decimal("100"), "credit": 0},
            {"chart_of_account_id": bank.id, "debit": 0, "credit": Decimal("100")},
        ],
    )
    with pytest.raises(PostingError, match="Period locked"):
        engine.post_entry(ctx, entry.id)


def test_duplicate_payment_reference(payment_setup):
    session, org, party, inv, payable, bank, ctx = payment_setup
    svc = PaymentService(session)

    svc.create_and_post_payment(
        ctx,
        party_id=party.id,
        amount=Decimal("1000"),
        payment_date=date.today(),
        payable_account_id=payable.id,
        bank_account_id=bank.id,
        reference="DUP-REF",
    )
    session.commit()

    with pytest.raises(ValidationError, match="Duplicate payment"):
        svc.create_and_post_payment(
            ctx,
            party_id=party.id,
            amount=Decimal("1000"),
            payment_date=date.today(),
            payable_account_id=payable.id,
            bank_account_id=bank.id,
            reference="DUP-REF",
        )
