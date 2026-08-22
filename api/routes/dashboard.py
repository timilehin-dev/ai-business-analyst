"""
Dashboard API — live business metrics from the organization's database.

Schema-agnostic by design: the database is profiled at request time and the
dashboard is built from whatever fact table, date column, measure, and
dimensions actually exist. Nothing assumes the demo orders/products/customers
schema, and all date math is passed as bound parameters so the same SQL runs
on SQLite, PostgreSQL, and MySQL.

Every number is queried directly from the user's data.
"""
from typing import Any, Dict, List, Optional

from fastapi import APIRouter
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from agent.memory.database import db_manager
from agent.tools.profiler import (
    TableProfile,
    days_ago,
    pick_fact_table,
    profile_database,
    quote_identifier,
)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

TREND_DAYS = 30
RECENT_LIMIT = 10
TOP_DIMENSION_LIMIT = 5


def _get_engine() -> Optional[Engine]:
    url = db_manager.get_config("database_url", is_sensitive=False)
    if not url:
        return None
    try:
        if url.startswith("sqlite"):
            return create_engine(url)
        return create_engine(url, connect_args={"connect_timeout": 5})
    except Exception:
        return None


def _scalar(engine: Engine, sql: str, params: Optional[Dict[str, Any]] = None, default=None):
    """Scalar query that degrades to a default instead of failing the page."""
    try:
        with engine.connect() as conn:
            row = conn.execute(text(sql), params or {}).fetchone()
            return row[0] if row and row[0] is not None else default
    except Exception:
        return default


def _rows(engine: Engine, sql: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """Multi-row query that degrades to an empty list."""
    try:
        with engine.connect() as conn:
            result = conn.execute(text(sql), params or {})
            keys = list(result.keys())
            return [dict(zip(keys, row)) for row in result.fetchall()]
    except Exception:
        return []


def _empty_payload(message: str, status: str) -> Dict[str, Any]:
    return {
        "status": status,
        "message": message,
        "metrics": {},
        "trends": [],
        "categories": [],
        "recent_activity": [],
        "top_dimensions": [],
        "schema": {},
        "profile": {},
    }


def _date_expression(engine: Engine, column: str) -> str:
    """
    Dialect-specific truncation of a timestamp to a day, for grouping.

    This is the only place a dialect branch is needed; the comparison
    values themselves travel as bound parameters.
    """
    dialect = engine.dialect.name
    if dialect == "sqlite":
        return f"date({column})"
    if dialect == "mysql":
        return f"DATE({column})"
    return f"CAST({column} AS DATE)"  # postgresql and standard SQL


def _build_metrics(
    engine: Engine, fact: TableProfile, table: str, date_col: Optional[str], measure: Optional[str]
) -> Dict[str, Any]:
    """Headline numbers: totals plus a 30-day vs prior-30-day comparison."""
    metrics: Dict[str, Any] = {
        "fact_table": fact.name,
        "measure": measure,
        "date_column": date_col,
        "total_records": fact.row_count,
    }

    if measure:
        quoted_measure = quote_identifier(engine, measure)
        metrics["measure_total"] = _scalar(
            engine, f"SELECT SUM({quoted_measure}) FROM {table}", default=0
        )

    if not date_col:
        return metrics

    quoted_date = quote_identifier(engine, date_col)
    current_start = days_ago(TREND_DAYS)
    previous_start = days_ago(TREND_DAYS * 2)

    metrics["records_30d"] = _scalar(
        engine,
        f"SELECT COUNT(*) FROM {table} WHERE {quoted_date} >= :start",
        {"start": current_start},
        default=0,
    )
    metrics["records_prev_30d"] = _scalar(
        engine,
        f"SELECT COUNT(*) FROM {table} WHERE {quoted_date} >= :start AND {quoted_date} < :end",
        {"start": previous_start, "end": current_start},
        default=0,
    )

    if measure:
        quoted_measure = quote_identifier(engine, measure)
        metrics["measure_30d"] = _scalar(
            engine,
            f"SELECT SUM({quoted_measure}) FROM {table} WHERE {quoted_date} >= :start",
            {"start": current_start},
            default=0,
        )
        metrics["measure_prev_30d"] = _scalar(
            engine,
            f"SELECT SUM({quoted_measure}) FROM {table} "
            f"WHERE {quoted_date} >= :start AND {quoted_date} < :end",
            {"start": previous_start, "end": current_start},
            default=0,
        )

    return metrics


def _build_trend(
    engine: Engine, table: str, date_col: str, measure: Optional[str]
) -> List[Dict[str, Any]]:
    """Daily counts (and measure sums) over the trend window."""
    quoted_date = quote_identifier(engine, date_col)
    day_expr = _date_expression(engine, quoted_date)
    measure_select = ""
    if measure:
        quoted_measure = quote_identifier(engine, measure)
        measure_select = f", SUM({quoted_measure}) AS value"

    return _rows(
        engine,
        f"SELECT {day_expr} AS day, COUNT(*) AS records{measure_select} "
        f"FROM {table} WHERE {quoted_date} >= :start "
        f"GROUP BY {day_expr} ORDER BY {day_expr}",
        {"start": days_ago(TREND_DAYS)},
    )


def _build_dimension_breakdown(
    engine: Engine, table: str, dimension: str, measure: Optional[str]
) -> List[Dict[str, Any]]:
    """Group the fact table by its most useful text dimension."""
    quoted_dim = quote_identifier(engine, dimension)
    if measure:
        quoted_measure = quote_identifier(engine, measure)
        value_select = f"SUM({quoted_measure}) AS value"
        order_by = "value DESC"
    else:
        value_select = "COUNT(*) AS value"
        order_by = "value DESC"

    rows = _rows(
        engine,
        f"SELECT {quoted_dim} AS label, {value_select}, COUNT(*) AS records "
        f"FROM {table} WHERE {quoted_dim} IS NOT NULL "
        f"GROUP BY {quoted_dim} ORDER BY {order_by}",
    )
    return rows[:12]


def _build_recent(
    engine: Engine, table: str, date_col: str, profile: TableProfile
) -> List[Dict[str, Any]]:
    """Most recent rows, limited to a readable set of columns."""
    quoted_date = quote_identifier(engine, date_col)
    display_columns = [date_col]
    display_columns += profile.dimension_columns[:3]
    display_columns += profile.measure_columns[:2]

    seen, ordered = set(), []
    for col in display_columns:
        if col not in seen:
            seen.add(col)
            ordered.append(col)

    select_list = ", ".join(quote_identifier(engine, c) for c in ordered)
    return _rows(
        engine,
        f"SELECT {select_list} FROM {table} "
        f"ORDER BY {quoted_date} DESC LIMIT {RECENT_LIMIT}",
    )


def _clean(obj):
    """Make DB-native values JSON-safe while preserving ints."""
    if isinstance(obj, dict):
        return {k: _clean(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_clean(i) for i in obj]
    if isinstance(obj, (int, float, str, bool)) or obj is None:
        return obj
    if hasattr(obj, "isoformat"):
        return obj.isoformat()
    if hasattr(obj, "__float__"):
        return float(obj)  # Decimal and similar
    return str(obj)


@router.get("")
async def get_dashboard_data() -> Dict[str, Any]:
    """
    Return live business metrics for the dashboard.
    Adapts to whatever tables and columns exist in the connected database.
    """
    engine = _get_engine()
    if engine is None:
        return _empty_payload(
            "No database configured. Run the setup wizard to connect your data.",
            "no_database",
        )

    profiles = profile_database(engine)
    if not profiles:
        return _empty_payload(
            "Connected, but no business tables were found in this database.",
            "no_tables",
        )

    fact = pick_fact_table(profiles)
    if fact is None:
        # Nothing to trend, but the schema itself is still worth showing.
        return {
            **_empty_payload(
                "No table with a usable date column was found, so trends are unavailable.",
                "no_fact_table",
            ),
            "schema": {
                "tables": [p.name for p in profiles],
                "table_count": len(profiles),
            },
            "profile": {"tables": [p.to_dict() for p in profiles]},
            "metrics": {
                "total_records": sum(p.row_count for p in profiles),
                "table_count": len(profiles),
            },
        }

    table = quote_identifier(engine, fact.name)
    date_col = fact.primary_date
    measure = fact.primary_measure

    metrics = _build_metrics(engine, fact, table, date_col, measure)
    metrics["table_count"] = len(profiles)

    trends = _build_trend(engine, table, date_col, measure) if date_col else []

    dimension = fact.dimension_columns[0] if fact.dimension_columns else None
    categories = (
        _build_dimension_breakdown(engine, table, dimension, measure) if dimension else []
    )

    top_dimensions: List[Dict[str, Any]] = []
    for extra_dim in fact.dimension_columns[1 : TOP_DIMENSION_LIMIT + 1]:
        rows = _build_dimension_breakdown(engine, table, extra_dim, measure)
        if rows:
            top_dimensions.append({"dimension": extra_dim, "values": rows[:5]})

    recent = _build_recent(engine, table, date_col, fact) if date_col else []

    return _clean({
        "status": "ok",
        "message": None,
        "metrics": metrics,
        "categories": categories,
        "category_dimension": dimension,
        "trends": trends,
        "recent_activity": recent,
        "top_dimensions": top_dimensions,
        "schema": {
            "tables": [p.name for p in profiles],
            "table_count": len(profiles),
        },
        "profile": {"tables": [p.to_dict() for p in profiles]},
    })
