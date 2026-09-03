"""Default GST + TDS tax rules for Indian SMB."""

from datetime import date
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.entities import TaxRuleVersion

DEFAULT_RULES = {
    "default_gst_rate": 18,
    "tds_sections": {
        "194C": {"rate": 1.0, "threshold": 30000, "description": "Contractors"},
        "194J": {"rate": 10.0, "threshold": 30000, "description": "Professional fees"},
        "194H": {"rate": 5.0, "threshold": 15000, "description": "Commission"},
        "194I": {"rate": 10.0, "threshold": 240000, "description": "Rent"},
    },
}


def seed_default_tax_rules(
    db: Session,
    organization_id: UUID | None = None,
    *,
    effective_from: date | None = None,
) -> TaxRuleVersion:
    rule = TaxRuleVersion(
        organization_id=organization_id,
        effective_from=effective_from or date(2020, 4, 1),
        rules=DEFAULT_RULES,
    )
    db.add(rule)
    db.flush()
    return rule
