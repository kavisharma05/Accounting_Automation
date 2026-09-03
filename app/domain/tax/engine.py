from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.entities import TaxRuleVersion


class TaxEngine:
    def __init__(self, db: Session):
        self.db = db

    def get_applicable_rule(
        self, organization_id: UUID, as_of: date
    ) -> TaxRuleVersion | None:
        return (
            self.db.query(TaxRuleVersion)
            .filter(
                (TaxRuleVersion.organization_id == organization_id)
                | (TaxRuleVersion.organization_id.is_(None))
            )
            .filter(TaxRuleVersion.effective_from <= as_of)
            .order_by(TaxRuleVersion.effective_from.desc())
            .first()
        )

    def compute_gst(
        self,
        *,
        organization_id: UUID,
        as_of: date,
        taxable_amount: Decimal,
        is_interstate: bool,
    ) -> dict:
        rule = self.get_applicable_rule(organization_id, as_of)
        if not rule:
            rate = Decimal("18")
        else:
            rate = Decimal(str(rule.rules.get("default_gst_rate", 18)))

        tax = (taxable_amount * rate / Decimal("100")).quantize(Decimal("0.01"))
        if is_interstate:
            return {
                "tax_rule_version_id": str(rule.id) if rule else None,
                "rate": float(rate),
                "igst": float(tax),
                "cgst": 0.0,
                "sgst": 0.0,
                "tax_total": float(tax),
            }
        half = (tax / 2).quantize(Decimal("0.01"))
        return {
            "tax_rule_version_id": str(rule.id) if rule else None,
            "rate": float(rate),
            "igst": 0.0,
            "cgst": float(half),
            "sgst": float(tax - half),
            "tax_total": float(tax),
        }
