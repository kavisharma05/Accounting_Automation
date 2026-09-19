import base64
import logging

import httpx

from app.core.config import settings
from app.integrations.document_understanding.parse import (
    EXTRACTION_PROMPT,
    JSON_RETRY_PROMPT,
    extraction_from_dict,
    parse_json_from_llm_text,
)
from app.integrations.document_understanding.render import prepare_vision_input
from app.integrations.protocols import DocumentExtraction

logger = logging.getLogger(__name__)


def _vision_message_content(content: bytes, mime_type: str) -> list[dict]:
    content, mime_type = prepare_vision_input(content, mime_type)
    b64 = base64.standard_b64encode(content).decode()
    return [
        {"type": "text", "text": EXTRACTION_PROMPT},
        {
            "type": "image_url",
            "image_url": {"url": f"data:{mime_type};base64,{b64}"},
        },
    ]


def _request_body(model: str, content: bytes, mime_type: str) -> dict:
    body: dict = {
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
    }
    if model.startswith("deepseek-"):
        body["seed"] = 42
        body["chat_template_kwargs"] = {"thinking": False}
    return body


def _completion_text(payload: dict) -> str:
    choices = payload.get("choices") or []
    if not choices:
        raise RuntimeError(
            f"NVIDIA API returned no choices (model may not support vision): {payload}"
        )
    message = choices[0].get("message") or {}
    text = message.get("content")
    if not text:
        raise RuntimeError(f"NVIDIA API returned empty content: {payload}")
    return text


async def _chat_completion(client: httpx.AsyncClient, base_url: str, body: dict) -> str:
    resp = await client.post(
        f"{base_url}/chat/completions",
        headers={
            "Authorization": f"Bearer {settings.document_ai_api_key}",
            "Content-Type": "application/json",
        },
        json=body,
    )
    if resp.status_code >= 400:
        logger.error("NVIDIA API error %s: %s", resp.status_code, resp.text)
    resp.raise_for_status()
    return _completion_text(resp.json())


async def extract_with_nvidia(content: bytes, mime_type: str) -> DocumentExtraction:
    if not settings.document_ai_api_key:
        raise RuntimeError("DOCUMENT_AI_API_KEY is not configured")

    base_url = settings.document_ai_base_url.rstrip("/")
    model = settings.document_ai_model or "meta/llama-3.2-11b-vision-instruct"

    async with httpx.AsyncClient(timeout=180) as client:
        text = await _chat_completion(
            client, base_url, _request_body(model, content, mime_type)
        )
        try:
            data = parse_json_from_llm_text(text)
        except ValueError:
            logger.warning("NVIDIA vision model returned non-JSON; retrying as text-only JSON conversion")
            text = await _chat_completion(
                client,
                base_url,
                {
                    "model": model,
                    "messages": [
                        {"role": "user", "content": JSON_RETRY_PROMPT + text},
                    ],
                    "temperature": 0.0,
                    "max_tokens": 2048,
                },
            )
            data = parse_json_from_llm_text(text)
        return extraction_from_dict(data)
