# Integration Contracts

**Stage:** 5 of 18

Provider interfaces live in [app/integrations/protocols.py](app/integrations/protocols.py). Adapters implement these contracts; domain code depends only on the ABCs.

## MessagingProvider

```python
async def parse_webhook(payload: dict) -> list[InboundMessage]
async def download_media(media_id: str) -> tuple[bytes, str]
async def send_message(message: OutboundMessage) -> str  # returns external message id
```

| Adapter | Path | Phase |
|---------|------|-------|
| MockMessagingProvider | `integrations/messaging/mock.py` | Dev/test |
| WhatsAppCloudAdapter | `integrations/messaging/whatsapp.py` | Production |

## DocumentUnderstandingProvider

```python
async def extract_document(content: bytes, mime_type: str, *, document_id: UUID | None) -> DocumentExtraction
```

| Adapter | Path |
|---------|------|
| MockDocumentProvider | `integrations/document_understanding/mock.py` |
| ClaudeDocumentProvider | `integrations/document_understanding/claude_adapter.py` |

## StorageProvider

```python
async def put(key: str, content: bytes, mime_type: str) -> str
async def get(key: str) -> tuple[bytes, str]
async def delete(key: str) -> None
```

## GspProvider

```python
async def generate_eway_bill(request: EWayBillRequest) -> EWayBillResponse
```

## EInvoiceProvider

Defined, unimplemented Phase 1 per PRD.

## Factory

[app/integrations/factory.py](app/integrations/factory.py) selects adapters from environment settings.
