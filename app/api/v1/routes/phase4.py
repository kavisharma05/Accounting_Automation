from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.authz import ensure_org_access, require_read, require_write
from app.api.deps import get_db
from app.core.exceptions import DomainError
from app.core.logging import OrganizationContext
from app.domain.organizations.pilot_config import get_org_account_defaults
from app.models.entities import ChartOfAccount, Organization
from app.schemas.phase4 import ComplianceStatusUpdate, TdsApplyRequest, TdsComputeRequest
from app.services.compliance_service import ComplianceCalendarService
from app.services.tds_service import TdsService

router = APIRouter()


def _tds_payable_id(db: Session, org_id: UUID, override: UUID | None) -> UUID:
    if override:
        return override
    org = db.get(Organization, org_id)
    if org and org.default_tds_payable_account_id:
        return org.default_tds_payable_account_id
    coa = (
        db.query(ChartOfAccount)
        .filter(ChartOfAccount.organization_id == org_id, ChartOfAccount.code == "2200")
        .first()
    )
    if not coa:
        raise HTTPException(422, "TDS payable account (2200) not configured")
    return coa.id


@router.post("/organizations/{org_id}/tds/compute")
def compute_tds(
    org_id: UUID,
    body: TdsComputeRequest,
    db: Session = Depends(get_db),
    ctx: OrganizationContext = Depends(require_read),
):
    ensure_org_access(ctx, org_id)
    try:
        as_of = body.as_of or date.today()
        return TdsService(db).compute(
            ctx, taxable_amount=body.taxable_amount, section=body.section, as_of=as_of
        )
    except DomainError as e:
        raise HTTPException(400, str(e)) from e


@router.get("/organizations/{org_id}/tds/deductions")
def list_tds_deductions(
    org_id: UUID,
    db: Session = Depends(get_db),
    ctx: OrganizationContext = Depends(require_read),
):
    ensure_org_access(ctx, org_id)
    return TdsService(db).list_deductions(ctx)


@router.post("/organizations/{org_id}/payments/{payment_id}/tds")
def apply_tds_to_payment(
    org_id: UUID,
    payment_id: UUID,
    body: TdsApplyRequest,
    db: Session = Depends(get_db),
    ctx: OrganizationContext = Depends(require_write),
):
    ensure_org_access(ctx, org_id)
    try:
        payable_id, _, _ = get_org_account_defaults(db, org_id)
        payable = body.payable_account_id or payable_id
        tds_payable = _tds_payable_id(db, org_id, body.tds_payable_account_id)
        deduction = TdsService(db).apply_to_payment(
            ctx,
            payment_id,
            section=body.section,
            tds_payable_account_id=tds_payable,
            payable_account_id=payable,
        )
        db.commit()
        return {
            "id": str(deduction.id),
            "tds_section": deduction.tds_section,
            "tds_amount": str(deduction.tds_amount),
            "journal_entry_id": str(deduction.journal_entry_id),
        }
    except DomainError as e:
        db.rollback()
        raise HTTPException(400, str(e)) from e


@router.get("/organizations/{org_id}/compliance-calendar")
def list_compliance_calendar(
    org_id: UUID,
    days_ahead: int = Query(90, le=365),
    db: Session = Depends(get_db),
    ctx: OrganizationContext = Depends(require_read),
):
    ensure_org_access(ctx, org_id)
    return ComplianceCalendarService(db).list_entries(ctx, days_ahead=days_ahead)


@router.post("/organizations/{org_id}/compliance-calendar/generate")
def generate_compliance_calendar(
    org_id: UUID,
    months_ahead: int = Query(3, le=12),
    db: Session = Depends(get_db),
    ctx: OrganizationContext = Depends(require_write),
):
    ensure_org_access(ctx, org_id)
    entries = ComplianceCalendarService(db).generate_upcoming(ctx, months_ahead=months_ahead)
    db.commit()
    return {"created": len(entries)}


@router.patch("/organizations/{org_id}/compliance-calendar/{entry_id}")
def update_compliance_entry(
    org_id: UUID,
    entry_id: UUID,
    body: ComplianceStatusUpdate,
    db: Session = Depends(get_db),
    ctx: OrganizationContext = Depends(require_write),
):
    ensure_org_access(ctx, org_id)
    try:
        if body.status == "completed":
            entry = ComplianceCalendarService(db).mark_completed(ctx, entry_id)
        else:
            raise HTTPException(422, "Only completed status supported")
        db.commit()
        return {"id": str(entry.id), "status": entry.status.value}
    except DomainError as e:
        db.rollback()
        raise HTTPException(400, str(e)) from e
