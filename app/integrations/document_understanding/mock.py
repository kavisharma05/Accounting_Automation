import hashlib
from datetime import date
from decimal import Decimal

from app.integrations.protocols import (
    DocumentExtraction,
    DocumentUnderstandingProvider,
    ExtractionLineItem,
)


class MockDocumentProvider(DocumentUnderstandingProvider):
    async def extract_document(
        self, content: bytes, mime_type: str, *, document_id=None
    ) -> DocumentExtraction:
        digest = hashlib.sha256(content).hexdigest()[:8]
        return DocumentExtraction(
            vendor_name="Mock Vendor Pvt Ltd",
            vendor_gstin="29AABCU9603R1ZM",
            invoice_number=f"INV-{digest}",
            invoice_date=date.today(),
            invoice_type="purchase",
            subtotal=Decimal("50000.00"),
            tax_total=Decimal("9000.00"),
            total=Decimal("59000.00"),
            line_items=[
                ExtractionLineItem(
                    description="Office supplies",
                    quantity=Decimal("1"),
                    unit_price=Decimal("50000.00"),
                    tax_rate=Decimal("18"),
                    line_total=Decimal("50000.00"),
                )
            ],
            confidence=0.92,
            raw={"mock": True, "digest": digest},
        )
