from datetime import date
from io import BytesIO

import pandas as pd
from sqlalchemy.orm import Session

from app.core.logging import OrganizationContext
from app.models.entities import Invoice, InvoiceStatus, InvoiceType, Party


class GstrService:
    """GSTR-1 / GSTR-3B worksheet preparation (not filing)."""

    def __init__(self, db: Session):
        self.db = db

    def gstr1_rows(
        self,
        ctx: OrganizationContext,
        *,
        period_start: date,
        period_end: date,
    ) -> list[dict]:
        rows = (
            self.db.query(Invoice, Party)
            .join(Party, Party.id == Invoice.party_id)
            .filter(
                Invoice.organization_id == ctx.organization_id,
                Invoice.invoice_type == InvoiceType.sales,
                Invoice.status == InvoiceStatus.posted,
                Invoice.invoice_date >= period_start,
                Invoice.invoice_date <= period_end,
            )
            .order_by(Invoice.invoice_date)
            .all()
        )
        data = []
        for inv, party in rows:
            snap = inv.tax_computation_snapshot or {}
            data.append(
                {
                    "invoice_number": inv.invoice_number,
                    "invoice_date": inv.invoice_date.isoformat(),
                    "party_name": party.name,
                    "party_gstin": party.gstin or "",
                    "taxable_value": float(inv.subtotal),
                    "cgst": snap.get("cgst", 0.0),
                    "sgst": snap.get("sgst", 0.0),
                    "igst": snap.get("igst", 0.0),
                    "total_tax": float(inv.tax_total),
                    "invoice_value": float(inv.total),
                }
            )
        return data

    def gstr3b_summary(
        self,
        ctx: OrganizationContext,
        *,
        period_start: date,
        period_end: date,
    ) -> dict:
        sales = (
            self.db.query(Invoice)
            .filter(
                Invoice.organization_id == ctx.organization_id,
                Invoice.invoice_type == InvoiceType.sales,
                Invoice.status == InvoiceStatus.posted,
                Invoice.invoice_date >= period_start,
                Invoice.invoice_date <= period_end,
            )
            .all()
        )
        purchases = (
            self.db.query(Invoice)
            .filter(
                Invoice.organization_id == ctx.organization_id,
                Invoice.invoice_type == InvoiceType.purchase,
                Invoice.status == InvoiceStatus.posted,
                Invoice.invoice_date >= period_start,
                Invoice.invoice_date <= period_end,
            )
            .all()
        )

        outward_taxable = sum(float(i.subtotal) for i in sales)
        output_tax = sum(float(i.tax_total) for i in sales)
        input_tax_credit = sum(float(i.tax_total) for i in purchases)

        return {
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
            "outward_taxable_supplies": outward_taxable,
            "output_tax": output_tax,
            "input_tax_credit": input_tax_credit,
            "net_tax_payable": round(output_tax - input_tax_credit, 2),
            "sales_invoice_count": len(sales),
            "purchase_invoice_count": len(purchases),
        }

    def export_gstr1_excel(
        self,
        ctx: OrganizationContext,
        *,
        period_start: date,
        period_end: date,
    ) -> bytes:
        rows = self.gstr1_rows(ctx, period_start=period_start, period_end=period_end)
        summary = self.gstr3b_summary(ctx, period_start=period_start, period_end=period_end)
        buf = BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as writer:
            pd.DataFrame(rows).to_excel(writer, index=False, sheet_name="GSTR-1 B2B")
            pd.DataFrame([summary]).to_excel(writer, index=False, sheet_name="GSTR-3B Summary")
        return buf.getvalue()
