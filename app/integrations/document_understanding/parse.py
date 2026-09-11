import json
import re
from datetime import date, datetime
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


def _parse_invoice_date(value) -> date | None:
    if not value:
        return None
    if isinstance(value, date):
        return value
    text = str(value).strip()
    try:
        return date.fromisoformat(text)
    except ValueError:
        pass
    for fmt in ("%d %b %Y", "%d-%B-%Y", "%d/%m/%Y", "%d-%m-%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def _to_decimal(value, default: str = "0") -> Decimal:
    if value is None:
        return Decimal(default)
    if isinstance(value, (int, float, Decimal)):
        return Decimal(str(value))
    cleaned = re.sub(r"[^\d.\-]", "", str(value).replace(",", ""))
    if not cleaned or cleaned in {".", "-", "-."}:
        return Decimal(default)
    return Decimal(cleaned)


def reconcile_amounts(
    subtotal: Decimal,
    tax_total: Decimal,
    total: Decimal,
    line_items: list[ExtractionLineItem],
) -> tuple[Decimal, Decimal, Decimal]:
    """Align subtotal, tax, and total for balanced journal posting."""
    line_subtotal = sum((item.quantity * item.unit_price for item in line_items), Decimal("0"))
    line_gross = sum((item.line_total for item in line_items if item.line_total > 0), Decimal("0"))

    if line_subtotal > 0:
        subtotal = line_subtotal
    elif line_gross > tax_total > 0:
        subtotal = line_gross - tax_total

    balanced_total = subtotal + tax_total
    if line_gross > 0 and abs(line_gross - balanced_total) <= Decimal("1"):
        total = line_gross
    elif abs(total - balanced_total) > Decimal("0.01"):
        total = balanced_total

    if abs(total - balanced_total) > Decimal("0.01"):
        total = balanced_total

    return subtotal, tax_total, total


def reconcile_extraction(extraction: DocumentExtraction) -> DocumentExtraction:
    subtotal, tax_total, total = reconcile_amounts(
        extraction.subtotal,
        extraction.tax_total,
        extraction.total,
        extraction.line_items,
    )
    if (
        subtotal == extraction.subtotal
        and tax_total == extraction.tax_total
        and total == extraction.total
    ):
        return extraction

    raw = {**extraction.raw, "amounts_reconciled": True}
    return DocumentExtraction(
        vendor_name=extraction.vendor_name,
        vendor_gstin=extraction.vendor_gstin,
        invoice_number=extraction.invoice_number,
        invoice_date=extraction.invoice_date,
        invoice_type=extraction.invoice_type,
        subtotal=subtotal,
        tax_total=tax_total,
        total=total,
        line_items=extraction.line_items,
        confidence=extraction.confidence,
        raw=raw,
    )


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
    return DocumentExtraction(
        vendor_name=data.get("vendor_name"),
        vendor_gstin=data.get("vendor_gstin"),
        invoice_number=data.get("invoice_number"),
        invoice_date=_parse_invoice_date(data.get("invoice_date")),
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
