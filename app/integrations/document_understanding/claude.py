import base64
import json
from datetime import date
from decimal import Decimal

import httpx

from app.core.config import settings
from app.integrations.protocols import DocumentExtraction, ExtractionLineItem


async def extract_with_claude(content: bytes, mime_type: str) -> DocumentExtraction:
    b64 = base64.standard_b64encode(content).decode()
    prompt = (
        "Extract invoice fields as JSON: vendor_name, vendor_gstin, invoice_number, "
        "invoice_date (YYYY-MM-DD), invoice_type (purchase|sales), subtotal, tax_total, "
        "total, line_items[{description, quantity, unit_price, tax_rate, line_total}], confidence."
    )
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": settings.anthropic_api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": "claude-sonnet-4-20250514",
                "max_tokens": 4096,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": mime_type,
                                    "data": b64,
                                },
                            },
                            {"type": "text", "text": prompt},
                        ],
                    }
                ],
            },
        )
        resp.raise_for_status()
        text = resp.json()["content"][0]["text"]
        data = json.loads(text)
        items = [
            ExtractionLineItem(
                description=i.get("description", ""),
                quantity=Decimal(str(i.get("quantity", 1))),
                unit_price=Decimal(str(i.get("unit_price", 0))),
                tax_rate=Decimal(str(i.get("tax_rate", 0))),
                line_total=Decimal(str(i.get("line_total", 0))),
            )
            for i in data.get("line_items", [])
        ]
        inv_date = data.get("invoice_date")
        return DocumentExtraction(
            vendor_name=data.get("vendor_name"),
            vendor_gstin=data.get("vendor_gstin"),
            invoice_number=data.get("invoice_number"),
            invoice_date=date.fromisoformat(inv_date) if inv_date else None,
            invoice_type=data.get("invoice_type", "purchase"),
            subtotal=Decimal(str(data.get("subtotal", 0))),
            tax_total=Decimal(str(data.get("tax_total", 0))),
            total=Decimal(str(data.get("total", 0))),
            line_items=items,
            confidence=float(data.get("confidence", 0.5)),
            raw=data,
        )
