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


def _vision_message_content(content: bytes, mime_type: str) -> list[dict]:
    if not mime_type.startswith("image/"):
        raise ValueError(
            f"NVIDIA DeepSeek extraction requires an image (jpeg/png/webp); got {mime_type}"
        )
    b64 = base64.standard_b64encode(content).decode()
    return [
        {
            "type": "image_url",
            "image_url": {"url": f"data:{mime_type};base64,{b64}"},
        },
        {"type": "text", "text": EXTRACTION_PROMPT},
    ]


async def extract_with_nvidia(content: bytes, mime_type: str) -> DocumentExtraction:
    if not settings.document_ai_api_key:
        raise RuntimeError("DOCUMENT_AI_API_KEY is not configured")

    base_url = settings.document_ai_base_url.rstrip("/")
    model = settings.document_ai_model or "deepseek-ai/deepseek-v4-pro-0813"

    async with httpx.AsyncClient(timeout=180) as client:
        resp = await client.post(
            f"{base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.document_ai_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": [
                    {
                        "role": "user",
                        "content": _vision_message_content(content, mime_type),
                    }
                ],
                "temperature": 0.2,
                "top_p": 0.95,
                "max_tokens": 4096,
                "seed": 42,
                "chat_template_kwargs": {"thinking": False},
            },
        )
        if resp.status_code >= 400:
            logger.error("NVIDIA API error %s: %s", resp.status_code, resp.text)
        resp.raise_for_status()

        payload = resp.json()
        text = payload["choices"][0]["message"]["content"]
        data = parse_json_from_llm_text(text)
        return extraction_from_dict(data)
