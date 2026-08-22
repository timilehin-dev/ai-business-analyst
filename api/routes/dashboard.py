"""
Dashboard API — live business metrics from the organization's database.

Every number is queried directly from the user's data. The dashboard
refreshes periodically so leadership always sees current state.
"""
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter
from sqlalchemy import create_engine, text

from agent.memory.database import db_manager

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def _get_engine():
    url = db_manager.get_config("database_url", is_sensitive=False)
    if not url:
        return None
    try:
        # SQLite doesn't support connect_timeout
        if url.startswith("sqlite"):
            return create_engine(url)
        return create_engine(url, connect_args={"connect_timeout": 5})
    except Exception:
        return None


def _q(engine, sql, default=None):
    """Scalar query with fallback."""
    try:
        with engine.connect() as conn:
            row = conn.execute(text(sql)).fetchone()
            return row[0] if row else default
    except Exception:
        return default


def _qall(engine, sql):
    """Multi-row query with fallback."""
    try:
        with engine.connect() as conn:
            result = conn.execute(text(sql))
            return [dict(zip(result.keys(), r)) for r in result.fetchall()]
    except Exception:
        return []


@router.get("")
async def get_dashboard_data() -> Dict[str, Any]:
    """
    Return live business metrics for the dashboard.
    Adapts to whatever tables/columns exist in the database.
    """
    engine = _get_engine()
    if engine is None:
        return {
            "status": "no_database",
            "metrics": {},
            "trends": [],
            "recent_orders": [],
            "categories": [],
            "top_customers": [],
            "schema": {},
            "message": "No database configured. Run the setup wizard to connect your data.",
        }

    # ---- Schema info ----
    try:
        from sqlalchemy import inspect as sa_inspect
        inspector = sa_inspect(engine)
        tables = inspector.get_table_names()
    except Exception:
        tables = []

    metrics: Dict[str, Any] = {}

    # Revenue (try 'completed' status first, then all orders)
    rev = _q(engine,
        "SELECT SUM(quantity * unit_price) FROM orders WHERE LOWER(status) = 'completed'")
    if rev is None:
        rev = _q(engine, "SELECT SUM(quantity * unit_price) FROM orders")
    metrics["revenue"] = float(rev) if rev else 0

    # Previous period revenue (30 days ago)
    prev_rev = _q(engine, """
        SELECT SUM(quantity * unit_price) FROM orders
        WHERE LOWER(status) = 'completed' AND ordered_at < datetime('now', '-30 days')
    """)
    if prev_rev is None:
        prev_rev = _q(engine, """
            SELECT SUM(quantity * unit_price) FROM orders
            WHERE ordered_at < datetime('now', '-30 days')
        """)
    metrics["revenue_previous"] = float(prev_rev) if prev_rev else 0

    # Counts
    metrics["total_orders"] = _q(engine, "SELECT COUNT(*) FROM orders") or 0
    metrics["total_customers"] = _q(engine, "SELECT COUNT(*) FROM customers") or 0
    metrics["total_products"] = _q(engine, "SELECT COUNT(*) FROM products") or 0
    metrics["active_customers"] = _q(engine, """
        SELECT COUNT(DISTINCT customer_id) FROM orders
        WHERE ordered_at >= datetime('now', '-30 days')
    """) or 0

    # Revenue by category
    categories = _qall(engine, """
        SELECT p.category, SUM(o.quantity * o.unit_price) as revenue,
               COUNT(*) as order_count
        FROM orders o
        JOIN products p ON o.product_id = p.id
        WHERE LOWER(o.status) = 'completed'
        GROUP BY p.category ORDER BY revenue DESC
    """)
    if not categories:
        categories = _qall(engine, """
            SELECT p.category, SUM(o.quantity * o.unit_price) as revenue,
                   COUNT(*) as order_count
            FROM orders o
            JOIN products p ON o.product_id = p.id
            GROUP BY p.category ORDER BY revenue DESC
        """)

    # Daily trend (last 30 days)
    daily = _qall(engine, """
        SELECT date(ordered_at) as day, COUNT(*) as orders,
               SUM(quantity * unit_price) as revenue
        FROM orders
        WHERE ordered_at >= datetime('now', '-30 days')
        GROUP BY date(ordered_at) ORDER BY day
    """)

    # Recent orders
    recent = _qall(engine, """
        SELECT o.id, o.ordered_at, o.status, o.quantity, o.unit_price,
               (o.quantity * o.unit_price) as total,
               c.name as customer_name, p.name as product_name
        FROM orders o
        LEFT JOIN customers c ON o.customer_id = c.id
        LEFT JOIN products p ON o.product_id = p.id
        ORDER BY o.ordered_at DESC LIMIT 10
    """)

    # Top customers
    top_cust = _qall(engine, """
        SELECT c.name, SUM(o.quantity * o.unit_price) as revenue,
               COUNT(*) as orders
        FROM orders o
        JOIN customers c ON o.customer_id = c.id
        WHERE LOWER(o.status) = 'completed'
        GROUP BY c.name ORDER BY revenue DESC LIMIT 5
    """)
    if not top_cust:
        top_cust = _qall(engine, """
            SELECT c.name, SUM(o.quantity * o.unit_price) as revenue,
                   COUNT(*) as orders
            FROM orders o
            JOIN customers c ON o.customer_id = c.id
            GROUP BY c.name ORDER BY revenue DESC LIMIT 5
        """)

    # Convert Decimal/float for JSON serialization
    def _clean(obj):
        if isinstance(obj, dict):
            return {k: _clean(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [_clean(i) for i in obj]
        if hasattr(obj, "__float__"):
            return float(obj)
        return obj

    return _clean({
        "status": "ok",
        "metrics": metrics,
        "categories": categories,
        "trends": daily,
        "recent_orders": recent,
        "top_customers": top_cust,
        "schema": {"tables": tables, "table_count": len(tables)},
    })
