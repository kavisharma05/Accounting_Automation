import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models.entities  # noqa: F401 — register ORM models
from app.core.database import Base, get_db
from app.main import app as fastapi_app


@pytest.fixture
def client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine)

    def override_get_db():
        db = TestSession()
        try:
            yield db
        finally:
            db.close()

    fastapi_app.dependency_overrides[get_db] = override_get_db
    with TestClient(fastapi_app) as c:
        yield c
    fastapi_app.dependency_overrides.clear()


def test_health(client):
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_create_organization_and_accounts(client):
    org_resp = client.post(
        "/api/v1/organizations",
        json={"name": "Acme Pvt Ltd", "gstin": "29AABCU9603R1ZM"},
    )
    assert org_resp.status_code == 200
    org_id = org_resp.json()["id"]

    # COA seeded on org creation (9 default accounts per PRD_DECISIONS Q-25)
    custom = client.post(
        f"/api/v1/organizations/{org_id}/accounts",
        json={"code": "5100", "name": "Travel Expense", "account_type": "expense"},
    )
    assert custom.status_code == 200

    mapping = client.post(
        f"/api/v1/organizations/{org_id}/phone-mappings",
        json={"phone_e164": "+919876543210"},
    )
    assert mapping.status_code == 200
