"""Phase 3: sales invoices, credit/debit notes, GSTR, e-invoice."""

from datetime import date
from decimal import Decimal

import pytest

from app.core.exceptions import ValidationError
from app.core.logging import OrganizationContext
from app.domain.accounting.engine import AccountingEngine
from app.domain.organizations.coa_seed import seed_chart_of_accounts
from app.domain.organizations.pilot_config import configure_pilot_accounts
from app.domain.tax.engine import TaxEngine
from app.models.entities import (
    Invoice,
    InvoiceStatus,
    InvoiceType,
    Party,
    PartyType,
)
from app.services.gstr_service import GstrService
from app.services.invoice_service import InvoiceService
from app.services.note_service import NoteService


@pytest.fixture
def phase3_setup(db):
    session, org = db
    seed_chart_of_accounts(session, org.id)
    configure_pilot_accounts(session, org.id, auto_from_coa=True)
    session.flush()
    session.refresh(org)

    customer = Party(
        organization_id=org.id,
        party_type=PartyType.customer,
        name="Retail Customer",
        gstin="29AABCU9603R1ZN",
    )
    vendor = Party(
        organization_id=org.id,
        party_type=PartyType.vendor,
        name="Vendor",
        gstin="29AABCU9603R1ZM",
    )
    session.add_all([customer, vendor])
    session.flush()

    from app.models.entities import ChartOfAccount

    receivable = session.query(ChartOfAccount).filter_by(code="1100").first()
    revenue = session.query(ChartOfAccount).filter_by(code="4000").first()
    output_gst = session.query(ChartOfAccount).filter_by(code="2100").first()
    expense = session.query(ChartOfAccount).filter_by(code="5000").first()
    payable = session.query(ChartOfAccount).filter_by(code="2000").first()
    input_gst = session.query(ChartOfAccount).filter_by(code="1400").first()

    ctx = OrganizationContext(organization_id=org.id)

    return {
        "session": session,
        "org": org,
        "customer": customer,
        "vendor": vendor,
        "ctx": ctx,
        "receivable": receivable,
        "revenue": revenue,
        "output_gst": output_gst,
        "expense": expense,
        "payable": payable,
        "input_gst": input_gst,
    }


def _post_sales_invoice(setup, *, number: str, subtotal=Decimal("10000"), tax=Decimal("1800")):
    session = setup["session"]
    inv = Invoice(
        organization_id=setup["org"].id,
        party_id=setup["customer"].id,
        invoice_type=InvoiceType.sales,
        invoice_number=number,
        invoice_date=date.today(),
        subtotal=subtotal,
        tax_total=tax,
        total=subtotal + tax,
        status=InvoiceStatus.pending_approval,
    )
    session.add(inv)
    session.flush()

    snap = TaxEngine(session).compute_gst(
        organization_id=setup["org"].id,
        as_of=inv.invoice_date,
        taxable_amount=subtotal,
        is_interstate=False,
    )
    inv.tax_computation_snapshot = snap

    InvoiceService(session).confirm_and_post(
        setup["ctx"],
        inv.id,
        receivable_account_id=setup["receivable"].id,
        revenue_account_id=setup["revenue"].id,
        output_tax_account_id=setup["output_gst"].id,
    )
    session.commit()
    session.refresh(inv)
    return inv


def _post_purchase_invoice(setup, *, number: str, subtotal=Decimal("10000"), tax=Decimal("1800")):
    session = setup["session"]
    inv = Invoice(
        organization_id=setup["org"].id,
        party_id=setup["vendor"].id,
        invoice_type=InvoiceType.purchase,
        invoice_number=number,
        invoice_date=date.today(),
        subtotal=subtotal,
        tax_total=tax,
        total=subtotal + tax,
        status=InvoiceStatus.pending_approval,
    )
    session.add(inv)
    session.flush()

    InvoiceService(session).confirm_and_post(
        setup["ctx"],
        inv.id,
        expense_account_id=setup["expense"].id,
        payable_account_id=setup["payable"].id,
        input_tax_account_id=setup["input_gst"].id,
    )
    session.commit()
    session.refresh(inv)
    return inv


def test_sales_invoice_posting(phase3_setup):
    inv = _post_sales_invoice(phase3_setup, number="SINV-1")
    assert inv.status == InvoiceStatus.posted
    assert inv.journal_entry_id is not None


def test_credit_note_reduces_sales_outstanding(phase3_setup):
    inv = _post_sales_invoice(phase3_setup, number="SINV-CN-1")
    note_svc = NoteService(phase3_setup["session"])

    note = note_svc.create_credit_note(
        phase3_setup["ctx"],
        original_invoice_id=inv.id,
        note_number="CN-001",
        note_date=date.today(),
        subtotal=Decimal("2000"),
        tax_total=Decimal("360"),
    )
    note_svc.post_credit_note(
        phase3_setup["ctx"],
        note.id,
        receivable_account_id=phase3_setup["receivable"].id,
        revenue_account_id=phase3_setup["revenue"].id,
        output_tax_account_id=phase3_setup["output_gst"].id,
    )
    phase3_setup["session"].commit()

    adjusted = note_svc.invoice_adjusted_outstanding(inv.id)
    assert adjusted == Decimal("9440")  # 11800 - 2360 credit


def test_credit_note_exceeds_outstanding_rejected(phase3_setup):
    inv = _post_sales_invoice(phase3_setup, number="SINV-CN-2")
    note_svc = NoteService(phase3_setup["session"])

    with pytest.raises(ValidationError, match="exceeds"):
        note_svc.create_credit_note(
            phase3_setup["ctx"],
            original_invoice_id=inv.id,
            note_number="CN-BIG",
            note_date=date.today(),
            subtotal=Decimal("20000"),
            tax_total=Decimal("3600"),
        )


def test_purchase_credit_note(phase3_setup):
    inv = _post_purchase_invoice(phase3_setup, number="PINV-CN-1")
    note_svc = NoteService(phase3_setup["session"])

    note = note_svc.create_credit_note(
        phase3_setup["ctx"],
        original_invoice_id=inv.id,
        note_number="PCN-001",
        note_date=date.today(),
        subtotal=Decimal("1000"),
        tax_total=Decimal("180"),
    )
    posted = note_svc.post_credit_note(
        phase3_setup["ctx"],
        note.id,
        expense_account_id=phase3_setup["expense"].id,
        payable_account_id=phase3_setup["payable"].id,
        input_tax_account_id=phase3_setup["input_gst"].id,
    )
    phase3_setup["session"].commit()
    assert posted.status.value == "posted"


def test_gstr1_worksheet(phase3_setup):
    _post_sales_invoice(phase3_setup, number="GSTR-S1")
    rows = GstrService(phase3_setup["session"]).gstr1_rows(
        phase3_setup["ctx"],
        period_start=date.today().replace(day=1),
        period_end=date.today(),
    )
    assert len(rows) == 1
    assert rows[0]["invoice_number"] == "GSTR-S1"
    assert rows[0]["taxable_value"] == 10000.0


def test_gstr3b_summary(phase3_setup):
    _post_sales_invoice(phase3_setup, number="GSTR-S2")
    _post_purchase_invoice(phase3_setup, number="GSTR-P1")
    summary = GstrService(phase3_setup["session"]).gstr3b_summary(
        phase3_setup["ctx"],
        period_start=date.today().replace(day=1),
        period_end=date.today(),
    )
    assert summary["outward_taxable_supplies"] == 10000.0
    assert summary["input_tax_credit"] == 1800.0
    assert summary["net_tax_payable"] == 0.0


def test_einvoice_generation(phase3_setup):
    import asyncio

    from app.services.einvoice_service import EInvoiceService

    inv = _post_sales_invoice(phase3_setup, number="EINV-1")

    async def _run():
        return await EInvoiceService(phase3_setup["session"]).request_einvoice(
            phase3_setup["ctx"], inv.id
        )

    record = asyncio.run(_run())
    phase3_setup["session"].commit()
    assert record.irn is not None
    assert record.status == "generated"


def test_search_invoices(phase3_setup):
    from app.services.search_service import SearchService

    _post_sales_invoice(phase3_setup, number="SEARCH-XYZ-99")
    results = SearchService(phase3_setup["session"]).search_invoices(
        phase3_setup["ctx"], q="SEARCH-XYZ"
    )
    assert len(results) == 1
    assert results[0]["invoice_number"] == "SEARCH-XYZ-99"
