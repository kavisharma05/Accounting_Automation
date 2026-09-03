"""Phase 4: TDS computation and compliance calendar."""

from datetime import date
from decimal import Decimal

import pytest

from app.core.logging import OrganizationContext
from app.domain.accounting.engine import AccountingEngine
from app.domain.organizations.coa_seed import seed_chart_of_accounts
from app.domain.organizations.pilot_config import configure_pilot_accounts
from app.domain.tax.default_rules import seed_default_tax_rules
from app.domain.tax.engine import TaxEngine
from app.models.entities import Organization, Party, PartyType, Payment
from app.services.compliance_service import ComplianceCalendarService
from app.services.tds_service import TdsService


@pytest.fixture
def tds_setup(db):
    session, org = db
    seed_chart_of_accounts(session, org.id)
    configure_pilot_accounts(session, org.id, auto_from_coa=True)
    seed_default_tax_rules(session, org.id)
    session.flush()

    party = Party(organization_id=org.id, party_type=PartyType.vendor, name="Contractor")
    session.add(party)
    session.flush()

    from app.models.entities import ChartOfAccount

    payable = session.query(ChartOfAccount).filter_by(code="2000").first()
    bank = session.query(ChartOfAccount).filter_by(code="1010").first()
    tds_payable = session.query(ChartOfAccount).filter_by(code="2200").first()

    payment = Payment(
        organization_id=org.id,
        party_id=party.id,
        amount=Decimal("50000"),
        payment_date=date.today(),
        reference="TDS-PAY-1",
    )
    session.add(payment)
    session.flush()

    ctx = OrganizationContext(organization_id=org.id)
    engine = AccountingEngine(session)
    entry = engine.create_draft_entry(
        ctx,
        entry_date=date.today(),
        description="Vendor payment",
        lines=[
            {"chart_of_account_id": payable.id, "debit": Decimal("50000"), "credit": 0},
            {"chart_of_account_id": bank.id, "debit": 0, "credit": Decimal("50000")},
        ],
        source_type="payment",
        source_id=payment.id,
    )
    engine.post_entry(ctx, entry.id)
    payment.journal_entry_id = entry.id
    session.commit()

    return session, org, party, payment, payable, tds_payable, ctx


def test_compute_tds_contractor(tds_setup):
    session, org, party, payment, payable, tds_payable, ctx = tds_setup
    result = TaxEngine(session).compute_tds(
        organization_id=org.id,
        as_of=date.today(),
        taxable_amount=Decimal("50000"),
        section="194C",
    )
    assert result["applicable"] is True
    assert result["tds_amount"] == 500.0  # 1% of 50000


def test_compute_tds_below_threshold(tds_setup):
    session, org, party, payment, payable, tds_payable, ctx = tds_setup
    result = TaxEngine(session).compute_tds(
        organization_id=org.id,
        as_of=date.today(),
        taxable_amount=Decimal("10000"),
        section="194C",
    )
    assert result["applicable"] is False


def test_apply_tds_to_payment(tds_setup):
    session, org, party, payment, payable, tds_payable, ctx = tds_setup
    svc = TdsService(session)
    deduction = svc.apply_to_payment(
        ctx,
        payment.id,
        section="194C",
        tds_payable_account_id=tds_payable.id,
        payable_account_id=payable.id,
    )
    session.commit()
    assert deduction.tds_amount == Decimal("500")
    assert deduction.journal_entry_id is not None


def test_compliance_calendar_generate(tds_setup):
    session, org, party, payment, payable, tds_payable, ctx = tds_setup
    svc = ComplianceCalendarService(session)
    created = svc.generate_upcoming(ctx, months_ahead=2)
    session.commit()
    assert len(created) >= 3
    entries = svc.list_entries(ctx)
    types = {e["entry_type"] for e in entries}
    assert "gstr3b" in types
    assert "tds_deposit" in types
