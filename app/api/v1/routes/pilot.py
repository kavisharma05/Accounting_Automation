from uuid import UUID

import logging

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import get_db

logger = logging.getLogger(__name__)
from app.core.exceptions import DomainError, NotFoundError, ValidationError
from app.core.logging import OrganizationContext
from app.domain.organizations.pilot_config import configure_pilot_accounts, get_org_account_defaults
from app.models.entities import ApprovalRequest, Invoice, Party
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
    if content[:4] == b"%PDF":
        mime = "application/pdf"
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
    from app.integrations.document_understanding.parse import extraction_from_dict

    ctx = OrganizationContext(organization_id=org_id)
    doc_svc = DocumentService(db)
    try:
        record = await doc_svc.extract(ctx, document_id)
    except Exception as exc:
        logger.exception("Bill extraction failed for document %s", document_id)
        raise HTTPException(
            422,
            "Could not read that bill. Use a clear photo (JPG or PNG), or a one-page PDF.",
        ) from exc
    extraction = extraction_from_dict(record.extracted_data)

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


def _post_pending_invoice(db: Session, org_id: UUID, invoice_id: UUID) -> dict:
    ctx = OrganizationContext(organization_id=org_id)
    expense_id, payable_id, tax_id = get_org_account_defaults(db, org_id)
    inv = InvoiceService(db).confirm_and_post(
        ctx,
        invoice_id,
        expense_account_id=expense_id,
        payable_account_id=payable_id,
        input_tax_account_id=tax_id,
    )
    return {
        "invoice_id": str(inv.id),
        "journal_entry_id": str(inv.journal_entry_id),
        "status": inv.status.value,
    }


@router.post("/organizations/{org_id}/invoices/confirm-pending")
def confirm_pending_invoice(org_id: UUID, db: Session = Depends(get_db)):
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
    try:
        result = _post_pending_invoice(db, org_id, pending.entity_id)
        db.commit()
        return result
    except ValidationError as e:
        db.rollback()
        raise HTTPException(422, str(e)) from e


@router.post("/organizations/{org_id}/invoices/{invoice_id}/reject")
def reject_invoice(org_id: UUID, invoice_id: UUID, db: Session = Depends(get_db)):
    ctx = OrganizationContext(organization_id=org_id)
    try:
        inv = InvoiceService(db).reject_pending(ctx, invoice_id)
        db.commit()
        return {"invoice_id": str(inv.id), "status": inv.status.value}
    except NotFoundError as e:
        db.rollback()
        raise HTTPException(404, str(e)) from e
    except ValidationError as e:
        db.rollback()
        raise HTTPException(422, str(e)) from e


@router.post("/organizations/{org_id}/invoices/{invoice_id}/confirm")
def confirm_invoice(org_id: UUID, invoice_id: UUID, db: Session = Depends(get_db)):
    try:
        result = _post_pending_invoice(db, org_id, invoice_id)
        db.commit()
        return result
    except NotFoundError as e:
        db.rollback()
        raise HTTPException(404, str(e)) from e
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
    rows = []
    for approval, invoice in pending:
        party = db.get(Party, invoice.party_id)
        rows.append(
            {
                "approval_id": str(approval.id),
                "invoice_id": str(invoice.id),
                "invoice_number": invoice.invoice_number,
                "invoice_date": invoice.invoice_date.isoformat(),
                "invoice_type": invoice.invoice_type.value,
                "party_name": party.name if party else "",
                "total": str(invoice.total),
                "status": invoice.status.value,
            }
        )
    return rows
