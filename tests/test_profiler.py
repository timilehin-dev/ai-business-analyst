"""
Tests for the schema profiler and the schema-agnostic dashboard payload.
"""
import pytest

from agent.tools.profiler import (
    INTERNAL_TABLES,
    TableProfile,
    days_ago,
    pick_fact_table,
    profile_database,
)


class TestDaysAgo:
    def test_returns_naive_datetime(self):
        dt = days_ago(30)
        assert dt.tzinfo is None  # naive, so it compares cleanly against naive columns


class TestProfileDatabase:
    def test_profiles_sample_schema(self, db_conn):
        profiles = profile_database(db_conn.engine)
        names = {p.name for p in profiles}
        assert {"orders", "customers", "products"} <= names

    def test_skips_internal_tables(self, db_conn):
        internal = INTERNAL_TABLES
        profiles = profile_database(db_conn.engine)
        assert all(p.name not in internal for p in profiles)

    def test_column_classification(self, db_conn):
        profiles = {p.name: p for p in profile_database(db_conn.engine)}
        orders = profiles["orders"]
        assert "ordered_at" in orders.date_columns
        assert "amount" in orders.measure_columns
        # surrogate key "id" must not count as a measure
        assert "id" not in orders.measure_columns
        assert "customer_id" not in orders.measure_columns


class TestPrimaryMeasurePriority:
    def test_money_beats_volume(self):
        from agent.tools.profiler import ColumnProfile

        profile = TableProfile(
            name="orders",
            columns=[
                ColumnProfile(name="quantity", type_name="INTEGER", is_numeric=True),
                ColumnProfile(name="unit_price", type_name="REAL", is_numeric=True),
            ],
        )
        # 'unit_price' (money tier) beats 'quantity' (volume tier) even though
        # it comes second in column order.
        assert profile.primary_measure == "unit_price"

    def test_fixture_orders_measure(self, db_conn):
        profiles = {p.name: p for p in profile_database(db_conn.engine)}
        assert profiles["orders"].primary_measure == "amount"


class TestPickFactTable:
    def test_picks_orders(self, db_conn):
        profiles = profile_database(db_conn.engine)
        fact = pick_fact_table(profiles)
        assert fact is not None
        assert fact.name == "orders"
        assert fact.primary_date == "ordered_at"

    def test_returns_none_when_no_dates(self):
        no_date = TableProfile(name="t1", columns=[])
        assert pick_fact_table([no_date]) is None