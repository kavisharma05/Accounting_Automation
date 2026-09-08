from decimal import Decimal

from app.integrations.document_understanding.parse import (
    extraction_from_dict,
    parse_json_from_llm_text,
)


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
