"""
Document Store - the knowledge graph.

Documents live in the analyst's own database (analyst.db), separate from the
user's business database. Tables are created on the same SQLAlchemy Base as
the config store, so they are picked up by create_all.

Schema:
  documents       - one row per ingested document, UNIQUE(source, source_id)
  connector_state - per-connector sync state (last sync, cursor, error)
"""
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    Column,
    DateTime,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import sessionmaker

from agent.memory.database import Base, db_manager
from agent.connectors.base import Document


class DocumentRecord(Base):
    __tablename__ = "documents"
    __table_args__ = (UniqueConstraint("source", "source_id", name="uq_doc_source_id"),)

    id = Column(Integer, primary_key=True)
    source = Column(String, nullable=False, index=True)
    source_id = Column(String, nullable=False)
    title = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    metadata_json = Column(Text, nullable=False, default="{}")
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class ConnectorStateRecord(Base):
    __tablename__ = "connector_state"

    connector_id = Column(String, primary_key=True)
    config_json = Column(Text, nullable=False, default="{}")
    last_sync_at = Column(DateTime, nullable=True)
    last_error = Column(Text, nullable=True)


class DocumentStore:
    """Upsert/query documents and connector state in the analyst DB."""

    def __init__(self):
        self.engine = db_manager.engine
        self.SessionLocal = db_manager.SessionLocal
        # Ensure tables exist even if this module is imported after
        # DatabaseManager.__init__ already ran create_all.
        Base.metadata.create_all(bind=self.engine)

    # ==================== DOCUMENTS ====================

    def save_document(self, doc: Document) -> bool:
        """Upsert one document. Returns True if created, False if updated."""
        session = self.SessionLocal()
        try:
            existing = (
                session.query(DocumentRecord)
                .filter_by(source=doc.source, source_id=doc.source_id)
                .first()
            )
            metadata_json = json.dumps(doc.metadata, default=str)
            if existing:
                existing.title = doc.title
                existing.content = doc.content
                existing.metadata_json = metadata_json
                existing.updated_at = datetime.now(timezone.utc)
                created = False
            else:
                session.add(
                    DocumentRecord(
                        source=doc.source,
                        source_id=doc.source_id,
                        title=doc.title,
                        content=doc.content,
                        metadata_json=metadata_json,
                    )
                )
                created = True
            session.commit()
            return created
        finally:
            session.close()

    def save_documents(self, docs: List[Document]) -> Dict[str, int]:
        """Upsert many documents. Returns {'created': n, 'updated': n}."""
        created = updated = 0
        for doc in docs:
            if self.save_document(doc):
                created += 1
            else:
                updated += 1
        return {"created": created, "updated": updated}

    def list_documents(
        self, source: Optional[str] = None, limit: int = 100, offset: int = 0
    ) -> List[Dict[str, Any]]:
        session = self.SessionLocal()
        try:
            q = session.query(DocumentRecord)
            if source:
                q = q.filter_by(source=source)
            rows = q.order_by(DocumentRecord.updated_at.desc()).limit(limit).offset(offset).all()
            return [self._to_dict(r) for r in rows]
        finally:
            session.close()

    def count_documents(self, source: Optional[str] = None) -> int:
        session = self.SessionLocal()
        try:
            q = session.query(DocumentRecord)
            if source:
                q = q.filter_by(source=source)
            return q.count()
        finally:
            session.close()

    def delete_document(self, doc_id: int) -> bool:
        session = self.SessionLocal()
        try:
            row = session.query(DocumentRecord).filter_by(id=doc_id).first()
            if not row:
                return False
            session.delete(row)
            session.commit()
            return True
        finally:
            session.close()

    def delete_source(self, source: str) -> int:
        session = self.SessionLocal()
        try:
            deleted = session.query(DocumentRecord).filter_by(source=source).delete()
            session.commit()
            return deleted
        finally:
            session.close()

    def all_content(self, limit: int = 200) -> str:
        """Concatenated document text for the analyst's context window."""
        docs = self.list_documents(limit=limit)
        if not docs:
            return ""
        parts = []
        for d in docs:
            parts.append(f"--- [{d['source']}] {d['title']} ---\n{d['content']}")
        return "\n\n".join(parts)

    @staticmethod
    def _to_dict(rec: DocumentRecord) -> Dict[str, Any]:
        try:
            metadata = json.loads(rec.metadata_json or "{}")
        except json.JSONDecodeError:
            metadata = {}
        return {
            "id": rec.id,
            "source": rec.source,
            "source_id": rec.source_id,
            "title": rec.title,
            "content": rec.content,
            "metadata": metadata,
            "created_at": rec.created_at.isoformat() if rec.created_at else None,
            "updated_at": rec.updated_at.isoformat() if rec.updated_at else None,
        }

    # ==================== CONNECTOR STATE ====================

    def get_state(self, connector_id: str) -> Dict[str, Any]:
        session = self.SessionLocal()
        try:
            rec = session.query(ConnectorStateRecord).filter_by(connector_id=connector_id).first()
            if not rec:
                return {"connector_id": connector_id, "config": {}, "last_sync_at": None, "last_error": None}
            try:
                config = json.loads(rec.config_json or "{}")
            except json.JSONDecodeError:
                config = {}
            return {
                "connector_id": connector_id,
                "config": config,
                "last_sync_at": rec.last_sync_at.isoformat() if rec.last_sync_at else None,
                "last_error": rec.last_error,
            }
        finally:
            session.close()

    def save_state(self, connector_id: str, config: Optional[Dict[str, Any]] = None,
                   last_error: Optional[str] = None) -> None:
        session = self.SessionLocal()
        try:
            rec = session.query(ConnectorStateRecord).filter_by(connector_id=connector_id).first()
            if not rec:
                rec = ConnectorStateRecord(connector_id=connector_id)
                session.add(rec)
            if config is not None:
                rec.config_json = json.dumps(config, default=str)
            rec.last_sync_at = datetime.now(timezone.utc)
            rec.last_error = last_error
            session.commit()
        finally:
            session.close()


# Global instance
document_store = DocumentStore()