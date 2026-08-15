"""
Integration tests: hit the FastAPI app via TestClient, backed by a fresh
in-memory SQLite DB per test.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import Base, get_db


@pytest.fixture
def client():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(bind=engine)

    def override_get_db():
        db = TestSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


def base_payload(**overrides):
    payload = dict(
        type="TRANSFER",
        amount=1000.0,
        name_orig="C1",
        oldbalance_org=5000.0,
        newbalance_orig=4000.0,
        name_dest="C2",
        oldbalance_dest=500.0,
        newbalance_dest=1500.0,
    )
    payload.update(overrides)
    return payload


class TestTransactionEndpoint:
    def test_normal_transaction_not_flagged(self, client):
        resp = client.post("/transactions", json=base_payload())

        assert resp.status_code == 201
        body = resp.json()
        assert body["flagged_for_review"] is False

    def test_drained_account_flagged_high(self, client):
        resp = client.post("/transactions", json=base_payload(
            oldbalance_org=5000.0, amount=5000.0,
        ))

        body = resp.json()
        assert body["flagged_for_review"] is True
        rule_names = [a["rule_name"] for a in body["alerts"]]
        assert "FULL_ACCOUNT_DRAIN" in rule_names

    def test_low_severity_alone_does_not_flag(self, client):
        # A round amount alone (LOW severity) should NOT set
        # flagged_for_review -- full-dataset evaluation showed LOW-severity
        # rules add false positives without meaningfully improving recall.
        resp = client.post("/transactions", json=base_payload(
            amount=3000.0,  # round, but not draining or glitched
            oldbalance_org=50_000.0,
        ))

        body = resp.json()
        rule_names = [a["rule_name"] for a in body["alerts"]]
        assert "ROUND_AMOUNT" in rule_names
        assert body["flagged_for_review"] is False

    def test_invalid_type_rejected(self, client):
        resp = client.post("/transactions", json=base_payload(type="NOT_A_REAL_TYPE"))
        assert resp.status_code == 400

    def test_payment_type_never_flagged_even_if_drained(self, client):
        # PAYMENT type never contains fraud in the real data -- rules should
        # not apply to it even if the balance numbers look suspicious.
        resp = client.post("/transactions", json=base_payload(
            type="PAYMENT", oldbalance_org=5000.0, amount=5000.0,
        ))

        body = resp.json()
        assert body["alerts"] == []
        assert body["flagged_for_review"] is False


class TestAlertEndpoints:
    def test_filter_alerts_by_severity(self, client):
        client.post("/transactions", json=base_payload(oldbalance_org=5000.0, amount=5000.0))

        resp = client.get("/alerts", params={"severity": "HIGH"})
        assert resp.status_code == 200
        assert all(a["severity"] == "HIGH" for a in resp.json())

    def test_get_nonexistent_alert_404(self, client):
        resp = client.get("/alerts/9999")
        assert resp.status_code == 404


class TestStatsEndpoint:
    def test_stats_reflect_submitted_transactions(self, client):
        client.post("/transactions", json=base_payload())
        client.post("/transactions", json=base_payload(oldbalance_org=5000.0, amount=5000.0))

        resp = client.get("/stats")
        body = resp.json()
        assert body["total_transactions"] == 2
        assert body["total_alerts"] >= 1
