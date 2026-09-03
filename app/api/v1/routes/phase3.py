from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.api.authz import ensure_org_access, require_read, require_write
from app.api.deps import get_db
from app.core.exceptions import DomainError
from app.core.logging import OrganizationContext
from app.domain.organizations.pilot_config import (
    get_org_account_defaults,
    get_sales_account_defaults,
)
from app.models.entities import (
    ApprovalRequest,
    CreditNote,
    DebitNote,
    Invoice,
    InvoiceLineItem,
    InvoiceStatus,
    InvoiceType,
    Party,
)
from app.schemas.phase3 import (
    CreditNoteCreate,
    DebitNoteCreate,
    EInvoiceResponse,
    InvoiceResponse,
    NoteResponse,
    SalesInvoiceCreate,
)
from app.services.einvoice_service import EInvoiceService
from app.services.gstr_service import GstrService
from app.services.invoice_service import InvoiceService
from app.services.note_service import NoteService
from app.services.search_service import SearchService

router = APIRouter()


@router.post("/organizations/{org_id}/sales-invoices", response_model=InvoiceResponse)
def create_sales_invoice(
    org_id: UUID,
    body: SalesInvoiceCreate,
    db: Session = Depends(get_db),
    ctx: OrganizationContext = Depends(require_write),
):
    ensure_org_access(ctx, org_id)
    party = db.get(Party, body.party_id)
    if not party or party.organization_id != org_id:
        raise HTTPException(404, "Party not found")

    total = body.total if body.total is not None else body.subtotal + body.tax_total
    inv = Invoice(
        organization_id=org_id,
        party_id=body.party_id,
        invoice_type=InvoiceType.sales,
        invoice_number=body.invoice_number,
        invoice_date=body.invoice_date,
        subtotal=body.subtotal,
        tax_total=body.tax_total,
        total=total,
        status=InvoiceStatus.pending_approval,
    )
    db.add(inv)
    db.flush()
    db.add(
        InvoiceLineItem(
            invoice_id=inv.id,
            description=body.line_description,
            quantity=1,
            unit_price=body.subtotal,
            line_total=body.subtotal,
        )
    )
    db.add(
        ApprovalRequest(
            organization_id=org_id,
            entity_type="invoice",
            entity_id=inv.id,
            status="pending",
            requested_by_id=ctx.user_id,
        )
    )
    db.commit()
    db.refresh(inv)
    return inv


@router.post("/organizations/{org_id}/sales-invoices/{invoice_id}/post", response_model=InvoiceResponse)
def post_sales_invoice(
    org_id: UUID,
    invoice_id: UUID,
    db: Session = Depends(get_db),
    ctx: OrganizationContext = Depends(require_write),
):
    ensure_org_access(ctx, org_id)
    try:
        receivable_id, revenue_id, output_tax_id = get_sales_account_defaults(db, org_id)
        inv = InvoiceService(db).confirm_and_post(
            ctx,
            invoice_id,
            receivable_account_id=receivable_id,
            revenue_account_id=revenue_id,
            output_tax_account_id=output_tax_id,
        )
        db.commit()
        return inv
    except DomainError as e:
        db.rollback()
        raise HTTPException(400, str(e)) from e


@router.post("/organizations/{org_id}/credit-notes", response_model=NoteResponse)
def create_credit_note(
    org_id: UUID,
    body: CreditNoteCreate,
    db: Session = Depends(get_db),
    ctx: OrganizationContext = Depends(require_write),
):
    ensure_org_access(ctx, org_id)
    try:
        note = NoteService(db).create_credit_note(
            ctx,
            original_invoice_id=body.original_invoice_id,
            note_number=body.note_number,
            note_date=body.note_date,
            subtotal=body.subtotal,
            tax_total=body.tax_total,
            reason=body.reason,
        )
        db.commit()
        return note
    except DomainError as e:
        db.rollback()
        raise HTTPException(400, str(e)) from e


@router.post("/organizations/{org_id}/credit-notes/{note_id}/post", response_model=NoteResponse)
def post_credit_note(
    org_id: UUID,
    note_id: UUID,
    db: Session = Depends(get_db),
    ctx: OrganizationContext = Depends(require_write),
):
    ensure_org_access(ctx, org_id)
    try:
        note = (
            db.query(CreditNote)
            .filter(CreditNote.id == note_id, CreditNote.organization_id == org_id)
            .first()
        )
        if not note:
            raise HTTPException(404, "Credit note not found")
        inv = db.get(Invoice, note.original_invoice_id)
        kwargs: dict = {}
        if inv and inv.invoice_type == InvoiceType.purchase:
            expense_id, payable_id, input_tax_id = get_org_account_defaults(db, org_id)
            kwargs = {
                "expense_account_id": expense_id,
                "payable_account_id": payable_id,
                "input_tax_account_id": input_tax_id,
            }
        else:
            receivable_id, revenue_id, output_tax_id = get_sales_account_defaults(db, org_id)
            kwargs = {
                "receivable_account_id": receivable_id,
                "revenue_account_id": revenue_id,
                "output_tax_account_id": output_tax_id,
            }
        posted = NoteService(db).post_credit_note(ctx, note_id, **kwargs)
        db.commit()
        return posted
    except DomainError as e:
        db.rollback()
        raise HTTPException(400, str(e)) from e


@router.post("/organizations/{org_id}/debit-notes", response_model=NoteResponse)
def create_debit_note(
    org_id: UUID,
    body: DebitNoteCreate,
    db: Session = Depends(get_db),
    ctx: OrganizationContext = Depends(require_write),
):
    ensure_org_access(ctx, org_id)
    try:
        note = NoteService(db).create_debit_note(
            ctx,
            original_invoice_id=body.original_invoice_id,
            note_number=body.note_number,
            note_date=body.note_date,
            subtotal=body.subtotal,
            tax_total=body.tax_total,
            reason=body.reason,
        )
        db.commit()
        return note
    except DomainError as e:
        db.rollback()
        raise HTTPException(400, str(e)) from e


@router.post("/organizations/{org_id}/debit-notes/{note_id}/post", response_model=NoteResponse)
def post_debit_note(
    org_id: UUID,
    note_id: UUID,
    db: Session = Depends(get_db),
    ctx: OrganizationContext = Depends(require_write),
):
    ensure_org_access(ctx, org_id)
    try:
        note = (
            db.query(DebitNote)
            .filter(DebitNote.id == note_id, DebitNote.organization_id == org_id)
            .first()
        )
        if not note:
            raise HTTPException(404, "Debit note not found")
        inv = db.get(Invoice, note.original_invoice_id)
        kwargs: dict = {}
        if inv and inv.invoice_type == InvoiceType.purchase:
            expense_id, payable_id, input_tax_id = get_org_account_defaults(db, org_id)
            kwargs = {
                "expense_account_id": expense_id,
                "payable_account_id": payable_id,
                "input_tax_account_id": input_tax_id,
            }
        else:
            receivable_id, revenue_id, output_tax_id = get_sales_account_defaults(db, org_id)
            kwargs = {
                "receivable_account_id": receivable_id,
                "revenue_account_id": revenue_id,
                "output_tax_account_id": output_tax_id,
            }
        posted = NoteService(db).post_debit_note(ctx, note_id, **kwargs)
        db.commit()
        return posted
    except DomainError as e:
        db.rollback()
        raise HTTPException(400, str(e)) from e


@router.get("/organizations/{org_id}/gstr/gstr1")
def gstr1_worksheet(
    org_id: UUID,
    period_start: date = Query(...),
    period_end: date = Query(...),
    db: Session = Depends(get_db),
    ctx: OrganizationContext = Depends(require_read),
):
    ensure_org_access(ctx, org_id)
    return GstrService(db).gstr1_rows(ctx, period_start=period_start, period_end=period_end)


@router.get("/organizations/{org_id}/gstr/gstr3b")
def gstr3b_summary(
    org_id: UUID,
    period_start: date = Query(...),
    period_end: date = Query(...),
    db: Session = Depends(get_db),
    ctx: OrganizationContext = Depends(require_read),
):
    ensure_org_access(ctx, org_id)
    return GstrService(db).gstr3b_summary(ctx, period_start=period_start, period_end=period_end)


@router.get("/organizations/{org_id}/reports/gstr1.xlsx")
def export_gstr1(
    org_id: UUID,
    period_start: date = Query(...),
    period_end: date = Query(...),
    db: Session = Depends(get_db),
    ctx: OrganizationContext = Depends(require_read),
):
    ensure_org_access(ctx, org_id)
    content = GstrService(db).export_gstr1_excel(
        ctx, period_start=period_start, period_end=period_end
    )
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=gstr1.xlsx"},
    )


@router.post("/organizations/{org_id}/invoices/{invoice_id}/einvoice", response_model=EInvoiceResponse)
async def generate_einvoice(
    org_id: UUID,
    invoice_id: UUID,
    db: Session = Depends(get_db),
    ctx: OrganizationContext = Depends(require_write),
):
    ensure_org_access(ctx, org_id)
    try:
        record = await EInvoiceService(db).request_einvoice(ctx, invoice_id)
        db.commit()
        return record
    except DomainError as e:
        db.rollback()
        raise HTTPException(400, str(e)) from e


@router.get("/organizations/{org_id}/search/invoices")
def search_invoices(
    org_id: UUID,
    q: str = Query(..., min_length=1),
    invoice_type: str | None = None,
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
    ctx: OrganizationContext = Depends(require_read),
):
    ensure_org_access(ctx, org_id)
    return SearchService(db).search_invoices(
        ctx, q=q, invoice_type=invoice_type, limit=limit
    )
