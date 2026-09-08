from app.integrations.protocols import DocumentUnderstandingProvider


class NvidiaDocumentProvider(DocumentUnderstandingProvider):
    async def extract_document(self, content: bytes, mime_type: str, *, document_id=None):
        from app.integrations.document_understanding.nvidia import extract_with_nvidia

        return await extract_with_nvidia(content, mime_type)
