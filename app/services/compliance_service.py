from calendar import monthrange
from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.core.logging import OrganizationContext
from app.models.entities import ComplianceCalendarEntry, ComplianceEntryStatus


class ComplianceCalendarService:
    """Generate and track GST/TDS compliance due dates (reminders only — not filing)."""

    def __init__(self, db: Session):
        self.db = db

    def generate_upcoming(
        self,
        ctx: OrganizationContext,
        *,
        months_ahead: int = 3,
    ) -> list[ComplianceCalendarEntry]:
        today = date.today()
        created: list[ComplianceCalendarEntry] = []
        for month_offset in range(months_ahead + 1):
            year = today.year + (today.month + month_offset - 1) // 12
            month = (today.month + month_offset - 1) % 12 + 1
            period = f"{year}-{month:02d}"

            templates = [
                ("gstr1", f"GSTR-1 preparation — {period}", 11),
                ("gstr3b", f"GSTR-3B preparation — {period}", 20),
                ("tds_deposit", f"TDS deposit (Challan 281) — {period}", 7),
            ]
            for entry_type, title, day in templates:
                due_month = month + 1 if month < 12 else 1
                due_year = year if month < 12 else year + 1
                last_day = monthrange(due_year, due_month)[1]
                due_day = min(day, last_day)
                due = date(due_year, due_month, due_day)
                if due < today:
                    continue

                exists = (
                    self.db.query(ComplianceCalendarEntry)
                    .filter(
                        ComplianceCalendarEntry.organization_id == ctx.organization_id,
                        ComplianceCalendarEntry.entry_type == entry_type,
                        ComplianceCalendarEntry.due_date == due,
                        ComplianceCalendarEntry.reference_period == period,
                    )
                    .first()
                )
                if exists:
                    continue

                entry = ComplianceCalendarEntry(
                    organization_id=ctx.organization_id,
                    title=title,
                    entry_type=entry_type,
                    due_date=due,
                    reference_period=period,
                    status=ComplianceEntryStatus.pending,
                )
                self.db.add(entry)
                created.append(entry)

        self.db.flush()
        return created

    def list_entries(
        self,
        ctx: OrganizationContext,
        *,
        days_ahead: int = 90,
    ) -> list[dict]:
        cutoff = date.today() + timedelta(days=days_ahead)
        rows = (
            self.db.query(ComplianceCalendarEntry)
            .filter(
                ComplianceCalendarEntry.organization_id == ctx.organization_id,
                ComplianceCalendarEntry.due_date <= cutoff,
                ComplianceCalendarEntry.status != ComplianceEntryStatus.skipped,
            )
            .order_by(ComplianceCalendarEntry.due_date)
            .all()
        )
        return [
            {
                "id": str(r.id),
                "title": r.title,
                "entry_type": r.entry_type,
                "due_date": r.due_date.isoformat(),
                "reference_period": r.reference_period,
                "status": r.status.value,
                "notes": r.notes,
            }
            for r in rows
        ]

    def mark_completed(
        self,
        ctx: OrganizationContext,
        entry_id,
    ) -> ComplianceCalendarEntry:
        entry = (
            self.db.query(ComplianceCalendarEntry)
            .filter(
                ComplianceCalendarEntry.id == entry_id,
                ComplianceCalendarEntry.organization_id == ctx.organization_id,
            )
            .first()
        )
        if not entry:
            from app.core.exceptions import NotFoundError

            raise NotFoundError("Compliance entry not found")
        entry.status = ComplianceEntryStatus.completed
        self.db.flush()
        return entry
