"""
Sample Data Seeder.

Creates a small demo business database (customers, products, orders,
order_items) so users can test the analyst immediately without their own
data. Idempotent: if the tables already exist with rows, it does nothing.

Works on SQLite, PostgreSQL, and MySQL.
"""
import random
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import create_engine, inspect, text

SAMPLE_TABLES = {"customers", "products", "orders", "order_items"}


def _engine(database_url: str):
    connect_args = {}
    if database_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
    return create_engine(database_url, connect_args=connect_args)


def seed_sample_data(database_url: str, force: bool = False) -> dict:
    """
    Seed demo tables into the given database.

    Returns {'seeded': bool, 'tables': [...], 'message': str}.
    """
    engine = _engine(database_url)
    inspector = inspect(engine)
    existing = set(inspector.get_table_names())

    if not force and SAMPLE_TABLES.issubset(existing):
        return {
            "seeded": False,
            "tables": sorted(SAMPLE_TABLES),
            "message": "Sample data already present.",
        }

    random.seed(42)  # deterministic demo data

    with engine.begin() as conn:
        # Drop only the sample tables so re-seeding is clean.
        for table in SAMPLE_TABLES:
            if table in existing:
                conn.execute(text(f"DROP TABLE IF EXISTS {table}"))

        conn.execute(text(
            """
            CREATE TABLE customers (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT,
                country TEXT,
                segment TEXT,
                created_at TIMESTAMP
            )
            """
        ))
        conn.execute(text(
            """
            CREATE TABLE products (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                category TEXT,
                price REAL,
                cost REAL
            )
            """
        ))
        conn.execute(text(
            """
            CREATE TABLE orders (
                id INTEGER PRIMARY KEY,
                customer_id INTEGER,
                product_id INTEGER,
                quantity INTEGER,
                unit_price REAL,
                status TEXT,
                ordered_at TIMESTAMP
            )
            """
        ))
        conn.execute(text(
            """
            CREATE TABLE order_items (
                id INTEGER PRIMARY KEY,
                order_id INTEGER,
                product_id INTEGER,
                quantity INTEGER,
                line_total REAL
            )
            """
        ))

        # ---- Customers ----
        segments = ["enterprise", "mid-market", "small-business", "startup"]
        countries = ["US", "UK", "DE", "FR", "NG", "IN", "BR", "JP"]
        customers = []
        for i in range(1, 61):
            customers.append((
                i,
                f"Customer {i:03d}",
                f"customer{i:03d}@example.com",
                random.choice(countries),
                random.choice(segments),
                datetime(2023, 1, 1) + timedelta(days=random.randint(0, 900)),
            ))
        conn.execute(
            text("INSERT INTO customers (id, name, email, country, segment, created_at) VALUES (:id, :name, :email, :country, :segment, :created_at)"),
            [dict(id=c[0], name=c[1], email=c[2], country=c[3], segment=c[4], created_at=c[5]) for c in customers],
        )

        # ---- Products ----
        products = [
            (1, "Analytics Pro", "software", 499.0, 120.0),
            (2, "Analytics Lite", "software", 99.0, 30.0),
            (3, "Data Warehouse", "infrastructure", 1200.0, 400.0),
            (4, "API Gateway", "infrastructure", 250.0, 80.0),
            (5, "Support Plus", "services", 150.0, 60.0),
            (6, "Security Shield", "security", 300.0, 90.0),
            (7, "Mobile SDK", "developer-tools", 0.0, 10.0),
            (8, "BI Reports", "services", 75.0, 25.0),
        ]
        conn.execute(
            text("INSERT INTO products (id, name, category, price, cost) VALUES (:id, :name, :category, :price, :cost)"),
            [dict(id=p[0], name=p[1], category=p[2], price=p[3], cost=p[4]) for p in products],
        )

        # ---- Orders + order_items (last 18 months) ----
        statuses = ["completed", "completed", "completed", "pending", "refunded"]
        orders = []
        items = []
        order_id = 1
        item_id = 1
        start = datetime.now() - timedelta(days=540)
        for _ in range(1200):
            customer = random.choice(customers)
            product = random.choice(products)
            qty = random.randint(1, 5)
            ordered_at = start + timedelta(days=random.randint(0, 540))
            status = random.choice(statuses)
            orders.append((
                order_id, customer[0], product[0], qty, product[3], status, ordered_at,
            ))
            items.append((item_id, order_id, product[0], qty, round(qty * product[3], 2)))
            order_id += 1
            item_id += 1

        conn.execute(
            text("INSERT INTO orders (id, customer_id, product_id, quantity, unit_price, status, ordered_at) VALUES (:id, :customer_id, :product_id, :quantity, :unit_price, :status, :ordered_at)"),
            [dict(id=o[0], customer_id=o[1], product_id=o[2], quantity=o[3], unit_price=o[4], status=o[5], ordered_at=o[6]) for o in orders],
        )
        conn.execute(
            text("INSERT INTO order_items (id, order_id, product_id, quantity, line_total) VALUES (:id, :order_id, :product_id, :quantity, :line_total)"),
            [dict(id=i[0], order_id=i[1], product_id=i[2], quantity=i[3], line_total=i[4]) for i in items],
        )

    return {
        "seeded": True,
        "tables": sorted(SAMPLE_TABLES),
        "message": f"Sample data seeded: 60 customers, 8 products, {len(orders)} orders.",
    }


def sample_data_available(database_url: str) -> bool:
    """Whether the sample tables already exist in the target database."""
    try:
        engine = _engine(database_url)
        inspector = inspect(engine)
        return SAMPLE_TABLES.issubset(set(inspector.get_table_names()))
    except Exception:
        return False