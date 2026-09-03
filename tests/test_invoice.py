from datetime import date
from decimal import Decimal

import pytest

from app.core.exceptions import ValidationError
from app.core.logging import OrganizationContext
from app.domain.organizations.coa_seed import seed_chart_of_accounts
from app.integrations.protocols import DocumentExtraction, ExtractionLineItem
from app.models.entities import ChartOfAccount, Party, PartyType
from app.services.invoice_service import InvoiceService


def test_seed_coa(db):
    session, org = db
    accounts = seed_chart_of_accounts(session, org.id)
    session.commit()
    assert len(accounts) == 10
    codes = {a.code for a in accounts}
    assert "5000" in codes
    assert "2000" in codes


def test_duplicate_invoice_rejected(db):
    session, org = db
    seed_chart_of_accounts(session, org.id)
    party = Party(
        organization_id=org.id,
        party_type=PartyType.vendor,
        name="Vendor A",
        gstin="29AABCU9603R1ZM",
    )
    session.add(party)
    session.commit()

    ctx = OrganizationContext(organization_id=org.id)
    svc = InvoiceService(session)
    extraction = DocumentExtraction(
        vendor_name="Vendor A",
        vendor_gstin="29AABCU9603R1ZM",
        invoice_number="INV-001",
        invoice_date=date.today(),
        invoice_type="purchase",
        subtotal=Decimal("1000"),
        tax_total=Decimal("180"),
        total=Decimal("1180"),
        line_items=[
            ExtractionLineItem(
                description="Item",
                quantity=Decimal("1"),
                unit_price=Decimal("1000"),
                tax_rate=Decimal("18"),
                line_total=Decimal("1000"),
            )
        ],
        confidence=0.9,
        raw={},
    )

    expense = session.query(ChartOfAccount).filter_by(code="5000").first()
    payable = session.query(ChartOfAccount).filter_by(code="2000").first()
    gst = session.query(ChartOfAccount).filter_by(code="1400").first()

    svc.create_from_extraction(
        ctx,
        extraction,
        expense_account_id=expense.id,
        payable_account_id=payable.id,
        input_tax_account_id=gst.id,
    )
    session.commit()

    with pytest.raises(ValidationError, match="Duplicate invoice"):
        svc.create_from_extraction(
            ctx,
            extraction,
            expense_account_id=expense.id,
            payable_account_id=payable.id,
            input_tax_account_id=gst.id,
        )
