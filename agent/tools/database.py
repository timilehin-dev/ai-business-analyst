"""
Database Connection Layer.
Provides schema crawling and read-only query execution
for the analyst agent. Supports SQLite, PostgreSQL, and MySQL.

Security model (defense in depth):
1. The SQL validator blocks non-SELECT statements before execution.
2. The connection is forced read-only at the database level
   (PRAGMA query_only / SET TRANSACTION READ ONLY), so even a
   crafted statement cannot modify data.
"""
import datetime
import decimal
from typing import Any, Dict, List, Optional

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine


class DatabaseConnection:
    """Wraps a SQLAlchemy engine with schema introspection and read-only execution."""

    MAX_ROWS = 500
    STATEMENT_TIMEOUT_MS = 15000

    def __init__(self, database_url: str):
        self.database_url = database_url
        connect_args = {}
        if database_url.startswith("sqlite"):
            connect_args["check_same_thread"] = False
        self.engine: Engine = create_engine(database_url, connect_args=connect_args)
        self._schema_cache: Optional[str] = None

    # ==================== SCHEMA CRAWLING ====================

    def crawl_schema(self, max_tables: int = 50) -> str:
        """
        Introspect the database and return a compact schema description
        suitable for the SQL generator prompt.
        """
        if self._schema_cache is not None:
            return self._schema_cache

        try:
            inspector = inspect(self.engine)
            lines = []

            for table in inspector.get_table_names()[:max_tables]:
                lines.append(self._describe_table(inspector, table))

            for view in inspector.get_view_names()[:max_tables]:
                lines.append(f"VIEW {view}")

            self._schema_cache = "\n".join(lines) if lines else "No tables found in database."
        except Exception as e:
            self._schema_cache = f"Schema introspection failed: {str(e)}"

        return self._schema_cache

    def _describe_table(self, inspector, table: str) -> str:
        """Describe one table: columns, primary key, and foreign keys."""
        columns = inspector.get_columns(table)
        col_parts = [f"{col['name']}:{col['type']}" for col in columns]

        pk = inspector.get_pk_constraint(table)
        pk_cols = pk.get("constrained_columns") or []

        fk_parts = []
        for fk in inspector.get_foreign_keys(table):
            fk_parts.append(
                f"{','.join(fk['constrained_columns'])}->"
                f"{fk['referred_table']}.{','.join(fk['referred_columns'])}"
            )

        parts = [f"TABLE {table} ({', '.join(col_parts)})"]
        if pk_cols:
            parts.append(f"PK: {','.join(pk_cols)}")
        if fk_parts:
            parts.append(f"FK: {'; '.join(fk_parts)}")
        return " ".join(parts)

    # ==================== READ-ONLY EXECUTION ====================

    def execute_readonly(self, sql: str) -> Dict[str, Any]:
        """
        Execute a SELECT query and return serializable results.

        Returns:
            Dict with 'columns', 'rows', 'row_count', 'truncated', 'query'.

        Raises:
            Exception on any failure so the agent can self-correct.
        """
        with self.engine.connect() as conn:
            self._apply_read_only(conn)
            result = conn.execute(text(sql))
            columns = list(result.keys())
            rows = [list(row) for row in result.fetchmany(self.MAX_ROWS + 1)]
            truncated = len(rows) > self.MAX_ROWS
            rows = rows[: self.MAX_ROWS]

        return {
            "columns": columns,
            "rows": [self._serialize_row(r) for r in rows],
            "row_count": len(rows),
            "truncated": truncated,
            "query": sql,
        }

    def _apply_read_only(self, conn) -> None:
        """Force the connection read-only at the database level."""
        dialect = self.engine.dialect.name
        if dialect == "sqlite":
            conn.execute(text("PRAGMA query_only = ON"))
        elif dialect == "postgresql":
            conn.execute(text("SET default_transaction_read_only = on"))
            conn.execute(text(f"SET statement_timeout = {self.STATEMENT_TIMEOUT_MS}"))
        elif dialect == "mysql":
            conn.execute(text("SET SESSION TRANSACTION READ ONLY"))
            conn.execute(text(f"SET SESSION MAX_EXECUTION_TIME = {self.STATEMENT_TIMEOUT_MS}"))

    @staticmethod
    def _serialize_row(row: List[Any]) -> List[Any]:
        """Convert non-JSON-safe values (datetime, Decimal, bytes) to strings."""
        out = []
        for value in row:
            if value is None or isinstance(value, (int, float, bool, str)):
                out.append(value)
            elif isinstance(value, (datetime.datetime, datetime.date, datetime.time, decimal.Decimal)):
                out.append(str(value))
            elif isinstance(value, (bytes, bytearray)):
                out.append(value.decode("utf-8", errors="replace"))
            else:
                out.append(str(value))
        return out
