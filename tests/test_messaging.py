import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.models.entities import Organization, PhoneOrgMapping
from app.services.messaging_service import MessagingService


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_unregistered_phone_returns_none(db):
    svc = MessagingService(db)
    assert svc.resolve_org_from_phone("+919999999999") is None


def test_registered_phone_resolves_org(db):
    org = Organization(name="Acme")
    db.add(org)
    db.flush()
    db.add(PhoneOrgMapping(organization_id=org.id, phone_e164="+919876543210"))
    db.commit()
    svc = MessagingService(db)
    ctx = svc.resolve_org_from_phone("+919876543210")
    assert ctx is not None
    assert ctx.organization_id == org.id
