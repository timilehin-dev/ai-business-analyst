"""
Shared fixtures: a sample SQLite database and a fake model router
so graph tests run without any LLM or network access.
"""
import os
import sqlite3
import tempfile

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from agent.core.analyst import create_agent_graph
from agent.memory.database import Base, db_manager
from agent.connectors import storage as storage_mod
from agent.tools.database import DatabaseConnection
from agent.tools.newsroom import NewsroomTool
from agent.tools.sql_validator import SQLValidatorTool


@pytest.fixture(autouse=True)
def isolated_analyst_db(tmp_path, monkeypatch):
    """
    Give every test its own throwaway analyst database.

    document_store and db_manager are module-level singletons bound to the
    app's real data dir at import time. Without this fixture, tests mutate
    the live analyst.db AND become run-order dependent (rerunning the suite
    fails because documents persist between runs). Patch both singletons to
    a per-test temp SQLite file so tests are hermetic and repeatable.
    """
    engine = create_engine(f"sqlite:///{tmp_path}/analyst_test.db")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    monkeypatch.setattr(db_manager, "engine", engine)
    monkeypatch.setattr(db_manager, "SessionLocal", Session)
    store = storage_mod.document_store
    monkeypatch.setattr(store, "engine", engine)
    monkeypatch.setattr(store, "SessionLocal", Session)
    yield

PLAN_JSON = (
    '{"plan": "1. Query orders 2. Aggregate revenue by customer", '
    '"needs_external_search": false, "search_queries": [], '
    '"needs_code_execution": false, "required_tables": ["orders", "customers"], '
    '"metrics_needed": ["revenue"]}'
)


@pytest.fixture
def sample_db_path():
    """Create a temp SQLite DB with customers/products/orders and sample rows."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE customers (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT,
            created_at DATETIME
        );
        CREATE TABLE products (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            price REAL
        );
        CREATE TABLE orders (
            id INTEGER PRIMARY KEY,
            customer_id INTEGER REFERENCES customers(id),
            product_id INTEGER REFERENCES products(id),
            amount REAL,
            ordered_at DATETIME
        );
        INSERT INTO customers (name, email, created_at) VALUES
            ('Acme Corp', 'acme@example.com', '2026-01-15 10:00:00'),
            ('Globex', 'globex@example.com', '2026-02-01 09:30:00');
        INSERT INTO products (name, price) VALUES
            ('Widget', 9.99), ('Gadget', 19.99);
        INSERT INTO orders (customer_id, product_id, amount, ordered_at) VALUES
            (1, 1, 9.99, '2026-03-01 12:00:00'),
            (1, 2, 19.99, '2026-03-02 12:00:00'),
            (2, 1, 9.99, '2026-03-03 12:00:00');
        """
    )
    conn.commit()
    conn.close()
    yield path
    os.unlink(path)


@pytest.fixture
def db_conn(sample_db_path):
    return DatabaseConnection(f"sqlite:///{sample_db_path}")


class FakeModelRouter:
    """
    Queue-based fake router. Responses are popped per task_type in order;
    an exhausted queue returns an empty string (like a dead LLM endpoint).
    """

    def __init__(self, responses=None):
        self.responses = responses or {}
        self.calls = []

    async def complete(self, messages, task_type="reasoning", **kwargs):
        self.calls.append(task_type)
        queue = self.responses.get(task_type, [])
        return queue.pop(0) if queue else ""


def build_graph(router, database_url=None):
    """Build the compiled LangGraph with a fake router and optional DB."""
    newsroom = NewsroomTool(enabled=False)
    validator = SQLValidatorTool(strict_mode=True)
    db = DatabaseConnection(database_url) if database_url else None
    return create_agent_graph(router, newsroom, validator, db)


@pytest.fixture
def happy_router():
    """Router that plans, generates valid SQL, and reports."""
    return FakeModelRouter(
        {
            "reasoning": [
                PLAN_JSON,
                "## Report\nRevenue by customer is healthy. Acme leads.",
            ],
            "sql": [
                "SELECT c.name, SUM(o.amount) AS revenue "
                "FROM orders o JOIN customers c ON c.id = o.customer_id "
                "GROUP BY c.name"
            ],
        }
    )