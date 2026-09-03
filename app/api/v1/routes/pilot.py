from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.exceptions import DomainError, ValidationError
from app.core.logging import OrganizationContext
from app.domain.organizations.pilot_config import configure_pilot_accounts, get_org_account_defaults
from app.models.entities import ApprovalRequest, Invoice
from app.schemas.common import PilotConfigResponse, PilotConfigUpdate
from app.services.document_service import DocumentService
from app.services.invoice_service import InvoiceService

router = APIRouter()


@router.patch("/organizations/{org_id}/pilot-config", response_model=PilotConfigResponse)
def update_pilot_config(
    org_id: UUID,
    body: PilotConfigUpdate,
    db: Session = Depends(get_db),
):
    try:
        org = configure_pilot_accounts(
            db,
            org_id,
            expense_account_id=body.expense_account_id,
            payable_account_id=body.payable_account_id,
            input_tax_account_id=body.input_tax_account_id,
            receivable_account_id=body.receivable_account_id,
            revenue_account_id=body.revenue_account_id,
            output_tax_account_id=body.output_tax_account_id,
            auto_from_coa=body.auto_from_coa,
        )
        db.commit()
        return PilotConfigResponse(
            organization_id=org.id,
            default_expense_account_id=org.default_expense_account_id,
            default_payable_account_id=org.default_payable_account_id,
            default_input_tax_account_id=org.default_input_tax_account_id,
            default_receivable_account_id=org.default_receivable_account_id,
            default_revenue_account_id=org.default_revenue_account_id,
            default_output_tax_account_id=org.default_output_tax_account_id,
        )
    except DomainError as e:
        db.rollback()
        raise HTTPException(400, str(e)) from e


@router.get("/organizations/{org_id}/pilot-config", response_model=PilotConfigResponse)
def get_pilot_config(org_id: UUID, db: Session = Depends(get_db)):
    from app.models.entities import Organization

    org = db.get(Organization, org_id)
    if not org:
        raise HTTPException(404, "Organization not found")
    return PilotConfigResponse(
        organization_id=org.id,
        default_expense_account_id=org.default_expense_account_id,
        default_payable_account_id=org.default_payable_account_id,
        default_input_tax_account_id=org.default_input_tax_account_id,
        default_receivable_account_id=org.default_receivable_account_id,
        default_revenue_account_id=org.default_revenue_account_id,
        default_output_tax_account_id=org.default_output_tax_account_id,
    )


@router.post("/organizations/{org_id}/documents/upload")
async def upload_document(
    org_id: UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    ctx = OrganizationContext(organization_id=org_id)
    content = await file.read()
    mime = file.content_type or "application/octet-stream"
    doc_svc = DocumentService(db)
    doc = await doc_svc.upload(ctx, content, mime)
    db.commit()
    return {"document_id": str(doc.id), "sha256": doc.sha256}


@router.post("/organizations/{org_id}/documents/{document_id}/extract")
async def extract_document(
    org_id: UUID,
    document_id: UUID,
    db: Session = Depends(get_db),
):
    ctx = OrganizationContext(organization_id=org_id)
    doc_svc = DocumentService(db)
    record = await doc_svc.extract(ctx, document_id)
    db.commit()
    return {"extraction_id": str(record.id), "data": record.extracted_data}


@router.post("/organizations/{org_id}/documents/{document_id}/propose-invoice")
async def propose_invoice_from_document(
    org_id: UUID,
    document_id: UUID,
    db: Session = Depends(get_db),
):
    from datetime import date
    from decimal import Decimal

    from app.integrations.protocols import DocumentExtraction, ExtractionLineItem

    ctx = OrganizationContext(organization_id=org_id)
    doc_svc = DocumentService(db)
    record = await doc_svc.extract(ctx, document_id)
    data = record.extracted_data

    extraction = DocumentExtraction(
        vendor_name=data.get("vendor_name"),
        vendor_gstin=data.get("vendor_gstin"),
        invoice_number=data.get("invoice_number"),
        invoice_date=date.fromisoformat(data["invoice_date"]) if data.get("invoice_date") else None,
        invoice_type=data.get("invoice_type", "purchase"),
        subtotal=Decimal(data.get("subtotal", "0")),
        tax_total=Decimal(data.get("tax_total", "0")),
        total=Decimal(data.get("total", "0")),
        line_items=[
            ExtractionLineItem(
                description="Line",
                quantity=Decimal("1"),
                unit_price=Decimal(data.get("subtotal", "0")),
                tax_rate=Decimal("18"),
                line_total=Decimal(data.get("subtotal", "0")),
            )
        ],
        confidence=float(data.get("confidence", 0)),
        raw=data,
    )

    expense_id, payable_id, tax_id = get_org_account_defaults(db, org_id)
    inv_svc = InvoiceService(db)
    inv = inv_svc.create_from_extraction(
        ctx,
        extraction,
        expense_account_id=expense_id,
        payable_account_id=payable_id,
        input_tax_account_id=tax_id,
    )
    db.commit()
    return {
        "invoice_id": str(inv.id),
        "invoice_number": inv.invoice_number,
        "total": str(inv.total),
        "status": inv.status.value,
    }


@router.post("/organizations/{org_id}/invoices/confirm-pending")
def confirm_pending_invoice(org_id: UUID, db: Session = Depends(get_db)):
    ctx = OrganizationContext(organization_id=org_id)
    pending = (
        db.query(ApprovalRequest)
        .filter(
            ApprovalRequest.organization_id == org_id,
            ApprovalRequest.status == "pending",
            ApprovalRequest.entity_type == "invoice",
        )
        .order_by(ApprovalRequest.created_at.desc())
        .first()
    )
    if not pending:
        raise HTTPException(404, "No pending invoice approval")

    expense_id, payable_id, tax_id = get_org_account_defaults(db, org_id)
    inv_svc = InvoiceService(db)
    try:
        inv = inv_svc.confirm_and_post(
            ctx,
            pending.entity_id,
            expense_account_id=expense_id,
            payable_account_id=payable_id,
            input_tax_account_id=tax_id,
        )
        db.commit()
        return {
            "invoice_id": str(inv.id),
            "journal_entry_id": str(inv.journal_entry_id),
            "status": inv.status.value,
        }
    except ValidationError as e:
        db.rollback()
        raise HTTPException(422, str(e)) from e


@router.get("/organizations/{org_id}/invoices/pending")
def list_pending_invoices(org_id: UUID, db: Session = Depends(get_db)):
    pending = (
        db.query(ApprovalRequest, Invoice)
        .join(Invoice, Invoice.id == ApprovalRequest.entity_id)
        .filter(
            ApprovalRequest.organization_id == org_id,
            ApprovalRequest.status == "pending",
            ApprovalRequest.entity_type == "invoice",
        )
        .all()
    )
    return [
        {
            "approval_id": str(a.id),
            "invoice_id": str(i.id),
            "invoice_number": i.invoice_number,
            "total": str(i.total),
            "status": i.status.value,
        }
        for a, i in pending
    ]
