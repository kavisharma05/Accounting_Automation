import hashlib
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.core.logging import OrganizationContext
from app.core.config import settings
from app.integrations.factory import get_document_provider, get_storage_provider
from app.integrations.document_understanding.parse import extraction_to_record_dict
from app.models.entities import AIExtractionRecord, Document


def _extraction_model_name(is_mock: bool) -> str:
    if is_mock:
        return "mock-v1"
    if settings.document_provider == "claude":
        return settings.anthropic_model
    if settings.document_provider == "nvidia":
        return settings.document_ai_model
    return settings.document_provider


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
        is_mock = extraction.raw.get("mock") is True
        record = AIExtractionRecord(
            document_id=doc.id,
            provider="mock" if is_mock else settings.document_provider,
            model=_extraction_model_name(is_mock),
            extracted_data=extraction_to_record_dict(extraction),
            confidence=extraction.confidence,
            raw_response_ref=None,
        )
        self.db.add(record)
        self.db.flush()
        return record
