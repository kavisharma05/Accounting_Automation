
import httpx

from app.core.config import settings
from app.integrations.protocols import (
    InboundMessage,
    MessagingProvider,
    OutboundMessage,
)


class WhatsAppCloudAdapter(MessagingProvider):
    BASE = "https://graph.facebook.com/v21.0"

    async def parse_webhook(self, payload: dict) -> list[InboundMessage]:
        from app.integrations.messaging.mock import MockMessagingProvider

        return await MockMessagingProvider().parse_webhook(payload)

    async def download_media(self, media_id: str) -> tuple[bytes, str]:
        async with httpx.AsyncClient() as client:
            meta = await client.get(
                f"{self.BASE}/{media_id}",
                headers={"Authorization": f"Bearer {settings.whatsapp_access_token}"},
            )
            meta.raise_for_status()
            url = meta.json()["url"]
            mime = meta.json().get("mime_type", "application/octet-stream")
            data = await client.get(
                url,
                headers={"Authorization": f"Bearer {settings.whatsapp_access_token}"},
            )
            data.raise_for_status()
            return data.content, mime

    async def send_message(self, message: OutboundMessage) -> str:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.BASE}/{settings.whatsapp_phone_number_id}/messages",
                headers={"Authorization": f"Bearer {settings.whatsapp_access_token}"},
                json={
                    "messaging_product": "whatsapp",
                    "to": message.to_phone,
                    "type": "text",
                    "text": {"body": message.text},
                },
            )
            resp.raise_for_status()
            return resp.json()["messages"][0]["id"]
