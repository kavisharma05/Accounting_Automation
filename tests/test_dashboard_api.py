"""Dashboard API integration tests."""

from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models.entities  # noqa: F401
from app.core.database import Base, get_db
from app.core.security import create_access_token
from app.domain.organizations.coa_seed import seed_chart_of_accounts
from app.domain.organizations.pilot_config import configure_pilot_accounts
from app.main import app as fastapi_app
from app.models.entities import (
    Invoice,
    InvoiceStatus,
    InvoiceType,
    MembershipRole,
    Organization,
    OrganizationMembership,
    Party,
    PartyType,
    User,
)


@pytest.fixture
def dashboard_client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine)
    session = TestSession()

    org = Organization(name="Dashboard Org", gstin="29AABCU9603R1ZM")
    session.add(org)
    session.flush()
    seed_chart_of_accounts(session, org.id)
    configure_pilot_accounts(session, org.id, auto_from_coa=True)

    user = User(email="dash@test.local", password_hash="test")
    session.add(user)
    session.flush()
    session.add(
        OrganizationMembership(
            organization_id=org.id,
            user_id=user.id,
            role=MembershipRole.owner,
        )
    )

    party = Party(
        organization_id=org.id,
        party_type=PartyType.vendor,
        name="Vendor",
    )
    session.add(party)
    session.flush()

    inv = Invoice(
        organization_id=org.id,
        party_id=party.id,
        invoice_type=InvoiceType.purchase,
        invoice_number="DASH-1",
        invoice_date=date.today(),
        subtotal=Decimal("1000"),
        tax_total=Decimal("180"),
        total=Decimal("1180"),
        status=InvoiceStatus.posted,
    )
    session.add(inv)
    session.commit()

    token = create_access_token(str(user.id), org.id, MembershipRole.owner.value)

    def override_get_db():
        db = TestSession()
        try:
            yield db
        finally:
            db.close()

    fastapi_app.dependency_overrides[get_db] = override_get_db
    with TestClient(fastapi_app) as client:
        yield client, org, token
    fastapi_app.dependency_overrides.clear()
    session.close()


def test_me_endpoint(dashboard_client):
    client, org, token = dashboard_client
    resp = client.get(
        "/api/v1/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["organization_id"] == str(org.id)
    assert data["organization_name"] == "Dashboard Org"
    assert data["role"] == "owner"


def test_dashboard_summary(dashboard_client):
    client, org, token = dashboard_client
    resp = client.get(
        f"/api/v1/organizations/{org.id}/dashboard",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "pending_approvals" in data
    assert "outstanding_total" in data
    assert isinstance(data["recent_journal_entries"], list)


def test_list_invoices(dashboard_client):
    client, org, token = dashboard_client
    resp = client.get(
        f"/api/v1/organizations/{org.id}/invoices",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    rows = resp.json()
    assert len(rows) >= 1
    assert rows[0]["invoice_number"] == "DASH-1"


def test_list_payments_empty(dashboard_client):
    client, org, token = dashboard_client
    resp = client.get(
        f"/api/v1/organizations/{org.id}/payments",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_parties_and_accounts(dashboard_client):
    client, org, token = dashboard_client
    headers = {"Authorization": f"Bearer {token}"}

    parties = client.get(f"/api/v1/organizations/{org.id}/parties", headers=headers)
    assert parties.status_code == 200
    assert len(parties.json()) >= 1

    accounts = client.get(f"/api/v1/organizations/{org.id}/accounts", headers=headers)
    assert accounts.status_code == 200
    codes = [a["code"] for a in accounts.json()]
    assert "1010" in codes
    assert "2000" in codes


def test_create_party(dashboard_client):
    client, org, token = dashboard_client
    resp = client.post(
        f"/api/v1/organizations/{org.id}/parties",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "New Customer Ltd", "party_type": "customer", "gstin": "29AABCU9603R1ZX"},
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "New Customer Ltd"


def test_list_invoices_by_type(dashboard_client):
    client, org, token = dashboard_client
    resp = client.get(
        f"/api/v1/organizations/{org.id}/invoices?invoice_type=purchase",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert all(i["invoice_type"] == "purchase" for i in resp.json())
