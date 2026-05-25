import csv
import os
import sqlite3
from collections import defaultdict
from datetime import datetime


class DemandForecaster:

    def __init__(self, transactions_file, max_rows=100_000):
        self.transactions_file = transactions_file
        self.max_rows = max_rows
        self.db_file = os.getenv("SQLITE_DB", "data/retail.db")
        self._demand_cache = None

    def _use_sqlite(self) -> bool:
        return os.path.exists(self.db_file)

    # ── Per-article lookup ────────────────────────────────────────────────────

    def get_demand(self, article_id: str) -> dict | None:
        if self._use_sqlite():
            return self._get_demand_sqlite(article_id)
        return self._load_demand_csv().get(article_id)

    def _get_demand_sqlite(self, article_id: str) -> dict | None:
        conn = sqlite3.connect(self.db_file)
        cur = conn.cursor()
        cur.execute(
            "SELECT daily_demand_rate, total_transactions, date_min, date_max "
            "FROM demand_summary WHERE article_id = ?",
            (article_id,)
        )
        row = cur.fetchone()
        conn.close()
        if not row:
            return None
        rate, total, d_min, d_max = row
        return {
            "daily_demand_rate":  round(rate, 4),
            "total_transactions": total,
            "first_seen":         d_min,
            "last_seen":          d_max,
        }

    # ── Portfolio at-risk scan ────────────────────────────────────────────────

    def get_at_risk_articles(self, inventory_snapshot: list, top_n: int = 20) -> list:
        if self._use_sqlite():
            demand = self._load_demand_sqlite_all()
        else:
            demand = self._load_demand_csv()

        at_risk = []
        for item in inventory_snapshot:
            article_id   = item["article_id"]
            current_stock = int(item["current_stock"])
            reorder_point = int(item["reorder_point"])
            lead_time     = int(item["lead_time_days"])

            if current_stock < reorder_point:
                d = demand.get(article_id, {"daily_demand_rate": 1.0})
                daily_rate = d["daily_demand_rate"]
                days_until_stockout = int(current_stock / daily_rate) if daily_rate > 0 else 999
                at_risk.append({
                    **item,
                    "daily_demand_rate":  round(daily_rate, 4),
                    "days_until_stockout": days_until_stockout,
                    "urgency_score":       lead_time - days_until_stockout,
                })

        at_risk.sort(key=lambda x: x["urgency_score"], reverse=True)
        return at_risk[:top_n]

    def _load_demand_sqlite_all(self) -> dict:
        conn = sqlite3.connect(self.db_file)
        cur = conn.cursor()
        cur.execute("SELECT article_id, daily_demand_rate FROM demand_summary")
        rows = cur.fetchall()
        conn.close()
        return {r[0]: {"daily_demand_rate": round(r[1], 4)} for r in rows}

    # ── CSV fallback ──────────────────────────────────────────────────────────

    def _load_demand_csv(self) -> dict:
        if self._demand_cache is not None:
            return self._demand_cache

        print(f"  Loading demand data from CSV (up to {self.max_rows} rows)...")
        counts = defaultdict(int)
        min_dates, max_dates = {}, {}

        with open(self.transactions_file, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader):
                if i >= self.max_rows:
                    break
                aid  = row["article_id"]
                date = datetime.strptime(row["t_dat"], "%Y-%m-%d")
                counts[aid] += 1
                if aid not in min_dates or date < min_dates[aid]:
                    min_dates[aid] = date
                if aid not in max_dates or date > max_dates[aid]:
                    max_dates[aid] = date

        self._demand_cache = {}
        for aid, count in counts.items():
            span = (max_dates[aid] - min_dates[aid]).days or 1
            self._demand_cache[aid] = {
                "total_transactions": count,
                "daily_demand_rate":  round(count / span, 4),
                "first_seen":         min_dates[aid].strftime("%Y-%m-%d"),
                "last_seen":          max_dates[aid].strftime("%Y-%m-%d"),
            }

        print(f"  Demand data loaded for {len(self._demand_cache)} articles")
        return self._demand_cache
