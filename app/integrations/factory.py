import logging

from app.core.config import settings
from app.integrations.document_understanding.claude_adapter import ClaudeDocumentProvider
from app.integrations.document_understanding.mock import MockDocumentProvider
from app.integrations.document_understanding.nvidia_adapter import NvidiaDocumentProvider
from app.integrations.gsp.mock import MockGspProvider
from app.integrations.messaging.mock import MockMessagingProvider
from app.integrations.messaging.whatsapp import WhatsAppCloudAdapter
from app.integrations.protocols import (
    DocumentUnderstandingProvider,
    EInvoiceProvider,
    GspProvider,
    MessagingProvider,
    StorageProvider,
)
from app.integrations.storage.local import LocalStorageProvider

logger = logging.getLogger(__name__)


def get_messaging_provider() -> MessagingProvider:
    if settings.messaging_provider == "whatsapp":
        return WhatsAppCloudAdapter()
    return MockMessagingProvider()


def get_document_provider() -> DocumentUnderstandingProvider:
    if settings.document_provider == "claude":
        if not settings.anthropic_api_key:
            logger.error(
                "DOCUMENT_PROVIDER=claude but ANTHROPIC_API_KEY is missing; "
                "falling back to mock extraction"
            )
            return MockDocumentProvider()
        return ClaudeDocumentProvider()
    if settings.document_provider == "nvidia":
        if not settings.document_ai_api_key:
            logger.error(
                "DOCUMENT_PROVIDER=nvidia but DOCUMENT_AI_API_KEY is missing; "
                "falling back to mock extraction"
            )
            return MockDocumentProvider()
        return NvidiaDocumentProvider()
    return MockDocumentProvider()


def get_storage_provider() -> StorageProvider:
    if settings.storage_provider == "s3":
        try:
            from app.integrations.storage.s3 import S3StorageProvider

            return S3StorageProvider()
        except Exception:
            logger.exception("S3 storage init failed; falling back to local storage")
            return LocalStorageProvider()
    return LocalStorageProvider()


def get_gsp_provider() -> GspProvider:
    return MockGspProvider()


def get_einvoice_provider() -> EInvoiceProvider:
    from app.integrations.gsp.mock import MockEInvoiceProvider

    return MockEInvoiceProvider()


def get_email_provider():
    from app.integrations.email.mock import MockEmailProvider

    return MockEmailProvider()
