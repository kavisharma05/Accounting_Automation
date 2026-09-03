from app.models.entities import Organization, PhoneOrgMapping
from app.services.messaging_service import MessagingService


def test_unregistered_phone_returns_none(db):
    session, _ = db
    svc = MessagingService(session)
    assert svc.resolve_org_from_phone("+919999999999") is None


def test_registered_phone_resolves_org(db):
    session, org = db
    session.add(PhoneOrgMapping(organization_id=org.id, phone_e164="+919876543210"))
    session.commit()
    svc = MessagingService(session)
    ctx = svc.resolve_org_from_phone("+919876543210")
    assert ctx is not None
    assert ctx.organization_id == org.id
