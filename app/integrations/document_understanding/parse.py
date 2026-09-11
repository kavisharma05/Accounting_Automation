import json
import re
from datetime import date
from decimal import Decimal

from app.integrations.protocols import DocumentExtraction, ExtractionLineItem

EXTRACTION_PROMPT = """Extract invoice fields from this document for Indian GST bookkeeping.
Respond with ONLY a single JSON object. No markdown, no code fences, no explanation.
Schema:
{
  "vendor_name": string | null,
  "vendor_gstin": string | null,
  "invoice_number": string | null,
  "invoice_date": "YYYY-MM-DD" | null,
  "invoice_type": "purchase" | "sales",
  "subtotal": number,
  "tax_total": number,
  "total": number,
  "line_items": [
    {
      "description": string,
      "quantity": number,
      "unit_price": number,
      "tax_rate": number,
      "line_total": number
    }
  ],
  "confidence": number between 0 and 1
}
Use purchase for vendor bills and sales for outgoing invoices. Amounts in INR."""


def parse_json_from_llm_text(text: str) -> dict:
    """Parse JSON from an LLM response, tolerating markdown code fences."""
    cleaned = text.strip()
    fence_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", cleaned, re.DOTALL | re.IGNORECASE)
    if fence_match:
        cleaned = fence_match.group(1).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        obj_match = re.search(r"\{[\s\S]*\}", cleaned)
        if obj_match:
            return json.loads(obj_match.group(0))
        raise


JSON_RETRY_PROMPT = """Convert this invoice extraction into ONLY valid JSON using this schema:
{
  "vendor_name": string | null,
  "vendor_gstin": string | null,
  "invoice_number": string | null,
  "invoice_date": "YYYY-MM-DD" | null,
  "invoice_type": "purchase" | "sales",
  "subtotal": number,
  "tax_total": number,
  "total": number,
  "line_items": [{"description": string, "quantity": number, "unit_price": number, "tax_rate": number, "line_total": number}],
  "confidence": number between 0 and 1
}
Return JSON only — no markdown or explanation.

Extraction:
"""


def _to_decimal(value, default: str = "0") -> Decimal:
    if value is None:
        return Decimal(default)
    if isinstance(value, (int, float, Decimal)):
        return Decimal(str(value))
    cleaned = re.sub(r"[^\d.\-]", "", str(value).replace(",", ""))
    if not cleaned or cleaned in {".", "-", "-."}:
        return Decimal(default)
    return Decimal(cleaned)


def extraction_from_dict(data: dict) -> DocumentExtraction:
    items = [
        ExtractionLineItem(
            description=str(i.get("description", "")),
            quantity=_to_decimal(i.get("quantity", 1), "1"),
            unit_price=_to_decimal(i.get("unit_price", 0)),
            tax_rate=_to_decimal(i.get("tax_rate", 0)),
            line_total=_to_decimal(i.get("line_total", 0)),
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
        subtotal=_to_decimal(data.get("subtotal", 0)),
        tax_total=_to_decimal(data.get("tax_total", 0)),
        total=_to_decimal(data.get("total", 0)),
        line_items=items,
        confidence=float(data.get("confidence", 0.5)),
        raw=data,
    )


def extraction_to_record_dict(extraction: DocumentExtraction) -> dict:
    return {
        "vendor_name": extraction.vendor_name,
        "vendor_gstin": extraction.vendor_gstin,
        "invoice_number": extraction.invoice_number,
        "invoice_date": extraction.invoice_date.isoformat() if extraction.invoice_date else None,
        "invoice_type": extraction.invoice_type,
        "subtotal": str(extraction.subtotal),
        "tax_total": str(extraction.tax_total),
        "total": str(extraction.total),
        "confidence": extraction.confidence,
        "line_items": [
            {
                "description": item.description,
                "quantity": str(item.quantity),
                "unit_price": str(item.unit_price),
                "tax_rate": str(item.tax_rate),
                "line_total": str(item.line_total),
            }
            for item in extraction.line_items
        ],
    }
