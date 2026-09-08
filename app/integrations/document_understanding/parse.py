import json
import re
from datetime import date
from decimal import Decimal

from app.integrations.protocols import DocumentExtraction, ExtractionLineItem

EXTRACTION_PROMPT = """Extract invoice fields from this document for Indian GST bookkeeping.
Return ONLY valid JSON (no markdown) with this schema:
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
    fence_match = re.match(r"^```(?:json)?\s*\n?(.*?)\n?```\s*$", cleaned, re.DOTALL | re.IGNORECASE)
    if fence_match:
        cleaned = fence_match.group(1).strip()
    return json.loads(cleaned)


def extraction_from_dict(data: dict) -> DocumentExtraction:
    items = [
        ExtractionLineItem(
            description=str(i.get("description", "")),
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
