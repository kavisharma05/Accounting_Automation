from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class SalesInvoiceCreate(BaseModel):
    party_id: UUID
    invoice_number: str
    invoice_date: date
    subtotal: Decimal
    tax_total: Decimal = Decimal("0")
    total: Decimal | None = None
    line_description: str = "Sales item"


class InvoiceResponse(BaseModel):
    id: UUID
    invoice_number: str
    invoice_type: str
    status: str
    total: Decimal
    journal_entry_id: UUID | None = None

    model_config = {"from_attributes": True}


class CreditNoteCreate(BaseModel):
    original_invoice_id: UUID
    note_number: str
    note_date: date
    subtotal: Decimal
    tax_total: Decimal = Decimal("0")
    reason: str | None = None


class DebitNoteCreate(BaseModel):
    original_invoice_id: UUID
    note_number: str
    note_date: date
    subtotal: Decimal
    tax_total: Decimal = Decimal("0")
    reason: str | None = None


class NoteResponse(BaseModel):
    id: UUID
    note_number: str
    status: str
    total: Decimal
    journal_entry_id: UUID | None = None

    model_config = {"from_attributes": True}


class GstrPeriodQuery(BaseModel):
    period_start: date
    period_end: date


class EInvoiceResponse(BaseModel):
    id: UUID
    invoice_id: UUID
    irn: str | None
    ack_no: str | None
    status: str

    model_config = {"from_attributes": True}


class SearchQuery(BaseModel):
    q: str = Field(min_length=1)
    invoice_type: str | None = None
    limit: int = Field(default=50, le=200)
