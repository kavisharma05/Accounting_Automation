from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class PaymentApplicationItem(BaseModel):
    invoice_id: UUID
    amount_applied: Decimal


class PaymentCreate(BaseModel):
    party_id: UUID
    amount: Decimal
    payment_date: date
    payable_account_id: UUID
    bank_account_id: UUID
    reference: str | None = None
    idempotency_key: str | None = None
    applications: list[PaymentApplicationItem] = Field(default_factory=list)


class PaymentResponse(BaseModel):
    id: UUID
    amount: Decimal
    payment_date: date
    reference: str | None
    journal_entry_id: UUID | None

    model_config = {"from_attributes": True}


class BankAccountCreate(BaseModel):
    name: str
    chart_of_account_id: UUID
    account_number: str | None = None
    ifsc: str | None = None


class BankAccountResponse(BaseModel):
    id: UUID
    name: str
    account_number: str | None
    chart_of_account_id: UUID

    model_config = {"from_attributes": True}


class PartyResponse(BaseModel):
    id: UUID
    name: str
    party_type: str
    gstin: str | None

    model_config = {"from_attributes": True}


class AccountListItem(BaseModel):
    id: UUID
    code: str
    name: str
    account_type: str

    model_config = {"from_attributes": True}


class PeriodLockUpdate(BaseModel):
    locked_through_date: date


class CAEmailRequest(BaseModel):
    ca_email: str | None = None
