from io import BytesIO

import pandas as pd
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from sqlalchemy.orm import Session

from app.core.logging import OrganizationContext
from app.models.entities import JournalEntry, JournalEntryLine, JournalEntryStatus


class ReportingService:
    def __init__(self, db: Session):
        self.db = db

    def ledger_dataframe(self, ctx: OrganizationContext) -> pd.DataFrame:
        rows = (
            self.db.query(JournalEntry, JournalEntryLine)
            .join(JournalEntryLine, JournalEntryLine.journal_entry_id == JournalEntry.id)
            .filter(
                JournalEntry.organization_id == ctx.organization_id,
                JournalEntry.status == JournalEntryStatus.posted,
            )
            .all()
        )
        data = []
        for entry, line in rows:
            data.append(
                {
                    "entry_number": entry.entry_number,
                    "entry_date": entry.entry_date.isoformat(),
                    "description": entry.description,
                    "debit": float(line.debit or 0),
                    "credit": float(line.credit or 0),
                    "line_description": line.description,
                }
            )
        return pd.DataFrame(data)

    def export_excel(self, ctx: OrganizationContext) -> bytes:
        df = self.ledger_dataframe(ctx)
        buf = BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Ledger")
        return buf.getvalue()

    def export_pdf(self, ctx: OrganizationContext) -> bytes:
        df = self.ledger_dataframe(ctx)
        buf = BytesIO()
        c = canvas.Canvas(buf, pagesize=A4)
        c.drawString(50, 800, "General Ledger")
        y = 780
        for _, row in df.head(40).iterrows():
            line = f"{row['entry_date']} {row['entry_number']} D:{row['debit']} C:{row['credit']}"
            c.drawString(50, y, line[:90])
            y -= 14
            if y < 50:
                c.showPage()
                y = 800
        c.save()
        return buf.getvalue()
