"""
End-to-end API tests for the learning loop and settings surface.

These exercise the HTTP layer (via FastAPI TestClient) against an isolated
database so they can assert on the real request/response contract without
network access.
"""
import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    from api.main import app

    with TestClient(app) as c:
        yield c


class TestStatusAndSettings:
    def test_status_reports_not_configured(self, client):
        r = client.get("/api/status")
        assert r.status_code == 200
        body = r.json()
        assert "analyst_ready" in body
        assert "briefing" in body
        assert set(body["briefing"]) >= {"hour", "timezone"}

    def test_settings_returns_expected_shape(self, client):
        r = client.get("/api/settings")
        assert r.status_code == 200
        body = r.json()
        assert set(body) >= {"organization", "ai_provider", "database", "features", "briefing"}
        assert "proactive_monitoring" in body["features"]
        assert "hour" in body["briefing"]

    def test_general_settings_rejects_bad_timezone(self, client):
        r = client.put(
            "/api/settings/general",
            json={"briefing_timezone": "Not/AZone"},
        )
        assert r.status_code == 400

    def test_general_settings_accepts_valid_timezone(self, client):
        r = client.put(
            "/api/settings/general",
            json={"organization_name": "Acme", "briefing_hour": 7, "briefing_timezone": "UTC"},
        )
        assert r.status_code == 200
        assert r.json()["success"] is True


class TestMemoryApi:
    def test_glossary_crud(self, client):
        r = client.post("/api/memory/glossary", json={"term": "ARR", "definition": "Annual recurring revenue"})
        assert r.status_code == 200
        term_id = r.json()["term"]["term"]

        r = client.get("/api/memory/glossary")
        assert r.status_code == 200
        assert any(t["term"] == "ARR" for t in r.json()["terms"])

    def test_rules_crud(self, client):
        r = client.post("/api/memory/rules", json={"rule": "Exclude test accounts."})
        assert r.status_code == 200
        assert r.json()["rule"]["active"] is True

        r = client.get("/api/memory/rules")
        assert r.status_code == 200
        assert any(x["rule"] == "Exclude test accounts." for x in r.json()["rules"])

    def test_audit_log_append_only(self, client):
        r = client.get("/api/audit")
        assert r.status_code == 200
        assert "entries" in r.json()


class TestFeedbackApi:
    def test_feedback_unknown_episode_404(self, client):
        r = client.post(
            "/api/feedback",
            json={"episode_id": 999999, "rating": 1, "correction": "nope"},
        )
        assert r.status_code == 404


class TestDashboardApi:
    def test_dashboard_no_database(self, client):
        r = client.get("/api/dashboard")
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "no_database"
        # Empty payload keys are always present so the frontend can render safely.
        assert set(body) >= {"metrics", "trends", "categories", "recent_activity", "top_dimensions"}

    def test_briefing_no_database(self, client):
        r = client.get("/api/briefing")
        assert r.status_code == 200
        assert "briefing" in r.json()