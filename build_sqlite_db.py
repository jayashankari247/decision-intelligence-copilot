"""
One-time script: pre-aggregates transactions_train.csv into a SQLite database.
Run this once after setting up the project. Eliminates CSV scanning on every query.

Usage:
    python build_sqlite_db.py

The database is saved to the path in SQLITE_DB env var (default: data/retail.db).
Agents automatically use SQLite if the file exists, and fall back to CSV if not.
"""
import csv
import os
import sqlite3
import time
from collections import defaultdict
from dotenv import load_dotenv

load_dotenv()

TRANSACTIONS_FILE = os.getenv("TRANSACTIONS_FILE", "data/product_discovery/transactions_train.csv")
DB_FILE = os.getenv("SQLITE_DB", "data/retail.db")


def build_db():
    print(f"Source : {TRANSACTIONS_FILE}")
    print(f"Output : {DB_FILE}")
    print()

    if not os.path.exists(TRANSACTIONS_FILE):
        print(f"ERROR: transactions file not found at {TRANSACTIONS_FILE}")
        return

    os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)

    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    cur.executescript("""
        DROP TABLE IF EXISTS price_points;
        DROP TABLE IF EXISTS demand_daily;
        DROP TABLE IF EXISTS demand_summary;

        CREATE TABLE price_points (
            article_id  TEXT,
            price       REAL,
            txn_count   INTEGER,
            total_rev   REAL,
            PRIMARY KEY (article_id, price)
        );

        CREATE TABLE demand_daily (
            article_id  TEXT,
            date        TEXT,
            txn_count   INTEGER,
            PRIMARY KEY (article_id, date)
        );
    """)

    price_data = defaultdict(lambda: defaultdict(int))
    daily_data = defaultdict(lambda: defaultdict(int))
    row_count = 0
    t0 = time.time()

    print("Reading transactions (this takes a few minutes for the full dataset)...")
    with open(TRANSACTIONS_FILE, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            row_count += 1
            if row_count % 500_000 == 0:
                elapsed = time.time() - t0
                print(f"  {row_count:>10,} rows  ({elapsed:.0f}s elapsed)")

            article_id = row["article_id"]
            date = row["t_dat"]
            try:
                price = float(row["price"])
            except (ValueError, KeyError):
                continue

            if price > 0:
                price_data[article_id][round(price, 4)] += 1
            daily_data[article_id][date] += 1

    print(f"\nRows processed        : {row_count:,}")
    print(f"Articles (price data) : {len(price_data):,}")
    print(f"Articles (demand data): {len(daily_data):,}")

    print("\nWriting price_points...")
    price_rows = [
        (article_id, price, count, round(price * count, 4))
        for article_id, prices in price_data.items()
        for price, count in prices.items()
    ]
    cur.executemany("INSERT OR REPLACE INTO price_points VALUES (?, ?, ?, ?)", price_rows)

    print("Writing demand_daily...")
    daily_rows = [
        (article_id, date, count)
        for article_id, dates in daily_data.items()
        for date, count in dates.items()
    ]
    cur.executemany("INSERT OR REPLACE INTO demand_daily VALUES (?, ?, ?)", daily_rows)

    print("Building demand_summary...")
    cur.execute("""
        CREATE TABLE demand_summary AS
        SELECT
            article_id,
            SUM(txn_count)  AS total_transactions,
            MIN(date)       AS date_min,
            MAX(date)       AS date_max,
            CAST(SUM(txn_count) AS REAL)
                / MAX(1.0, julianday(MAX(date)) - julianday(MIN(date)))
                            AS daily_demand_rate
        FROM demand_daily
        GROUP BY article_id
    """)

    print("Creating indexes...")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_pp ON price_points(article_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_dd ON demand_daily(article_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_ds ON demand_summary(article_id)")

    conn.commit()
    conn.close()

    size_mb = os.path.getsize(DB_FILE) / (1024 * 1024)
    total_time = time.time() - t0
    print(f"\nDone in {total_time:.0f}s  |  DB size: {size_mb:.1f} MB  |  Saved to: {DB_FILE}")


if __name__ == "__main__":
    build_db()
