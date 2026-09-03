from app.integrations.protocols import DocumentUnderstandingProvider


class ClaudeDocumentProvider(DocumentUnderstandingProvider):
    async def extract_document(self, content: bytes, mime_type: str, *, document_id=None):
        from app.integrations.document_understanding.claude import extract_with_claude

        return await extract_with_claude(content, mime_type)
