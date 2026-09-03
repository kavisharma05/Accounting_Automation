from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class TdsComputeRequest(BaseModel):
    taxable_amount: Decimal
    section: str = Field(description="TDS section e.g. 194C, 194J")
    as_of: date | None = None


class TdsApplyRequest(BaseModel):
    section: str
    payable_account_id: UUID | None = None
    tds_payable_account_id: UUID | None = None


class ComplianceStatusUpdate(BaseModel):
    status: str = "completed"
