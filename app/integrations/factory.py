from app.core.config import settings
from app.integrations.document_understanding.claude_adapter import ClaudeDocumentProvider
from app.integrations.document_understanding.mock import MockDocumentProvider
from app.integrations.gsp.mock import MockGspProvider
from app.integrations.messaging.mock import MockMessagingProvider
from app.integrations.messaging.whatsapp import WhatsAppCloudAdapter
from app.integrations.protocols import (
    DocumentUnderstandingProvider,
    GspProvider,
    MessagingProvider,
    StorageProvider,
)
from app.integrations.storage.local import LocalStorageProvider


def get_messaging_provider() -> MessagingProvider:
    if settings.messaging_provider == "whatsapp":
        return WhatsAppCloudAdapter()
    return MockMessagingProvider()


def get_document_provider() -> DocumentUnderstandingProvider:
    if settings.document_provider == "claude" and settings.anthropic_api_key:
        return ClaudeDocumentProvider()
    return MockDocumentProvider()


def get_storage_provider() -> StorageProvider:
    return LocalStorageProvider()


def get_gsp_provider() -> GspProvider:
    return MockGspProvider()
