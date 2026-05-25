import csv
import os
import sqlite3
from collections import defaultdict


class DemandTrendAnalyzer:

    def __init__(self, transactions_file, max_rows=100_000):
        self.transactions_file = transactions_file
        self.max_rows = max_rows
        self.db_file = os.getenv("SQLITE_DB", "data/retail.db")
        self._trend_cache = None

    def _use_sqlite(self) -> bool:
        return os.path.exists(self.db_file)

    # ── Per-article trend ─────────────────────────────────────────────────────

    def get_trend(self, article_id: str) -> dict | None:
        if self._use_sqlite():
            return self._get_trend_sqlite(article_id)
        return self._load_trends_csv().get(article_id)

    def _get_trend_sqlite(self, article_id: str) -> dict | None:
        conn = sqlite3.connect(self.db_file)
        cur = conn.cursor()
        cur.execute(
            "SELECT date, txn_count FROM demand_daily WHERE article_id = ? ORDER BY date",
            (article_id,)
        )
        rows = cur.fetchall()
        conn.close()
        if not rows:
            return None
        return self._compute_trend(article_id, {r[0]: r[1] for r in rows})

    # ── Portfolio promotion candidates ────────────────────────────────────────

    def get_promotion_candidates(self, inventory_snapshot: list, top_n: int = 20) -> list:
        if self._use_sqlite():
            trends = self._load_trends_sqlite_all()
        else:
            trends = self._load_trends_csv()

        candidates = []
        for item in inventory_snapshot:
            article_id    = item["article_id"]
            current_stock = int(item["current_stock"])
            reorder_point = int(item["reorder_point"])
            stock_ratio   = current_stock / max(reorder_point, 1)
            trend_data    = trends.get(article_id)

            if not trend_data:
                continue

            if trend_data["trend"] == "DECLINING" or stock_ratio > 2.5:
                urgency = (
                    "HIGH"
                    if trend_data["trend"] == "DECLINING" and stock_ratio > 2.0
                    else "MEDIUM"
                )
                candidates.append({
                    **item,
                    "trend":               trend_data["trend"],
                    "demand_change_pct":   trend_data["demand_change_pct"],
                    "recent_daily_demand": trend_data["recent_daily_demand"],
                    "stock_ratio":         round(stock_ratio, 2),
                    "urgency":             urgency,
                })

        candidates.sort(key=lambda x: (x["urgency"] != "HIGH", -abs(x["demand_change_pct"])))
        return candidates[:top_n]

    def _load_trends_sqlite_all(self) -> dict:
        conn = sqlite3.connect(self.db_file)
        cur = conn.cursor()
        cur.execute("SELECT article_id, date, txn_count FROM demand_daily ORDER BY article_id, date")
        rows = cur.fetchall()
        conn.close()

        daily: dict = defaultdict(dict)
        for article_id, date, count in rows:
            daily[article_id][date] = count

        return {aid: self._compute_trend(aid, dm) for aid, dm in daily.items()}

    # ── Trend computation ─────────────────────────────────────────────────────

    @staticmethod
    def _compute_trend(article_id: str, date_map: dict) -> dict:
        sorted_dates = sorted(date_map.keys())
        if len(sorted_dates) < 2:
            avg = sum(date_map.values()) / len(date_map)
            return {
                "trend":               "STABLE",
                "demand_change_pct":   0,
                "recent_daily_demand": round(avg, 4),
                "earlier_daily_demand": round(avg, 4),
                "date_range":          f"{sorted_dates[0]} to {sorted_dates[0]}",
                "data_points":         len(sorted_dates),
            }

        midpoint     = len(sorted_dates) // 2
        early_dates  = sorted_dates[:midpoint]
        recent_dates = sorted_dates[midpoint:]

        early_demand  = sum(date_map[d] for d in early_dates) / len(early_dates)
        recent_demand = sum(date_map[d] for d in recent_dates) / len(recent_dates)

        change_pct = (
            round(((recent_demand - early_demand) / early_demand) * 100, 1)
            if early_demand > 0 else 0
        )
        trend = "DECLINING" if change_pct < -20 else "GROWING" if change_pct > 20 else "STABLE"

        return {
            "trend":                trend,
            "demand_change_pct":    change_pct,
            "recent_daily_demand":  round(recent_demand, 4),
            "earlier_daily_demand": round(early_demand, 4),
            "date_range":           f"{sorted_dates[0]} to {sorted_dates[-1]}",
            "data_points":          len(sorted_dates),
        }

    # ── CSV fallback ──────────────────────────────────────────────────────────

    def _load_trends_csv(self) -> dict:
        if self._trend_cache is not None:
            return self._trend_cache

        print(f"  Loading transaction trends from CSV (up to {self.max_rows} rows)...")
        daily_counts: dict = defaultdict(lambda: defaultdict(int))

        with open(self.transactions_file, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader):
                if i >= self.max_rows:
                    break
                daily_counts[row["article_id"]][row["t_dat"]] += 1

        self._trend_cache = {
            aid: self._compute_trend(aid, dm) for aid, dm in daily_counts.items()
        }
        print(f"  Trend data computed for {len(self._trend_cache)} articles")
        return self._trend_cache
