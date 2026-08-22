"""
Schema profiler.

Discovers what a database actually contains so features can adapt to any
schema instead of assuming demo tables named orders/products/customers.

The profiler answers three questions per table:
  - is there a date column to trend on?
  - which numeric columns are real measures (not surrogate keys)?
  - which text columns are low-cardinality enough to group by?

It also centralises the one genuinely dialect-specific piece of SQL —
"timestamp N days ago" — so callers stay portable across SQLite,
PostgreSQL, and MySQL.
"""
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

# Tables owned by the analyst itself — never business data.
INTERNAL_TABLES = frozenset({
    "config_store", "documents", "connector_state", "briefings",
    "chat_history", "memory_semantic", "memory_episodic",
    "memory_procedural", "audit_log",
})

_DATE_TYPE_HINTS = ("DATE", "TIME", "TIMESTAMP")
_DATE_NAME_RE = re.compile(r"\b(date|time|created|updated|ordered|at|on)\b", re.I)
_NUMERIC_TYPE_HINTS = ("INT", "FLOAT", "REAL", "NUMERIC", "DECIMAL", "DOUBLE", "MONEY")
_TEXT_TYPE_HINTS = ("CHAR", "TEXT", "STRING", "ENUM", "UUID")

# Surrogate/foreign keys: summing them is meaningless.
_KEY_COL_RE = re.compile(r"(^|_)(id|key|code|no|num|number)$", re.I)

# Headline-metric preference, most meaningful first. Money beats volume:
# "total revenue" is a better summary than "total units", and a column
# matching an earlier tier wins regardless of column order in the table.
_MEASURE_PRIORITY = (
    re.compile(r"(revenue|sales|amount|total|gross|net|turnover)", re.I),
    re.compile(r"(price|cost|value|balance|spend|fee|charge|payment)", re.I),
    re.compile(r"(qty|quantity|units|count|volume)", re.I),
)


@dataclass
class ColumnProfile:
    name: str
    type_name: str
    is_date: bool = False
    is_numeric: bool = False
    is_text: bool = False


@dataclass
class TableProfile:
    """What one table offers for automatic analysis."""

    name: str
    columns: List[ColumnProfile] = field(default_factory=list)
    row_count: int = 0

    @property
    def date_columns(self) -> List[str]:
        return [c.name for c in self.columns if c.is_date]

    @property
    def measure_columns(self) -> List[str]:
        """Numeric columns that are measures rather than identifiers."""
        return [
            c.name for c in self.columns if c.is_numeric and not _KEY_COL_RE.search(c.name)
        ]

    @property
    def dimension_columns(self) -> List[str]:
        """Text columns usable as group-by dimensions."""
        return [
            c.name for c in self.columns if c.is_text and not _KEY_COL_RE.search(c.name)
        ]

    @property
    def primary_date(self) -> Optional[str]:
        cols = self.date_columns
        return cols[0] if cols else None

    @property
    def primary_measure(self) -> Optional[str]:
        """Best headline metric, by priority tier then column order."""
        measures = self.measure_columns
        if not measures:
            return None
        for pattern in _MEASURE_PRIORITY:
            for name in measures:
                if pattern.search(name):
                    return name
        return measures[0]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "row_count": self.row_count,
            "date_columns": self.date_columns,
            "measure_columns": self.measure_columns,
            "dimension_columns": self.dimension_columns,
            "primary_date": self.primary_date,
            "primary_measure": self.primary_measure,
        }


def quote_identifier(engine: Engine, identifier: str) -> str:
    """Quote a table/column name for the engine's dialect."""
    return engine.dialect.identifier_preparer.quote(identifier)


def days_ago(days: int) -> datetime:
    """
    A timezone-naive UTC timestamp N days back.

    Returned as a bound parameter value rather than dialect SQL
    (datetime('now', ...) vs NOW() - INTERVAL) so the same query text works
    on SQLite, PostgreSQL, and MySQL. Naive because most business columns
    are stored without timezone and comparing naive to aware raises.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days)


def _is_date(col: Dict[str, Any]) -> bool:
    type_name = str(col["type"]).upper()
    if any(hint in type_name for hint in _DATE_TYPE_HINTS):
        return True
    # A generic type with a date-ish name still trends correctly.
    return bool(_DATE_NAME_RE.search(col["name"]))


def _is_numeric(col: Dict[str, Any]) -> bool:
    type_name = str(col["type"]).upper()
    if "BOOL" in type_name:
        return False
    return any(hint in type_name for hint in _NUMERIC_TYPE_HINTS)


def _is_text(col: Dict[str, Any]) -> bool:
    type_name = str(col["type"]).upper()
    return any(hint in type_name for hint in _TEXT_TYPE_HINTS)


def profile_database(
    engine: Engine, max_tables: int = 50, include_row_counts: bool = True
) -> List[TableProfile]:
    """
    Inspect every business table and classify its columns.

    Individual table failures are skipped rather than aborting the profile —
    a single permission error must not blank the whole dashboard.
    """
    try:
        inspector = inspect(engine)
        table_names = inspector.get_table_names()
    except Exception:
        return []

    profiles: List[TableProfile] = []
    for name in table_names[:max_tables]:
        if name in INTERNAL_TABLES:
            continue
        try:
            columns = inspector.get_columns(name)
        except Exception:
            continue

        profile = TableProfile(
            name=name,
            columns=[
                ColumnProfile(
                    name=col["name"],
                    type_name=str(col["type"]),
                    is_date=_is_date(col),
                    is_numeric=_is_numeric(col),
                    is_text=_is_text(col),
                )
                for col in columns
            ],
        )

        if include_row_counts:
            try:
                with engine.connect() as conn:
                    quoted = quote_identifier(engine, name)
                    profile.row_count = int(
                        conn.execute(text(f"SELECT COUNT(*) FROM {quoted}")).scalar() or 0
                    )
            except Exception:
                profile.row_count = 0

        profiles.append(profile)

    return profiles


def pick_fact_table(profiles: List[TableProfile]) -> Optional[TableProfile]:
    """
    Choose the table that best represents business activity.

    Prefers a dated table with a real measure and the most rows — that is
    almost always the transaction/event table worth trending.
    """
    candidates = [p for p in profiles if p.primary_date and p.measure_columns]
    if not candidates:
        candidates = [p for p in profiles if p.primary_date]
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.row_count)
