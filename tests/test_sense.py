"""
Tests for the Sense loop: anomaly detection engine and briefing generation.
"""
import json
import os
import sqlite3
import tempfile
from datetime import datetime, timedelta, timezone

import pytest

from agent.connectors.sample_data import seed_sample_data
from agent.sense.anomaly import AnomalyDetector
from agent.sense.briefing import briefing_store, generate_briefing
from agent.tools.database import DatabaseConnection


@pytest.fixture
def sample_db():
    """Sample-data SQLite DB (deterministic seed)."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    seed_sample_data(f"sqlite:///{path}")
    yield DatabaseConnection(f"sqlite:///{path}")
    os.unlink(path)


class TestAnomalyDetector:
    def test_finds_candidate_tables(self, sample_db):
        detector = AnomalyDetector(sample_db)
        candidates = detector._candidate_metrics()
        tables = {c["table"] for c in candidates}
        # orders has a date col + numeric cols; products has no date column
        assert "orders" in tables
        assert "products" not in tables  # no date column
        # internal app tables are never monitored
        assert "config_store" not in tables
        metrics = {c["metric"] for c in candidates if c["table"] == "orders"}
        # surrogate keys (id, product_id, customer_id) are skipped — SUM(id) is meaningless
        assert {"quantity", "unit_price", "__row_count__"} <= metrics
        assert not {"id", "product_id", "customer_id"} & metrics

    def test_scan_returns_findings(self, sample_db):
        detector = AnomalyDetector(sample_db, threshold_pct=10.0)
        findings = detector.scan(days=7)
        assert isinstance(findings, list)
        for f in findings:
            assert f.table
            assert f.metric
            assert f.current >= 0
            assert f.severity in ("critical", "warning")
            assert f.direction in ("up", "down", "new")

    def test_scan_deterministic(self, sample_db):
        detector = AnomalyDetector(sample_db, threshold_pct=10.0)
        f1 = detector.scan(days=7)
        f2 = detector.scan(days=7)
        assert [f.to_dict() for f in f1] == [f.to_dict() for f in f2]

    def test_window_math_is_exact(self, sample_db):
        """The engine's numbers must match direct SQL aggregates."""
        detector = AnomalyDetector(sample_db, threshold_pct=0.0)  # flag everything
        now = datetime.now(timezone.utc)
        findings = detector.scan(days=7, now=now)

        # Verify every finding against a direct window query
        candidates = detector._candidate_metrics()
        for f in findings:
            cand = next(c for c in candidates if c["table"] == f.table and c["metric"] == f.metric)
            start_current = now - timedelta(days=7)
            start_previous = start_current - timedelta(days=7)
            current = detector._window_value(cand, start_current, now)
            previous = detector._window_value(cand, start_previous, start_current)
            assert current == f.current
            assert previous == f.previous

    def test_no_date_table_skipped(self):
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        conn = sqlite3.connect(path)
        conn.execute("CREATE TABLE products (id INTEGER PRIMARY KEY, price REAL)")
        conn.execute("INSERT INTO products (price) VALUES (10.0)")
        conn.commit()
        conn.close()
        try:
            db = DatabaseConnection(f"sqlite:///{path}")
            detector = AnomalyDetector(db)
            assert detector._candidate_metrics() == []
            assert detector.scan() == []
        finally:
            os.unlink(path)


class FakeModelRouter:
    def __init__(self, summary: str):
        self.summary = summary
        self.calls = 0

    async def complete(self, messages, task_type="reasoning", **kwargs):
        self.calls += 1
        return self.summary


class TestBriefing:
    def test_store_roundtrip(self):
        from agent.sense.anomaly import Finding

        f = Finding(
            table="orders", metric="unit_price", current=5000.0, previous=3000.0,
            change_pct=66.67, direction="up", severity="critical",
            window="last 7 days vs prior 7 days",
        )
        saved = briefing_store.save("Revenue spiked 66.67%.", [f], status="anomalies")
        assert saved["status"] == "anomalies"
        assert saved["findings"][0]["change_pct"] == 66.67
        latest = briefing_store.latest()
        assert latest is not None
        assert latest["summary"] == "Revenue spiked 66.67%."

    @pytest.mark.asyncio
    async def test_generate_with_no_anomalies(self):
        # A DB with no date columns → no candidates → deterministic "ok" branch
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        conn = sqlite3.connect(path)
        conn.execute("CREATE TABLE products (id INTEGER PRIMARY KEY, price REAL)")
        conn.execute("INSERT INTO products (price) VALUES (10.0)")
        conn.commit()
        conn.close()
        try:
            db = DatabaseConnection(f"sqlite:///{path}")

            class FakeAnalyst:
                db_conn = db
                model_router = FakeModelRouter("")

            briefing = await generate_briefing(FakeAnalyst(), days=7)
            assert briefing["status"] == "ok"
            assert briefing["findings"] == []
        finally:
            os.unlink(path)

    @pytest.mark.asyncio
    async def test_generate_with_anomalies_grounds_numbers(self, sample_db):
        # A summary that quotes findings exactly must pass the grounding check
        class FakeAnalyst:
            db_conn = sample_db
            model_router = FakeModelRouter("Revenue in orders grew. New activity detected.")

        briefing = await generate_briefing(FakeAnalyst(), days=7)
        assert briefing["status"] in ("ok", "anomalies")
        # summary must not contain numbers the model invented (it used none)
        assert briefing["summary"]

    @pytest.mark.asyncio
    async def test_generate_without_db(self):
        class FakeAnalyst:
            db_conn = None
            model_router = FakeModelRouter("")

        briefing = await generate_briefing(FakeAnalyst())
        assert briefing["status"] == "error"
        assert "No database" in briefing["summary"]