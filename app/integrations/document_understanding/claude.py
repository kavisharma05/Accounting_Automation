import base64
import logging

import httpx

from app.core.config import settings
from app.integrations.document_understanding.parse import (
    EXTRACTION_PROMPT,
    extraction_from_dict,
    parse_json_from_llm_text,
)
from app.integrations.protocols import DocumentExtraction

logger = logging.getLogger(__name__)


def _content_block(content: bytes, mime_type: str) -> dict:
    b64 = base64.standard_b64encode(content).decode()
    if mime_type == "application/pdf":
        return {
            "type": "document",
            "source": {
                "type": "base64",
                "media_type": "application/pdf",
                "data": b64,
            },
        }
    if mime_type.startswith("image/"):
        return {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": mime_type,
                "data": b64,
            },
        }
    raise ValueError(f"Unsupported document mime type for Claude: {mime_type}")


async def extract_with_claude(content: bytes, mime_type: str) -> DocumentExtraction:
    if not settings.anthropic_api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is not configured")

    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": settings.anthropic_api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": settings.anthropic_model,
                "max_tokens": 4096,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            _content_block(content, mime_type),
                            {"type": "text", "text": EXTRACTION_PROMPT},
                        ],
                    }
                ],
            },
        )
        if resp.status_code >= 400:
            logger.error("Claude API error %s: %s", resp.status_code, resp.text)
        resp.raise_for_status()

        payload = resp.json()
        text = payload["content"][0]["text"]
        data = parse_json_from_llm_text(text)
        return extraction_from_dict(data)
