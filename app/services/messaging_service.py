from uuid import UUID

from sqlalchemy.orm import Session

from app.core.logging import OrganizationContext
from app.domain.organizations.pilot_config import get_org_account_defaults
from app.integrations.factory import get_messaging_provider
from app.integrations.protocols import OutboundMessage
from app.models.entities import PhoneOrgMapping
from app.services.document_service import DocumentService
from app.services.invoice_service import InvoiceService
from app.workers.jobs import enqueue_extract_and_propose


class MessagingService:
    def __init__(self, db: Session):
        self.db = db
        self.messaging = get_messaging_provider()
        self.documents = DocumentService(db)
        self.invoices = InvoiceService(db)

    def resolve_org_from_phone(self, phone: str) -> OrganizationContext | None:
        mapping = (
            self.db.query(PhoneOrgMapping)
            .filter(PhoneOrgMapping.phone_e164 == phone)
            .first()
        )
        if not mapping:
            return None
        return OrganizationContext(organization_id=mapping.organization_id, phone=phone)

    async def handle_inbound(
        self,
        ctx: OrganizationContext,
        *,
        media_content: bytes | None,
        mime_type: str | None,
        text: str | None,
        from_phone: str,
        expense_account_id: UUID | None = None,
        payable_account_id: UUID | None = None,
        input_tax_account_id: UUID | None = None,
    ) -> str:
        if text and text.strip().upper() in ("YES", "CONFIRM", "OK"):
            try:
                expense_id, payable_id, tax_id = get_org_account_defaults(self.db, ctx.organization_id)
            except Exception:
                expense_id = payable_id = tax_id = None
            return await self._handle_confirmation(
                ctx, from_phone, expense_id, payable_id, tax_id
            )

        if media_content and mime_type:
            try:
                expense_id, payable_id, tax_id = get_org_account_defaults(
                    self.db, ctx.organization_id
                )
            except Exception:
                expense_id = payable_id = tax_id = None
            doc = await self.documents.upload(ctx, media_content, mime_type)
            job_id = enqueue_extract_and_propose(
                str(ctx.organization_id),
                str(doc.id),
                from_phone,
                str(expense_account_id or expense_id) if (expense_account_id or expense_id) else None,
                str(payable_account_id or payable_id) if (payable_account_id or payable_id) else None,
                str(input_tax_account_id or tax_id) if (input_tax_account_id or tax_id) else None,
            )
            await self.messaging.send_message(
                OutboundMessage(
                    to_phone=from_phone,
                    text=f"Document received. Processing (job {job_id}). I'll ask you to confirm before posting.",
                )
            )
            return "processing"

        await self.messaging.send_message(
            OutboundMessage(
                to_phone=from_phone,
                text="Send an invoice image or PDF to record a purchase.",
            )
        )
        return "prompt"

    async def _handle_confirmation(
        self,
        ctx: OrganizationContext,
        from_phone: str,
        expense_account_id: UUID | None,
        payable_account_id: UUID | None,
        input_tax_account_id: UUID | None,
    ) -> str:
        from app.models.entities import ApprovalRequest

        pending = (
            self.db.query(ApprovalRequest)
            .filter(
                ApprovalRequest.organization_id == ctx.organization_id,
                ApprovalRequest.status == "pending",
                ApprovalRequest.entity_type == "invoice",
            )
            .order_by(ApprovalRequest.created_at.desc())
            .first()
        )
        if not pending or not expense_account_id or not payable_account_id:
            await self.messaging.send_message(
                OutboundMessage(
                    to_phone=from_phone,
                    text="No pending invoice to confirm, or accounts not configured.",
                )
            )
            return "no_pending"

        inv = self.invoices.confirm_and_post(
            ctx,
            pending.entity_id,
            expense_account_id=expense_account_id,
            payable_account_id=payable_account_id,
            input_tax_account_id=input_tax_account_id,
        )
        await self.messaging.send_message(
            OutboundMessage(
                to_phone=from_phone,
                text=f"Posted invoice {inv.invoice_number} for ₹{inv.total}. Journal entry created.",
            )
        )
        return "posted"
