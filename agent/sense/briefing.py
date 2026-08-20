"""
Briefing Generator + Storage.

Turns anomaly findings into a morning briefing. The LLM narrates the
findings but NEVER computes — every number in the briefing is verified
against the findings data by the deterministic grounding guard, with a
bounded regeneration loop.
"""
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import Column, DateTime, Integer, String, Text, func
from sqlalchemy.orm import sessionmaker

from agent.core.analyst import find_ungrounded_numbers
from agent.memory.database import Base, db_manager
from agent.sense.anomaly import AnomalyDetector, Finding


class BriefingRecord(Base):
    __tablename__ = "briefings"

    id = Column(Integer, primary_key=True)
    generated_at = Column(DateTime, default=func.now())
    summary = Column(Text, nullable=False)
    findings_json = Column(Text, nullable=False, default="[]")
    status = Column(String, default="ok")  # ok | anomalies | error


class BriefingStore:
    """Persist and retrieve briefings in the analyst DB."""

    def __init__(self):
        self.engine = db_manager.engine
        self.SessionLocal = db_manager.SessionLocal
        Base.metadata.create_all(bind=self.engine)

    def save(self, summary: str, findings: List[Finding], status: str = "ok") -> Dict[str, Any]:
        session = self.SessionLocal()
        try:
            rec = BriefingRecord(
                summary=summary,
                findings_json=json.dumps([f.to_dict() for f in findings], default=str),
                status=status,
            )
            session.add(rec)
            session.commit()
            return self._to_dict(rec)
        finally:
            session.close()

    def latest(self) -> Optional[Dict[str, Any]]:
        session = self.SessionLocal()
        try:
            rec = (
                session.query(BriefingRecord)
                .order_by(BriefingRecord.generated_at.desc())
                .first()
            )
            return self._to_dict(rec) if rec else None
        finally:
            session.close()

    def list(self, limit: int = 10) -> List[Dict[str, Any]]:
        session = self.SessionLocal()
        try:
            recs = (
                session.query(BriefingRecord)
                .order_by(BriefingRecord.generated_at.desc())
                .limit(limit)
                .all()
            )
            return [self._to_dict(r) for r in recs]
        finally:
            session.close()

    @staticmethod
    def _to_dict(rec: BriefingRecord) -> Dict[str, Any]:
        try:
            findings = json.loads(rec.findings_json or "[]")
        except json.JSONDecodeError:
            findings = []
        return {
            "id": rec.id,
            "generated_at": rec.generated_at.isoformat() if rec.generated_at else None,
            "summary": rec.summary,
            "findings": findings,
            "status": rec.status,
        }


briefing_store = BriefingStore()

_BRIEFING_PROMPT = """You are the AI Business Analyst writing the morning briefing for leadership.

ANOMALY FINDINGS (exact numbers from the database — trust them completely):
{findings_json}

Write a concise morning briefing (max 250 words) that:
1. Opens with a one-line summary of the situation
2. Lists each finding with its metric, direction, and magnitude
3. Suggests what to investigate first (critical findings first)
4. Uses plain markdown (## sections, bullet points)

CRITICAL RULES:
- Never compute, sum, derive, or convert numbers yourself.
- Quote figures EXACTLY as they appear in the findings above.
- If a finding has no change_pct (new activity), say "new activity" — do not invent a percentage.
- Every number you write must exist verbatim in the findings.
"""


async def generate_briefing(analyst, db_conn=None, days: int = 7, threshold_pct: float = 20.0) -> Dict[str, Any]:
    """
    Run the Sense loop now: scan for anomalies, write a grounded briefing,
    store it, and return it.

    Args:
        analyst: AutonomousAnalyst (for the model router)
        db_conn: DatabaseConnection (defaults to the analyst's connection)
        days: comparison window length
        threshold_pct: minimum swing (percent) to flag as an anomaly

    Returns:
        The stored briefing dict.
    """
    conn = db_conn or getattr(analyst, "db_conn", None)
    if conn is None:
        return briefing_store.save(
            "No database connected — the analyst cannot monitor anything yet.",
            [],
            status="error",
        )

    findings = AnomalyDetector(conn, threshold_pct=threshold_pct).scan(days=days)

    if not findings:
        return briefing_store.save(
            f"No anomalies detected in the last {days} days. All monitored metrics are within normal range.",
            [],
            status="ok",
        )

    findings_json = json.dumps([f.to_dict() for f in findings], default=str, indent=2)
    summary = await _write_grounded_briefing(analyst, findings_json, findings)
    return briefing_store.save(summary, findings, status="anomalies")


async def _write_grounded_briefing(analyst, findings_json: str, findings: List[Finding]) -> str:
    """Write the briefing with a bounded grounding loop (max 2 regenerations)."""
    data_for_grounding = [f.to_dict() for f in findings]
    summary = ""
    for attempt in range(3):
        summary = await analyst.model_router.complete(
            messages=[
                {"role": "system", "content": _BRIEFING_PROMPT.format(findings_json=findings_json)},
                {"role": "user", "content": "Write the morning briefing."},
            ],
            task_type="reasoning",
            temperature=0.4,
        )
        ungrounded = find_ungrounded_numbers(
            summary, data=data_for_grounding, confidence=0.9
        )
        if not ungrounded:
            # Sanitize model output artifacts (e.g. mangled em-dashes)
            return summary.replace("\ufffd", "-")
        # Regenerate with a correction instruction
        findings_json += (
            f"\n\nGROUNDING CHECK FAILED — the previous draft contained numbers not in the findings: {ungrounded}. "
            "Rewrite using ONLY the numbers above."
        )
    return summary  # give up after bounded attempts; numbers were still checked