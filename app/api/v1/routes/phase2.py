from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.api.authz import ensure_org_access, require_read, require_write
from app.api.deps import get_db
from app.core.exceptions import DomainError, IdempotencyConflict
from app.core.logging import OrganizationContext
from app.integrations.factory import get_email_provider
from app.models.entities import Organization
from app.schemas.phase2 import (
    BankAccountCreate,
    BankAccountResponse,
    CAEmailRequest,
    PaymentCreate,
    PaymentResponse,
    PeriodLockUpdate,
)
from app.services.bank_service import BankService
from app.services.dashboard_service import DashboardService
from app.services.payment_service import PaymentService
from app.services.reporting_service import ReportingService

router = APIRouter()


@router.get("/organizations/{org_id}/dashboard")
def dashboard_summary(
    org_id: UUID,
    db: Session = Depends(get_db),
    ctx: OrganizationContext = Depends(require_read),
):
    ensure_org_access(ctx, org_id)
    return DashboardService(db).summary(ctx)


@router.get("/organizations/{org_id}/invoices")
def list_invoices(
    org_id: UUID,
    status: str | None = None,
    db: Session = Depends(get_db),
    ctx: OrganizationContext = Depends(require_read),
):
    ensure_org_access(ctx, org_id)
    return DashboardService(db).list_invoices(ctx, status=status)


@router.get("/organizations/{org_id}/payments")
def list_payments(
    org_id: UUID,
    db: Session = Depends(get_db),
    ctx: OrganizationContext = Depends(require_read),
):
    ensure_org_access(ctx, org_id)
    return DashboardService(db).list_payments(ctx)


@router.post("/organizations/{org_id}/payments", response_model=PaymentResponse)
def create_payment(
    org_id: UUID,
    body: PaymentCreate,
    db: Session = Depends(get_db),
    ctx: OrganizationContext = Depends(require_write),
):
    ensure_org_access(ctx, org_id)
    svc = PaymentService(db)
    try:
        payment = svc.create_and_post_payment(
            ctx,
            party_id=body.party_id,
            amount=body.amount,
            payment_date=body.payment_date,
            payable_account_id=body.payable_account_id,
            bank_account_id=body.bank_account_id,
            reference=body.reference,
            idempotency_key=body.idempotency_key,
            applications=[a.model_dump() for a in body.applications],
        )
        db.commit()
        db.refresh(payment)
        return payment
    except IdempotencyConflict as e:
        db.rollback()
        raise HTTPException(409, str(e)) from e
    except DomainError as e:
        db.rollback()
        raise HTTPException(422, str(e)) from e


@router.post("/organizations/{org_id}/bank-accounts", response_model=BankAccountResponse)
def create_bank_account(
    org_id: UUID,
    body: BankAccountCreate,
    db: Session = Depends(get_db),
    ctx: OrganizationContext = Depends(require_write),
):
    ensure_org_access(ctx, org_id)
    acct = BankService(db).create_bank_account(
        ctx,
        name=body.name,
        chart_of_account_id=body.chart_of_account_id,
        account_number=body.account_number,
        ifsc=body.ifsc,
    )
    db.commit()
    db.refresh(acct)
    return acct


@router.post("/organizations/{org_id}/bank-accounts/{bank_id}/import")
async def import_bank_statement(
    org_id: UUID,
    bank_id: UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    ctx: OrganizationContext = Depends(require_write),
):
    ensure_org_access(ctx, org_id)
    content = (await file.read()).decode("utf-8")
    try:
        txns = BankService(db).import_csv(ctx, bank_id, content)
        db.commit()
        return {"imported": len(txns)}
    except DomainError as e:
        db.rollback()
        raise HTTPException(422, str(e)) from e


@router.post("/organizations/{org_id}/bank-accounts/{bank_id}/reconcile")
def reconcile_bank(
    org_id: UUID,
    bank_id: UUID,
    db: Session = Depends(get_db),
    ctx: OrganizationContext = Depends(require_write),
):
    ensure_org_access(ctx, org_id)
    matches = BankService(db).auto_match(ctx, bank_id)
    db.commit()
    return {"matches": len(matches)}


@router.patch("/organizations/{org_id}/period-lock")
def update_period_lock(
    org_id: UUID,
    body: PeriodLockUpdate,
    db: Session = Depends(get_db),
    ctx: OrganizationContext = Depends(require_write),
):
    ensure_org_access(ctx, org_id)
    if ctx.role not in ("owner", "admin"):
        raise HTTPException(403, "Only owner/admin can lock periods")
    org = db.get(Organization, org_id)
    if not org:
        raise HTTPException(404, "Organization not found")
    org.locked_through_date = body.locked_through_date
    db.commit()
    return {"locked_through_date": body.locked_through_date.isoformat()}


@router.post("/organizations/{org_id}/reports/email-ledger")
async def email_ledger_to_ca(
    org_id: UUID,
    body: CAEmailRequest,
    db: Session = Depends(get_db),
    ctx: OrganizationContext = Depends(require_write),
):
    ensure_org_access(ctx, org_id)
    org = db.get(Organization, org_id)
    if not org:
        raise HTTPException(404, "Organization not found")
    to_email = body.ca_email or org.ca_email
    if not to_email:
        raise HTTPException(422, "CA email not configured")

    excel = ReportingService(db).export_excel(ctx)
    email = get_email_provider()
    await email.send_email(
        to_email,
        subject=f"Ledger export — {org.name}",
        body="Please find attached the general ledger export.",
        attachment=excel,
    )
    if body.ca_email:
        org.ca_email = body.ca_email
        db.commit()
    return {"status": "sent", "to": to_email}
