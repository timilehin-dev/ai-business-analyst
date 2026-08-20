"""
Anomaly Detection Engine.

Schema-agnostic: crawls the database, finds tables with a date column and
numeric columns, and compares the current window (e.g. last 7 days) against
the previous window of equal length. Large swings are flagged as findings.

All numbers are computed by the database — the engine never invents data.
"""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import re
from typing import Any, Dict, List, Optional

from sqlalchemy import inspect, text

from agent.tools.database import DatabaseConnection

# Column type names that indicate a date/time column (SQLAlchemy dialect-agnostic).
# Compared against the UPPERCASED type string, so hints are uppercase too.
_DATE_TYPE_HINTS = ("DATE", "TIME", "TIMESTAMP")
# Column names that strongly suggest a date even with a generic type.
# Word-boundary matched so "at" does not match "category".
_DATE_NAME_RE = re.compile(r"\b(date|time|created|updated|ordered|at)\b", re.I)
_NUMERIC_TYPE_HINTS = ("INT", "FLOAT", "REAL", "NUMERIC", "DECIMAL", "DOUBLE", "MONEY")

# The app's own tables — never monitored as business data
_INTERNAL_TABLES = {"config_store", "briefings", "documents", "connector_state"}

# Surrogate/foreign keys: SUM(id) is meaningless; row count already covers volume
_SKIP_METRIC_RE = re.compile(r"(^|_)id$", re.I)

_DATE_COL_TYPES = {
    "DATE", "DATETIME", "TIMESTAMP", "TIMESTAMPTZ", "TIMESTAMP WITH TIME ZONE",
    "TIMESTAMP WITHOUT TIME ZONE", "SMALLDATETIME",
}


@dataclass
class Finding:
    """One detected anomaly: a metric that swung between windows."""

    table: str
    metric: str  # column name, or 'row_count'
    current: float
    previous: float
    change_pct: float  # None for 'new' activity
    direction: str  # 'up' | 'down' | 'new'
    severity: str  # 'critical' | 'warning'
    window: str  # human description of the comparison windows

    def to_dict(self) -> Dict[str, Any]:
        return {
            "table": self.table,
            "metric": self.metric,
            "current": self.current,
            "previous": self.previous,
            "change_pct": self.change_pct,
            "direction": self.direction,
            "severity": self.severity,
            "window": self.window,
        }


class AnomalyDetector:
    """Compare recent vs previous windows for every measurable table."""

    def __init__(
        self,
        db_conn: DatabaseConnection,
        threshold_pct: float = 20.0,
        critical_pct: float = 50.0,
        min_value: float = 1.0,
        max_tables: int = 20,
    ):
        self.db = db_conn
        self.threshold_pct = threshold_pct
        self.critical_pct = critical_pct
        self.min_value = min_value
        self.max_tables = max_tables

    # ==================== SCHEMA DISCOVERY ====================

    def _candidate_metrics(self) -> List[Dict[str, str]]:
        """Find (table, date_col, metric_col) triples worth monitoring."""
        inspector = inspect(self.db.engine)
        candidates = []
        for table in inspector.get_table_names()[: self.max_tables]:
            if table in _INTERNAL_TABLES:
                continue
            columns = inspector.get_columns(table)
            date_cols = [c["name"] for c in columns if self._is_date_col(c)]
            numeric_cols = [
                c["name"]
                for c in columns
                if self._is_numeric_col(c) and not _SKIP_METRIC_RE.search(c["name"])
            ]
            if not date_cols:
                continue
            date_col = date_cols[0]
            for metric in numeric_cols:
                candidates.append({"table": table, "date_col": date_col, "metric": metric})
            # Row count is always a meaningful metric
            candidates.append({"table": table, "date_col": date_col, "metric": "__row_count__"})
        return candidates

    @staticmethod
    def _is_date_col(col: Dict[str, Any]) -> bool:
        type_name = str(col["type"]).upper()
        if any(h in type_name for h in _DATE_TYPE_HINTS):
            return True
        return bool(_DATE_NAME_RE.search(col["name"]))

    @staticmethod
    def _is_numeric_col(col: Dict[str, Any]) -> bool:
        type_name = str(col["type"]).upper()
        return any(h in type_name for h in _NUMERIC_TYPE_HINTS)

    # ==================== WINDOW COMPARISON ====================

    def scan(self, days: int = 7, now: Optional[datetime] = None) -> List[Finding]:
        """
        Scan the database for anomalies.

        Args:
            days: window length in days (current vs previous)
            now: reference time (defaults to UTC now; injectable for tests)

        Returns:
            List of Findings sorted by severity then |change|.
        """
        now = now or datetime.now(timezone.utc)
        start_current = now - timedelta(days=days)
        start_previous = start_current - timedelta(days=days)

        findings: List[Finding] = []
        for cand in self._candidate_metrics():
            try:
                current = self._window_value(cand, start_current, now)
                previous = self._window_value(cand, start_previous, start_current)
            except Exception:
                continue  # a broken table must not kill the scan

            finding = self._compare(cand, current, previous, days)
            if finding:
                findings.append(finding)

        findings.sort(key=lambda f: (f.severity != "critical", -abs(f.change_pct or 0)))
        return findings

    def _window_value(self, cand: Dict[str, str], start, end) -> float:
        """Aggregate one metric over [start, end) — computed by the DB."""
        table = cand["table"]
        date_col = cand["date_col"]
        if cand["metric"] == "__row_count__":
            expr = "COUNT(*)"
        else:
            expr = f"COALESCE(SUM({cand['metric']}), 0)"
        sql = (
            f"SELECT {expr} FROM {table} "
            f"WHERE {date_col} >= :start AND {date_col} < :end"
        )
        with self.db.engine.connect() as conn:
            row = conn.execute(
                text(sql), {"start": start, "end": end}
            ).fetchone()
        return float(row[0] or 0)

    def _compare(self, cand, current: float, previous: float, days: int) -> Optional[Finding]:
        """Decide whether a swing is worth reporting."""
        if max(current, previous) < self.min_value:
            return None  # too small to be meaningful

        if previous == 0:
            if current > 0:
                return Finding(
                    table=cand["table"],
                    metric=cand["metric"],
                    current=current,
                    previous=0.0,
                    change_pct=None,
                    direction="new",
                    severity="warning",
                    window=f"last {days} days vs prior {days} days (no prior activity)",
                )
            return None

        change_pct = (current - previous) / previous * 100.0
        if abs(change_pct) < self.threshold_pct:
            return None

        severity = "critical" if abs(change_pct) >= self.critical_pct else "warning"
        return Finding(
            table=cand["table"],
            metric=cand["metric"],
            current=current,
            previous=previous,
            change_pct=round(change_pct, 2),
            direction="up" if change_pct > 0 else "down",
            severity=severity,
            window=f"last {days} days vs prior {days} days",
        )