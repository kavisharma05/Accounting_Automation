from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any
from uuid import UUID


@dataclass
class InboundMessage:
    external_id: str
    from_phone: str
    text: str | None
    media_id: str | None
    media_mime_type: str | None
    timestamp: str


@dataclass
class OutboundMessage:
    to_phone: str
    text: str


class MessagingProvider(ABC):
    @abstractmethod
    async def parse_webhook(self, payload: dict[str, Any]) -> list[InboundMessage]:
        ...

    @abstractmethod
    async def download_media(self, media_id: str) -> tuple[bytes, str]:
        ...

    @abstractmethod
    async def send_message(self, message: OutboundMessage) -> str:
        ...


@dataclass
class ExtractionLineItem:
    description: str
    quantity: Decimal
    unit_price: Decimal
    tax_rate: Decimal
    line_total: Decimal


@dataclass
class DocumentExtraction:
    vendor_name: str | None
    vendor_gstin: str | None
    invoice_number: str | None
    invoice_date: date | None
    invoice_type: str  # purchase | sales
    subtotal: Decimal
    tax_total: Decimal
    total: Decimal
    line_items: list[ExtractionLineItem]
    confidence: float
    raw: dict[str, Any]


class DocumentUnderstandingProvider(ABC):
    @abstractmethod
    async def extract_document(
        self, content: bytes, mime_type: str, *, document_id: UUID | None = None
    ) -> DocumentExtraction:
        ...


class OcrFallbackProvider(ABC):
    @abstractmethod
    async def extract_text(self, content: bytes, mime_type: str) -> str:
        ...


class EmailProvider(ABC):
    @abstractmethod
    async def send_email(self, to: str, subject: str, body: str, *, attachment: bytes | None = None) -> str:
        ...


class StorageProvider(ABC):
    @abstractmethod
    async def put(self, key: str, content: bytes, mime_type: str) -> str:
        ...

    @abstractmethod
    async def get(self, key: str) -> tuple[bytes, str]:
        ...

    @abstractmethod
    async def delete(self, key: str) -> None:
        ...


@dataclass
class EWayBillRequest:
    invoice_id: UUID
    organization_gstin: str
    consignee_gstin: str | None
    invoice_value: Decimal
    hsn_codes: list[str]


@dataclass
class EWayBillResponse:
    external_id: str
    status: str
    raw: dict[str, Any]


class GspProvider(ABC):
    @abstractmethod
    async def generate_eway_bill(self, request: EWayBillRequest) -> EWayBillResponse:
        ...


class EInvoiceProvider(ABC):
    @abstractmethod
    async def generate_einvoice(self, invoice_id: UUID, payload: dict[str, Any]) -> dict[str, Any]:
        ...
