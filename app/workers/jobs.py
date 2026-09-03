import logging
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

from app.core.database import SessionLocal
from app.core.logging import OrganizationContext
from app.integrations.factory import get_messaging_provider
from app.integrations.protocols import DocumentExtraction, ExtractionLineItem, OutboundMessage
from app.models.entities import AIExtractionRecord, BackgroundJob, JobStatus
from app.services.document_service import DocumentService
from app.services.invoice_service import InvoiceService

logger = logging.getLogger(__name__)


def enqueue_extract_and_propose(
    organization_id: str,
    document_id: str,
    from_phone: str,
    expense_account_id: str | None,
    payable_account_id: str | None,
    input_tax_account_id: str | None,
) -> str:
    from app.workers.queue import get_queue

    idempotency_key = f"extract-{document_id}"
    queue = get_queue()
    job = queue.enqueue(
        run_extract_and_propose,
        organization_id,
        document_id,
        from_phone,
        expense_account_id,
        payable_account_id,
        input_tax_account_id,
        job_id=idempotency_key,
    )
    return job.id


def run_extract_and_propose(
    organization_id: str,
    document_id: str,
    from_phone: str,
    expense_account_id: str | None,
    payable_account_id: str | None,
    input_tax_account_id: str | None,
) -> None:
    db = SessionLocal()
    idempotency_key = f"extract-{document_id}"
    try:
        bg = (
            db.query(BackgroundJob)
            .filter(
                BackgroundJob.organization_id == UUID(organization_id),
                BackgroundJob.idempotency_key == idempotency_key,
            )
            .first()
        )
        if bg and bg.status == JobStatus.succeeded:
            logger.info("Job already succeeded: %s", idempotency_key)
            return

        if not bg:
            bg = BackgroundJob(
                organization_id=UUID(organization_id),
                job_type="extract_and_propose",
                status=JobStatus.running,
                idempotency_key=idempotency_key,
                payload={"document_id": document_id},
            )
            db.add(bg)
        else:
            bg.status = JobStatus.running
            bg.attempts += 1
        db.commit()

        ctx = OrganizationContext(organization_id=UUID(organization_id), phone=from_phone)
        record = _sync_extract(db, ctx, UUID(document_id))

        extracted = record.extracted_data
        extraction = DocumentExtraction(
            vendor_name=extracted.get("vendor_name"),
            vendor_gstin=extracted.get("vendor_gstin"),
            invoice_number=extracted.get("invoice_number"),
            invoice_date=date.fromisoformat(extracted["invoice_date"]) if extracted.get("invoice_date") else None,
            invoice_type=extracted.get("invoice_type", "purchase"),
            subtotal=Decimal(extracted.get("subtotal", "0")),
            tax_total=Decimal(extracted.get("tax_total", "0")),
            total=Decimal(extracted.get("total", "0")),
            line_items=[
                ExtractionLineItem(
                    description="Line",
                    quantity=Decimal("1"),
                    unit_price=Decimal(extracted.get("subtotal", "0")),
                    tax_rate=Decimal("18"),
                    line_total=Decimal(extracted.get("subtotal", "0")),
                )
            ],
            confidence=float(extracted.get("confidence", 0)),
            raw=extracted,
        )

        inv_svc = InvoiceService(db)
        if expense_account_id and payable_account_id:
            inv = inv_svc.create_from_extraction(
                ctx,
                extraction,
                expense_account_id=UUID(expense_account_id),
                payable_account_id=UUID(payable_account_id),
                input_tax_account_id=UUID(input_tax_account_id) if input_tax_account_id else None,
            )
            messaging = get_messaging_provider()
            import asyncio

            asyncio.get_event_loop().run_until_complete(
                messaging.send_message(
                    OutboundMessage(
                        to_phone=from_phone,
                        text=(
                            f"Extracted invoice {inv.invoice_number} from {extraction.vendor_name} "
                            f"for ₹{inv.total}. Reply YES to confirm posting."
                        ),
                    )
                )
            )

        bg.status = JobStatus.succeeded
        db.commit()
    except Exception as exc:
        logger.exception("Job failed: %s", idempotency_key)
        db.rollback()
        bg = (
            db.query(BackgroundJob)
            .filter(
                BackgroundJob.organization_id == UUID(organization_id),
                BackgroundJob.idempotency_key == idempotency_key,
            )
            .first()
        )
        if bg:
            bg.status = JobStatus.failed
            bg.last_error = str(exc)
            if bg.attempts >= 3:
                bg.dead_letter_at = datetime.now(UTC)
            db.commit()
        raise
    finally:
        db.close()


def _sync_extract(db, ctx, document_id: UUID) -> AIExtractionRecord:
    import asyncio

    doc_svc = DocumentService(db)
    return asyncio.get_event_loop().run_until_complete(doc_svc.extract(ctx, document_id))
