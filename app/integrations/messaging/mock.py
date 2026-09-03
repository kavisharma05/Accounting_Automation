from typing import Any
from uuid import uuid4

from app.integrations.protocols import InboundMessage, MessagingProvider, OutboundMessage


class MockMessagingProvider(MessagingProvider):
    sent_messages: list[OutboundMessage] = []

    async def parse_webhook(self, payload: dict[str, Any]) -> list[InboundMessage]:
        msgs = []
        for entry in payload.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                for m in value.get("messages", []):
                    media = m.get("image") or m.get("document") or {}
                    msgs.append(
                        InboundMessage(
                            external_id=m.get("id", str(uuid4())),
                            from_phone=m.get("from", ""),
                            text=m.get("text", {}).get("body"),
                            media_id=media.get("id"),
                            media_mime_type=media.get("mime_type"),
                            timestamp=m.get("timestamp", ""),
                        )
                    )
        return msgs

    async def download_media(self, media_id: str) -> tuple[bytes, str]:
        return b"mock-invoice-image", "image/jpeg"

    async def send_message(self, message: OutboundMessage) -> str:
        MockMessagingProvider.sent_messages.append(message)
        return str(uuid4())
