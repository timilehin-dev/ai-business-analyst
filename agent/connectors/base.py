"""
Connector Framework - Base Types.

A connector ingests external data (files, Google Drive, Gmail, Sheets, ...)
into the analyst's document store — the knowledge graph that the agent can
query alongside the business database.

Every connector produces Documents. Documents are upserted into the
DocumentStore (analyst.db) keyed by (source, source_id), so re-syncing a
connector updates existing documents instead of duplicating them.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Document:
    """One unit of ingested knowledge (a file, a sheet, an email, ...)."""

    source: str  # connector id: 'csv', 'docx', 'pdf', 'txt', 'drive', 'sheets', 'gmail'
    source_id: str  # unique id within the source (file name, drive file id, gmail msg id)
    title: str
    content: str  # extracted text (markdown-ish for tables)
    metadata: Dict[str, Any] = field(default_factory=dict)
    updated_at: str = field(default_factory=_now_iso)


@dataclass
class ConnectorResult:
    """Outcome of a connector sync."""

    connector_id: str
    synced: int = 0  # documents created/updated
    skipped: int = 0  # documents unchanged
    errors: List[str] = field(default_factory=list)
    message: str = ""


class BaseConnector:
    """Interface every connector implements."""

    id: str = "base"
    name: str = "Base Connector"
    description: str = ""
    icon: str = "file"  # lucide icon name hint for the UI

    def is_configured(self) -> bool:
        """Whether the connector has what it needs to run (tokens, creds)."""
        return False

    def sync(self) -> ConnectorResult:
        """Pull new/changed data and return documents to store."""
        raise NotImplementedError

    def describe(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "icon": self.icon,
            "configured": self.is_configured(),
            "has_credentials": getattr(self, "has_credentials", lambda: False)(),
        }
