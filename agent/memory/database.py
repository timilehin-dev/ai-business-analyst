"""
Database Layer with Encryption and Vector Support.
Handles secure config storage and future memory systems.
"""
import os
import json
from typing import Optional, Dict, Any
from sqlalchemy import create_engine, Column, String, Text, Boolean, DateTime, func, Integer
from sqlalchemy.orm import sessionmaker, declarative_base
from cryptography.fernet import Fernet

Base = declarative_base()

class ChatHistoryRecord(Base):
    """Persistent chat/query history — survives across sessions."""
    __tablename__ = "chat_history"
    id = Column(Integer, primary_key=True)
    question = Column(Text, nullable=False)
    sql_query = Column(Text, nullable=True)
    answer = Column(Text, nullable=True)
    confidence = Column(String, nullable=True)
    timestamp = Column(DateTime, default=func.now())

class ConfigStore(Base):
    """Encrypted storage for user configurations and API keys."""
    __tablename__ = "config_store"

    key = Column(String, primary_key=True)
    value_encrypted = Column(Text, nullable=False)
    is_sensitive = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

class DatabaseManager:
    def __init__(self, database_url: Optional[str] = None):
        # Default to SQLite for zero-config MVP, switch to Postgres in prod.
        # Respect the DATABASE_URL env var / settings when provided.
        self.data_dir = os.environ.get("DATA_DIR", os.path.join(os.getcwd(), "data"))

        if database_url is None:
            try:
                from api.config import settings
                database_url = settings.database.url
            except Exception:
                database_url = None

        if database_url is None or database_url == "sqlite:///./data/analyst.db":
            db_path = os.path.join(self.data_dir, "analyst.db")
            os.makedirs(os.path.dirname(db_path), exist_ok=True)
            self.database_url = f"sqlite:///{db_path}"
        else:
            self.database_url = database_url

        self.engine = create_engine(
            self.database_url, 
            connect_args={"check_same_thread": False} if "sqlite" in self.database_url else {}
        )
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
        # Initialize encryption key (in prod, this should come from a secure env var or vault)
        # For MVP, we generate one and store it in the data folder if it doesn't exist
        self.fernet = self._load_or_generate_key()
        
        Base.metadata.create_all(bind=self.engine)

    def _load_or_generate_key(self) -> Fernet:
        key_path = os.path.join(self.data_dir, ".secret_key")
        os.makedirs(os.path.dirname(key_path), exist_ok=True)
        
        if os.path.exists(key_path):
            with open(key_path, "rb") as f:
                key = f.read()
        else:
            key = Fernet.generate_key()
            with open(key_path, "wb") as f:
                f.write(key)
        return Fernet(key)

    def save_config(self, key: str, value: Any, is_sensitive: bool = True):
        """Save configuration with automatic encryption for sensitive data."""
        session = self.SessionLocal()
        try:
            if is_sensitive:
                value_str = json.dumps(value) if not isinstance(value, str) else value
                encrypted_value = self.fernet.encrypt(value_str.encode()).decode()
            else:
                encrypted_value = json.dumps(value) if not isinstance(value, str) else value

            existing = session.query(ConfigStore).filter_by(key=key).first()
            if existing:
                existing.value_encrypted = encrypted_value
                existing.is_sensitive = is_sensitive
            else:
                new_config = ConfigStore(
                    key=key, 
                    value_encrypted=encrypted_value, 
                    is_sensitive=is_sensitive
                )
                session.add(new_config)
            
            session.commit()
        finally:
            session.close()

    def get_config(self, key: str, is_sensitive: bool = True) -> Optional[Any]:
        """Retrieve and decrypt configuration."""
        session = self.SessionLocal()
        try:
            record = session.query(ConfigStore).filter_by(key=key).first()
            if not record:
                return None
            
            if is_sensitive and record.is_sensitive:
                decrypted = self.fernet.decrypt(record.value_encrypted.encode()).decode()
                try:
                    return json.loads(decrypted)
                except json.JSONDecodeError:
                    return decrypted
            else:
                try:
                    return json.loads(record.value_encrypted)
                except json.JSONDecodeError:
                    return record.value_encrypted
        finally:
            session.close()

    def is_configured(self) -> bool:
        """Check if the system has been set up via the wizard."""
        return self.get_config("setup_complete", is_sensitive=False) is True

    def clear_config(self) -> int:
        """Delete ALL configuration entries. Data tables are untouched.
        Returns the number of config rows removed."""
        session = self.SessionLocal()
        try:
            count = session.query(ConfigStore).delete()
            session.commit()
            return count
        finally:
            session.close()

    # ==================== CHAT HISTORY ====================
    def save_chat_history(self, question: str, sql_query: str = None, answer: str = None, confidence: float = None):
        session = self.SessionLocal()
        try:
            rec = ChatHistoryRecord(
                question=question,
                sql_query=sql_query,
                answer=answer,
                confidence=str(confidence) if confidence is not None else None,
            )
            session.add(rec)
            session.commit()
            return rec.id
        finally:
            session.close()

    def get_chat_history(self, limit: int = 20) -> list:
        session = self.SessionLocal()
        try:
            rows = session.query(ChatHistoryRecord).order_by(ChatHistoryRecord.timestamp.desc()).limit(limit).all()
            return [
                {"id": r.id, "question": r.question, "sql_query": r.sql_query,
                 "answer": r.answer, "confidence": r.confidence, "timestamp": r.timestamp.isoformat() if r.timestamp else None}
                for r in rows
            ]
        finally:
            session.close()

# Global instance
db_manager = DatabaseManager()
