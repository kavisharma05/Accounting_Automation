from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.api.deps import get_current_ctx, get_db
from app.core.exceptions import IdempotencyConflict, ValidationError
from app.core.logging import OrganizationContext
from app.core.security import create_access_token, verify_password
from app.domain.accounting.engine import AccountingEngine
from app.domain.organizations.coa_seed import seed_chart_of_accounts
from app.domain.organizations.pilot_config import configure_pilot_accounts
from app.models.entities import ChartOfAccount, Organization, OrganizationMembership, User
from app.schemas.common import (
    ChartOfAccountCreate,
    ChartOfAccountResponse,
    JournalEntryCreate,
    JournalEntryResponse,
    LoginRequest,
    OrganizationCreate,
    OrganizationResponse,
    PhoneMappingCreate,
    TokenResponse,
)
from app.services.reporting_service import ReportingService

router = APIRouter()


@router.get("/health")
def health():
    return {"status": "ok"}


@router.post("/organizations", response_model=OrganizationResponse)
def create_organization(body: OrganizationCreate, db: Session = Depends(get_db)):
    org = Organization(name=body.name, gstin=body.gstin)
    db.add(org)
    db.flush()
    seed_chart_of_accounts(db, org.id)
    configure_pilot_accounts(db, org.id, auto_from_coa=True)
    db.commit()
    db.refresh(org)
    return org


@router.post("/organizations/{org_id}/accounts", response_model=ChartOfAccountResponse)
def create_account(
    org_id: UUID,
    body: ChartOfAccountCreate,
    db: Session = Depends(get_db),
):
    from app.models.entities import AccountType

    coa = ChartOfAccount(
        organization_id=org_id,
        code=body.code,
        name=body.name,
        account_type=AccountType(body.account_type),
    )
    db.add(coa)
    db.commit()
    db.refresh(coa)
    return coa


@router.post("/organizations/{org_id}/journal-entries", response_model=JournalEntryResponse)
def create_journal_entry(
    org_id: UUID,
    body: JournalEntryCreate,
    db: Session = Depends(get_db),
    ctx: OrganizationContext = Depends(get_current_ctx),
):
    if ctx.organization_id != org_id:
        raise HTTPException(403, "Organization mismatch")
    engine = AccountingEngine(db)
    try:
        entry = engine.create_draft_entry(
            ctx,
            entry_date=body.entry_date,
            description=body.description,
            lines=[line.model_dump() for line in body.lines],
            idempotency_key=body.idempotency_key,
        )
        entry = engine.post_entry(ctx, entry.id)
        db.commit()
        db.refresh(entry)
        return entry
    except IdempotencyConflict as e:
        db.rollback()
        raise HTTPException(409, str(e)) from e
    except ValidationError as e:
        db.rollback()
        raise HTTPException(422, str(e)) from e


@router.post("/organizations/{org_id}/phone-mappings")
def create_phone_mapping(
    org_id: UUID,
    body: PhoneMappingCreate,
    db: Session = Depends(get_db),
):
    from datetime import UTC, datetime

    from app.models.entities import PhoneOrgMapping

    mapping = PhoneOrgMapping(
        organization_id=org_id,
        phone_e164=body.phone_e164,
        verified_at=datetime.now(UTC),
    )
    db.add(mapping)
    db.commit()
    return {"status": "ok", "phone": body.phone_e164}


@router.post("/auth/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email).first()
    if not user or not user.password_hash or not verify_password(body.password, user.password_hash):
        raise HTTPException(401, "Invalid credentials")
    membership = db.query(OrganizationMembership).filter(OrganizationMembership.user_id == user.id).first()
    if not membership:
        raise HTTPException(403, "No organization membership")
    token = create_access_token(str(user.id), membership.organization_id, membership.role.value)
    return TokenResponse(access_token=token)


@router.get("/organizations/{org_id}/reports/ledger.xlsx")
def export_ledger_excel(
    org_id: UUID,
    db: Session = Depends(get_db),
    ctx: OrganizationContext = Depends(get_current_ctx),
):
    if ctx.organization_id != org_id:
        raise HTTPException(403, "Organization mismatch")
    data = ReportingService(db).export_excel(ctx)
    return Response(
        content=data,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=ledger.xlsx"},
    )


@router.get("/organizations/{org_id}/reports/ledger.pdf")
def export_ledger_pdf(
    org_id: UUID,
    db: Session = Depends(get_db),
    ctx: OrganizationContext = Depends(get_current_ctx),
):
    if ctx.organization_id != org_id:
        raise HTTPException(403, "Organization mismatch")
    data = ReportingService(db).export_pdf(ctx)
    return Response(content=data, media_type="application/pdf")
