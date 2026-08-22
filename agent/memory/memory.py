"""
Persistent memory layers + audit log.

Three memory types, each with a distinct retrieval role:

  semantic   - what words mean here (glossary: "ARR", "active customer")
  episodic   - what was analysed before (question -> SQL -> answer + feedback)
  procedural - rules learned from corrections ("always exclude test accounts")

Episodic memory is the substrate for learning: a thumbs-down with a written
correction is promoted into a procedural rule, which is then injected into
every future plan. That is the whole feedback loop.

The audit log is separate and append-only: it records what the system did,
not what it learned.
"""
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)

from agent.memory.database import Base, db_manager
from agent.memory.retrieval import score_documents, snippet

# Feedback below this rating (1-5) is treated as a correction signal.
NEGATIVE_RATING_THRESHOLD = 3


# ==================== TABLES ====================

class SemanticMemory(Base):
    """Business vocabulary: term -> definition."""

    __tablename__ = "memory_semantic"
    __table_args__ = (UniqueConstraint("term", name="uq_semantic_term"),)

    id = Column(Integer, primary_key=True)
    term = Column(String, nullable=False, index=True)
    definition = Column(Text, nullable=False)
    source = Column(String, default="user")  # user | schema | inferred
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class EpisodicMemory(Base):
    """One past analysis, plus any feedback it received."""

    __tablename__ = "memory_episodic"

    id = Column(Integer, primary_key=True)
    question = Column(Text, nullable=False)
    sql_query = Column(Text, nullable=True)
    answer = Column(Text, nullable=True)
    confidence = Column(Float, nullable=True)
    rating = Column(Integer, nullable=True)  # 1-5, set by feedback
    correction = Column(Text, nullable=True)  # user's written correction
    created_at = Column(DateTime, default=func.now(), index=True)


class ProceduralMemory(Base):
    """A learned rule applied to future analyses."""

    __tablename__ = "memory_procedural"
    __table_args__ = (UniqueConstraint("rule", name="uq_procedural_rule"),)

    id = Column(Integer, primary_key=True)
    rule = Column(Text, nullable=False)
    source_episode_id = Column(Integer, nullable=True)
    active = Column(Boolean, default=True)
    times_applied = Column(Integer, default=0)
    created_at = Column(DateTime, default=func.now())


class AuditLog(Base):
    """Append-only record of consequential actions."""

    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=func.now(), index=True)
    action = Column(String, nullable=False, index=True)
    actor = Column(String, default="system")
    detail_json = Column(Text, nullable=False, default="{}")
    success = Column(Boolean, default=True)


# ==================== STORE ====================

class MemoryStore:
    """Read/write access to all memory layers and the audit log."""

    def __init__(self):
        self.engine = db_manager.engine
        self.SessionLocal = db_manager.SessionLocal
        Base.metadata.create_all(bind=self.engine)

    # SessionLocal is re-read on each call because tests monkeypatch the
    # db_manager singleton onto a temp database after this object is built.
    def _session(self):
        return db_manager.SessionLocal()

    # ---------- semantic ----------

    def add_term(self, term: str, definition: str, source: str = "user") -> Dict[str, Any]:
        session = self._session()
        try:
            existing = session.query(SemanticMemory).filter_by(term=term).first()
            if existing:
                existing.definition = definition
                existing.source = source
            else:
                existing = SemanticMemory(term=term, definition=definition, source=source)
                session.add(existing)
            session.commit()
            return {"term": existing.term, "definition": existing.definition, "source": existing.source}
        finally:
            session.close()

    def list_terms(self, limit: int = 200) -> List[Dict[str, Any]]:
        session = self._session()
        try:
            rows = session.query(SemanticMemory).order_by(SemanticMemory.term).limit(limit).all()
            return [
                {
                    "id": r.id,
                    "term": r.term,
                    "definition": r.definition,
                    "source": r.source,
                    "updated_at": r.updated_at.isoformat() if r.updated_at else None,
                }
                for r in rows
            ]
        finally:
            session.close()

    def delete_term(self, term_id: int) -> bool:
        session = self._session()
        try:
            row = session.query(SemanticMemory).filter_by(id=term_id).first()
            if not row:
                return False
            session.delete(row)
            session.commit()
            return True
        finally:
            session.close()

    def relevant_terms(self, question: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Glossary entries whose term or definition matches the question."""
        terms = self.list_terms()
        if not terms:
            return []
        ranked = score_documents(
            question, terms, key=lambda t: f"{t['term']} {t['definition']}", limit=limit
        )
        return [t for t, _ in ranked]

    # ---------- episodic ----------

    def record_episode(
        self,
        question: str,
        sql_query: Optional[str] = None,
        answer: Optional[str] = None,
        confidence: Optional[float] = None,
    ) -> int:
        session = self._session()
        try:
            episode = EpisodicMemory(
                question=question, sql_query=sql_query, answer=answer, confidence=confidence
            )
            session.add(episode)
            session.commit()
            return episode.id
        finally:
            session.close()

    def add_feedback(
        self, episode_id: int, rating: int, correction: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Attach feedback to an episode. A low rating with a written correction
        is promoted to a procedural rule so it changes future behaviour.
        """
        session = self._session()
        try:
            episode = session.query(EpisodicMemory).filter_by(id=episode_id).first()
            if not episode:
                return None
            episode.rating = rating
            episode.correction = correction
            session.commit()
            result = {
                "episode_id": episode.id,
                "rating": rating,
                "correction": correction,
                "rule_created": False,
            }
        finally:
            session.close()

        if correction and correction.strip() and rating <= NEGATIVE_RATING_THRESHOLD:
            rule = self.add_rule(correction.strip(), source_episode_id=episode_id)
            result["rule_created"] = bool(rule)
        return result

    def list_episodes(self, limit: int = 20) -> List[Dict[str, Any]]:
        session = self._session()
        try:
            rows = (
                session.query(EpisodicMemory)
                .order_by(EpisodicMemory.created_at.desc())
                .limit(limit)
                .all()
            )
            return [self._episode_dict(r) for r in rows]
        finally:
            session.close()

    def similar_episodes(self, question: str, limit: int = 3) -> List[Dict[str, Any]]:
        """
        Past analyses resembling this question.

        Only well-rated or unrated episodes are recalled — replaying an
        analysis the user rejected would teach the agent its own mistakes.
        """
        session = self._session()
        try:
            rows = (
                session.query(EpisodicMemory)
                .order_by(EpisodicMemory.created_at.desc())
                .limit(200)
                .all()
            )
            candidates = [
                self._episode_dict(r)
                for r in rows
                if r.rating is None or r.rating > NEGATIVE_RATING_THRESHOLD
            ]
        finally:
            session.close()

        ranked = score_documents(question, candidates, key=lambda e: e["question"], limit=limit)
        return [e for e, _ in ranked]

    @staticmethod
    def _episode_dict(row: EpisodicMemory) -> Dict[str, Any]:
        return {
            "id": row.id,
            "question": row.question,
            "sql_query": row.sql_query,
            "answer": row.answer,
            "confidence": row.confidence,
            "rating": row.rating,
            "correction": row.correction,
            "timestamp": row.created_at.isoformat() if row.created_at else None,
        }

    # ---------- procedural ----------

    def add_rule(self, rule: str, source_episode_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
        session = self._session()
        try:
            existing = session.query(ProceduralMemory).filter_by(rule=rule).first()
            if existing:
                existing.active = True
                session.commit()
                return {"id": existing.id, "rule": existing.rule, "active": True}
            row = ProceduralMemory(rule=rule, source_episode_id=source_episode_id)
            session.add(row)
            session.commit()
            return {"id": row.id, "rule": row.rule, "active": True}
        finally:
            session.close()

    def list_rules(self, active_only: bool = True, limit: int = 100) -> List[Dict[str, Any]]:
        session = self._session()
        try:
            q = session.query(ProceduralMemory)
            if active_only:
                q = q.filter_by(active=True)
            rows = q.order_by(ProceduralMemory.created_at.desc()).limit(limit).all()
            return [
                {
                    "id": r.id,
                    "rule": r.rule,
                    "active": r.active,
                    "times_applied": r.times_applied,
                    "source_episode_id": r.source_episode_id,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
                for r in rows
            ]
        finally:
            session.close()

    def deactivate_rule(self, rule_id: int) -> bool:
        session = self._session()
        try:
            row = session.query(ProceduralMemory).filter_by(id=rule_id).first()
            if not row:
                return False
            row.active = False
            session.commit()
            return True
        finally:
            session.close()

    def mark_rules_applied(self, rule_ids: List[int]) -> None:
        if not rule_ids:
            return
        session = self._session()
        try:
            for row in session.query(ProceduralMemory).filter(ProceduralMemory.id.in_(rule_ids)):
                row.times_applied = (row.times_applied or 0) + 1
            session.commit()
        finally:
            session.close()

    # ---------- audit ----------

    def audit(
        self,
        action: str,
        detail: Optional[Dict[str, Any]] = None,
        actor: str = "system",
        success: bool = True,
    ) -> None:
        """Append an audit entry. Never raises — auditing must not break a request."""
        try:
            session = self._session()
            try:
                session.add(
                    AuditLog(
                        action=action,
                        actor=actor,
                        detail_json=json.dumps(detail or {}, default=str),
                        success=success,
                    )
                )
                session.commit()
            finally:
                session.close()
        except Exception:
            pass

    def list_audit(
        self, limit: int = 100, action: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        session = self._session()
        try:
            q = session.query(AuditLog)
            if action:
                q = q.filter_by(action=action)
            rows = q.order_by(AuditLog.timestamp.desc()).limit(limit).all()
            out = []
            for r in rows:
                try:
                    detail = json.loads(r.detail_json or "{}")
                except json.JSONDecodeError:
                    detail = {}
                out.append(
                    {
                        "id": r.id,
                        "timestamp": r.timestamp.isoformat() if r.timestamp else None,
                        "action": r.action,
                        "actor": r.actor,
                        "detail": detail,
                        "success": r.success,
                    }
                )
            return out
        finally:
            session.close()

    # ---------- glossary bootstrapping ----------

    def generate_glossary_from_schema(self, db_conn, max_terms: int = 50) -> int:
        """
        Seed the glossary from table/column names so the analyst starts with
        a vocabulary. Only fills gaps — user definitions are never overwritten.
        """
        try:
            from sqlalchemy import inspect as sa_inspect

            inspector = sa_inspect(db_conn.engine)
            tables = inspector.get_table_names()
        except Exception:
            return 0

        internal = {
            "config_store", "documents", "connector_state", "briefings",
            "chat_history", "memory_semantic", "memory_episodic",
            "memory_procedural", "audit_log",
        }
        existing = {t["term"] for t in self.list_terms()}
        added = 0

        for table in tables:
            if table in internal or added >= max_terms:
                continue
            try:
                columns = inspector.get_columns(table)
            except Exception:
                continue
            column_names = ", ".join(c["name"] for c in columns[:12])
            if table not in existing:
                self.add_term(
                    table,
                    f"Table '{table}' with columns: {column_names}.",
                    source="schema",
                )
                added += 1

        return added


memory_store = MemoryStore()
