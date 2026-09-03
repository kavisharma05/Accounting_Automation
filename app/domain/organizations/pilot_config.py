from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, ValidationError
from app.models.entities import ChartOfAccount, Organization


def get_org_account_defaults(db: Session, organization_id: UUID) -> tuple[UUID, UUID, UUID | None]:
    org = db.get(Organization, organization_id)
    if not org:
        raise NotFoundError("Organization not found")
    if not org.default_expense_account_id or not org.default_payable_account_id:
        raise ValidationError(
            "Organization pilot accounts not configured. "
            "Set default expense and payable accounts via PATCH /pilot-config."
        )
    return (
        org.default_expense_account_id,
        org.default_payable_account_id,
        org.default_input_tax_account_id,
    )


def get_sales_account_defaults(
    db: Session, organization_id: UUID
) -> tuple[UUID, UUID, UUID | None]:
    org = db.get(Organization, organization_id)
    if not org:
        raise NotFoundError("Organization not found")
    if not org.default_receivable_account_id or not org.default_revenue_account_id:
        raise ValidationError(
            "Organization sales accounts not configured. "
            "Set default receivable and revenue accounts via PATCH /pilot-config."
        )
    return (
        org.default_receivable_account_id,
        org.default_revenue_account_id,
        org.default_output_tax_account_id,
    )


def configure_pilot_accounts(
    db: Session,
    organization_id: UUID,
    *,
    expense_account_id: UUID | None = None,
    payable_account_id: UUID | None = None,
    input_tax_account_id: UUID | None = None,
    receivable_account_id: UUID | None = None,
    revenue_account_id: UUID | None = None,
    output_tax_account_id: UUID | None = None,
    auto_from_coa: bool = False,
) -> Organization:
    org = db.get(Organization, organization_id)
    if not org:
        raise NotFoundError("Organization not found")

    if auto_from_coa:
        expense = _coa_by_code(db, organization_id, "5000")
        payable = _coa_by_code(db, organization_id, "2000")
        input_tax = _coa_by_code(db, organization_id, "1400")
        receivable = _coa_by_code(db, organization_id, "1100")
        revenue = _coa_by_code(db, organization_id, "4000")
        output_tax = _coa_by_code(db, organization_id, "2100")
        org.default_expense_account_id = expense.id
        org.default_payable_account_id = payable.id
        org.default_input_tax_account_id = input_tax.id
        org.default_receivable_account_id = receivable.id
        org.default_revenue_account_id = revenue.id
        org.default_output_tax_account_id = output_tax.id
    else:
        if expense_account_id:
            _validate_coa(db, organization_id, expense_account_id)
            org.default_expense_account_id = expense_account_id
        if payable_account_id:
            _validate_coa(db, organization_id, payable_account_id)
            org.default_payable_account_id = payable_account_id
        if input_tax_account_id:
            _validate_coa(db, organization_id, input_tax_account_id)
            org.default_input_tax_account_id = input_tax_account_id
        if receivable_account_id:
            _validate_coa(db, organization_id, receivable_account_id)
            org.default_receivable_account_id = receivable_account_id
        if revenue_account_id:
            _validate_coa(db, organization_id, revenue_account_id)
            org.default_revenue_account_id = revenue_account_id
        if output_tax_account_id:
            _validate_coa(db, organization_id, output_tax_account_id)
            org.default_output_tax_account_id = output_tax_account_id

    db.flush()
    return org


def _coa_by_code(db: Session, organization_id: UUID, code: str) -> ChartOfAccount:
    coa = (
        db.query(ChartOfAccount)
        .filter(
            ChartOfAccount.organization_id == organization_id,
            ChartOfAccount.code == code,
        )
        .first()
    )
    if not coa:
        raise ValidationError(f"Chart of account {code} not found for organization")
    return coa


def _validate_coa(db: Session, organization_id: UUID, coa_id: UUID) -> None:
    coa = db.get(ChartOfAccount, coa_id)
    if not coa or coa.organization_id != organization_id:
        raise ValidationError("Invalid chart of account for organization")
