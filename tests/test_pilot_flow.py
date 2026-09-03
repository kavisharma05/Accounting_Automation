"""Pilot flow API tests — document upload through posting."""

from io import BytesIO

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models.entities  # noqa: F401
from app.core.database import Base, get_db
from app.main import app as fastapi_app


def test_pilot_flow_end_to_end():
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

    with TestClient(fastapi_app) as client:
        org = client.post("/api/v1/organizations", json={"name": "Pilot Co", "gstin": "29AABCU9603R1ZM"})
        assert org.status_code == 200
        org_id = org.json()["id"]

        cfg = client.get(f"/api/v1/organizations/{org_id}/pilot-config")
        assert cfg.status_code == 200
        assert cfg.json()["default_expense_account_id"]

        upload = client.post(
            f"/api/v1/organizations/{org_id}/documents/upload",
            files={"file": ("inv.jpg", BytesIO(b"invoice"), "image/jpeg")},
        )
        assert upload.status_code == 200
        doc_id = upload.json()["document_id"]

        propose = client.post(
            f"/api/v1/organizations/{org_id}/documents/{doc_id}/propose-invoice",
        )
        assert propose.status_code == 200
        assert propose.json()["status"] == "pending_approval"

        pending = client.get(f"/api/v1/organizations/{org_id}/invoices/pending")
        assert pending.status_code == 200
        assert len(pending.json()) == 1

        confirm = client.post(
            f"/api/v1/organizations/{org_id}/invoices/confirm-pending",
            headers={"X-Organization-Id": org_id},
        )
        assert confirm.status_code == 200
        assert confirm.json()["journal_entry_id"]

        ledger = client.get(
            f"/api/v1/organizations/{org_id}/reports/ledger.xlsx",
            headers={"X-Organization-Id": org_id},
        )
        assert ledger.status_code == 200
        assert len(ledger.content) > 50

    fastapi_app.dependency_overrides.clear()
