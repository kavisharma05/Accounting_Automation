from decimal import Decimal

from app.integrations.document_understanding.parse import (
    extraction_from_dict,
    parse_json_from_llm_text,
    reconcile_amounts,
)
from app.integrations.protocols import ExtractionLineItem


def test_parse_json_from_llm_text_strips_markdown_fence():
    raw = parse_json_from_llm_text(
        '```json\n{"vendor_name": "Acme", "total": 100, "line_items": []}\n```'
    )
    assert raw["vendor_name"] == "Acme"


def test_extraction_from_dict_parses_line_items():
    extraction = extraction_from_dict(
        {
            "vendor_name": "Acme",
            "invoice_date": "2026-01-15",
            "subtotal": "1000",
            "tax_total": "180",
            "total": "1180",
            "confidence": 0.9,
            "line_items": [
                {
                    "description": "Supplies",
                    "quantity": "2",
                    "unit_price": "500",
                    "tax_rate": "18",
                    "line_total": "1000",
                }
            ],
        }
    )
    assert extraction.vendor_name == "Acme"
    assert extraction.total == Decimal("1180")
    assert len(extraction.line_items) == 1
    assert extraction.line_items[0].description == "Supplies"


def test_parse_invoice_date_accepts_human_readable_format():
    extraction = extraction_from_dict(
        {
            "invoice_date": "08 Sep 2026",
            "subtotal": "1000",
            "tax_total": "180",
            "total": "1180",
            "line_items": [],
        }
    )
    assert extraction.invoice_date.isoformat() == "2026-09-08"


def test_reconcile_amounts_uses_line_items_when_header_totals_mismatch():
    line_items = [
        ExtractionLineItem(
            description="Laptop",
            quantity=Decimal("1"),
            unit_price=Decimal("42000"),
            tax_rate=Decimal("18"),
            line_total=Decimal("49560"),
        ),
        ExtractionLineItem(
            description="ADP unit",
            quantity=Decimal("1"),
            unit_price=Decimal("4500"),
            tax_rate=Decimal("18"),
            line_total=Decimal("5310"),
        ),
    ]
    subtotal, tax_total, total = reconcile_amounts(
        Decimal("54670"),
        Decimal("8370"),
        Decimal("63040"),
        line_items,
    )
    assert subtotal == Decimal("46500")
    assert tax_total == Decimal("8370")
    assert total == Decimal("54870")
