from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = "ok"


class OrganizationCreate(BaseModel):
    name: str
    gstin: str | None = None


class OrganizationResponse(BaseModel):
    id: UUID
    name: str
    gstin: str | None

    model_config = {"from_attributes": True}


class ChartOfAccountCreate(BaseModel):
    code: str
    name: str
    account_type: str


class ChartOfAccountResponse(BaseModel):
    id: UUID
    code: str
    name: str
    account_type: str

    model_config = {"from_attributes": True}


class JournalLineCreate(BaseModel):
    chart_of_account_id: UUID
    debit: Decimal = Field(default=Decimal("0"))
    credit: Decimal = Field(default=Decimal("0"))
    description: str | None = None


class JournalEntryCreate(BaseModel):
    entry_date: date
    description: str = ""
    lines: list[JournalLineCreate]
    idempotency_key: str | None = None


class JournalEntryResponse(BaseModel):
    id: UUID
    entry_number: str
    status: str

    model_config = {"from_attributes": True}


class PhoneMappingCreate(BaseModel):
    phone_e164: str


class PilotConfigResponse(BaseModel):
    organization_id: UUID
    default_expense_account_id: UUID | None
    default_payable_account_id: UUID | None
    default_input_tax_account_id: UUID | None
    default_receivable_account_id: UUID | None
    default_revenue_account_id: UUID | None
    default_output_tax_account_id: UUID | None

    model_config = {"from_attributes": True}


class PilotConfigUpdate(BaseModel):
    expense_account_id: UUID | None = None
    payable_account_id: UUID | None = None
    input_tax_account_id: UUID | None = None
    receivable_account_id: UUID | None = None
    revenue_account_id: UUID | None = None
    output_tax_account_id: UUID | None = None
    auto_from_coa: bool = False


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class MeResponse(BaseModel):
    user_id: UUID
    email: str
    organization_id: UUID
    organization_name: str
    role: str
