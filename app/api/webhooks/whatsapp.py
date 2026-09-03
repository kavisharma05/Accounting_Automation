import json

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.config import settings
from app.core.exceptions import ValidationError
from app.core.security import verify_whatsapp_signature
from app.domain.organizations.pilot_config import get_org_account_defaults
from app.integrations.protocols import OutboundMessage
from app.services.messaging_service import MessagingService

router = APIRouter()


@router.get("/whatsapp")
def whatsapp_verify(
    hub_mode: str = Query(alias="hub.mode"),
    hub_verify_token: str = Query(alias="hub.verify_token"),
    hub_challenge: str = Query(alias="hub.challenge"),
):
    if hub_mode == "subscribe" and hub_verify_token == settings.whatsapp_verify_token:
        return int(hub_challenge)
    raise HTTPException(403, "Verification failed")


@router.post("/whatsapp")
async def whatsapp_webhook(
    request: Request,
    db: Session = Depends(get_db),
):
    from app.core.rate_limit import get_webhook_limiter

    client_ip = request.client.host if request.client else "unknown"
    limiter = get_webhook_limiter(settings.webhook_rate_limit_per_minute)
    if not limiter.allow(client_ip):
        raise HTTPException(429, "Rate limit exceeded")

    body = await request.body()
    if not verify_whatsapp_signature(body, request.headers.get("X-Hub-Signature-256")):
        raise HTTPException(401, "Invalid signature")

    payload = json.loads(body)
    svc = MessagingService(db)
    messaging = svc.messaging
    messages = await messaging.parse_webhook(payload)

    for msg in messages:
        ctx = svc.resolve_org_from_phone(msg.from_phone)
        if not ctx:
            await messaging.send_message(
                OutboundMessage(
                    to_phone=msg.from_phone,
                    text="Phone not registered. Contact your administrator.",
                )
            )
            continue

        expense_id = payable_id = tax_id = None
        try:
            expense_id, payable_id, tax_id = get_org_account_defaults(db, ctx.organization_id)
        except ValidationError:
            pass

        media_content = None
        mime_type = None
        if msg.media_id:
            media_content, mime_type = await messaging.download_media(msg.media_id)

        await svc.handle_inbound(
            ctx,
            media_content=media_content,
            mime_type=mime_type,
            text=msg.text,
            from_phone=msg.from_phone,
            expense_account_id=expense_id,
            payable_account_id=payable_id,
            input_tax_account_id=tax_id,
        )

    db.commit()
    return {"status": "ok"}
