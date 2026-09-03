import hashlib
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.core.logging import OrganizationContext
from app.integrations.factory import get_document_provider, get_storage_provider
from app.models.entities import AIExtractionRecord, Document


class DocumentService:
    def __init__(self, db: Session):
        self.db = db
        self.storage = get_storage_provider()
        self.document_ai = get_document_provider()

    async def upload(
        self,
        ctx: OrganizationContext,
        content: bytes,
        mime_type: str,
        *,
        uploaded_by_id: UUID | None = None,
    ) -> Document:
        sha = hashlib.sha256(content).hexdigest()
        key = f"{ctx.organization_id}/{sha}/{uuid4()}"
        await self.storage.put(key, content, mime_type)
        doc = Document(
            organization_id=ctx.organization_id,
            storage_key=key,
            mime_type=mime_type,
            sha256=sha,
            uploaded_by_id=uploaded_by_id or ctx.user_id,
        )
        self.db.add(doc)
        self.db.flush()
        return doc

    async def extract(self, ctx: OrganizationContext, document_id: UUID) -> AIExtractionRecord:
        doc = (
            self.db.query(Document)
            .filter(
                Document.id == document_id,
                Document.organization_id == ctx.organization_id,
            )
            .first()
        )
        if not doc:
            raise ValueError("Document not found")
        content, mime = await self.storage.get(doc.storage_key)
        extraction = await self.document_ai.extract_document(content, mime, document_id=doc.id)
        record = AIExtractionRecord(
            document_id=doc.id,
            provider="mock" if extraction.raw.get("mock") else "claude",
            model="mock-v1" if extraction.raw.get("mock") else "claude-sonnet",
            extracted_data={
                "vendor_name": extraction.vendor_name,
                "vendor_gstin": extraction.vendor_gstin,
                "invoice_number": extraction.invoice_number,
                "invoice_date": extraction.invoice_date.isoformat() if extraction.invoice_date else None,
                "invoice_type": extraction.invoice_type,
                "subtotal": str(extraction.subtotal),
                "tax_total": str(extraction.tax_total),
                "total": str(extraction.total),
                "confidence": extraction.confidence,
            },
            confidence=extraction.confidence,
            raw_response_ref=None,
        )
        self.db.add(record)
        self.db.flush()
        return record
