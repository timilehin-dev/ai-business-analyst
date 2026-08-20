"""
Tests for the database layer: schema crawling and read-only execution.
"""
import sqlite3

import pytest

from agent.tools.database import DatabaseConnection


class TestSchemaCrawler:
    def test_crawl_schema_lists_tables(self, db_conn):
        schema = db_conn.crawl_schema()
        assert "TABLE customers" in schema
        assert "TABLE orders" in schema
        assert "TABLE products" in schema

    def test_crawl_schema_includes_columns_and_types(self, db_conn):
        schema = db_conn.crawl_schema()
        assert "id:INTEGER" in schema
        assert "name:VARCHAR" in schema or "name:TEXT" in schema

    def test_crawl_schema_includes_primary_key(self, db_conn):
        schema = db_conn.crawl_schema()
        assert "PK: id" in schema

    def test_crawl_schema_includes_foreign_keys(self, db_conn):
        schema = db_conn.crawl_schema()
        assert "customer_id->customers.id" in schema
        assert "product_id->products.id" in schema

    def test_schema_is_cached(self, db_conn):
        first = db_conn.crawl_schema()
        second = db_conn.crawl_schema()
        assert first is second  # cached object identity


class TestReadOnlyExecution:
    def test_select_returns_columns_and_rows(self, db_conn):
        result = db_conn.execute_readonly("SELECT name FROM customers ORDER BY id")
        assert result["columns"] == ["name"]
        assert result["rows"] == [["Acme Corp"], ["Globex"]]
        assert result["row_count"] == 2
        assert result["truncated"] is False

    def test_join_query(self, db_conn):
        result = db_conn.execute_readonly(
            "SELECT c.name, SUM(o.amount) AS revenue "
            "FROM orders o JOIN customers c ON c.id = o.customer_id "
            "GROUP BY c.name ORDER BY revenue DESC"
        )
        assert result["rows"][0][0] == "Acme Corp"
        assert result["rows"][0][1] == pytest.approx(29.98)
        assert result["rows"][1][0] == "Globex"
        assert result["rows"][1][1] == pytest.approx(9.99)

    def test_write_blocked_at_db_level(self, db_conn):
        """PRAGMA query_only must reject writes even if SQL passes the validator."""
        with pytest.raises(Exception):
            db_conn.execute_readonly(
                "INSERT INTO customers (name) VALUES ('Hacker')"
            )

    def test_row_limit_truncation(self, sample_db_path):
        conn = sqlite3.connect(sample_db_path)
        conn.execute(
            "CREATE TABLE big (id INTEGER PRIMARY KEY, v INTEGER)"
        )
        conn.executemany(
            "INSERT INTO big (v) VALUES (?)", [(i,) for i in range(600)]
        )
        conn.commit()
        conn.close()

        db = DatabaseConnection(f"sqlite:///{sample_db_path}")
        result = db.execute_readonly("SELECT * FROM big")
        assert result["row_count"] == DatabaseConnection.MAX_ROWS
        assert result["truncated"] is True

    def test_datetime_and_bytes_serialized(self, sample_db_path):
        conn = sqlite3.connect(sample_db_path)
        conn.execute(
            "CREATE TABLE misc (ts DATETIME, blob BLOB)"
        )
        conn.execute(
            "INSERT INTO misc VALUES (?, ?)", ("2026-08-20 12:00:00", b"\x00\x01")
        )
        conn.commit()
        conn.close()

        db = DatabaseConnection(f"sqlite:///{sample_db_path}")
        result = db.execute_readonly("SELECT * FROM misc")
        assert isinstance(result["rows"][0][0], str)
        assert isinstance(result["rows"][0][1], str)

    def test_bad_sql_raises(self, db_conn):
        with pytest.raises(Exception):
            db_conn.execute_readonly("SELECT * FROM nonexistent_table")