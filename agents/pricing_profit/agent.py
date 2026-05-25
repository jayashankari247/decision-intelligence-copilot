import anthropic
import csv
import json
import os
import sqlite3
from collections import defaultdict
from dotenv import load_dotenv
from agents.pricing_profit.prompts import SYSTEM_PROMPT, build_user_message
from shared.schemas import validate


class PricingProfitAgent:

    def __init__(self):
        load_dotenv()
        self.client = anthropic.Anthropic()
        self.transactions_file = os.getenv(
            "TRANSACTIONS_FILE", "data/product_discovery/transactions_train.csv"
        )
        self.articles_file = os.getenv(
            "ARTICLES_FILE", "data/product_discovery/articles.csv"
        )
        self.db_file = os.getenv("SQLITE_DB", "data/retail.db")
        self._price_cache = None

    # ── Data access — SQLite preferred, CSV fallback ──────────────────────────

    def _use_sqlite(self) -> bool:
        return os.path.exists(self.db_file)

    def _get_price_points_sqlite(self, article_id: str) -> list:
        conn = sqlite3.connect(self.db_file)
        cur = conn.cursor()
        cur.execute(
            "SELECT price, txn_count, total_rev FROM price_points WHERE article_id = ? ORDER BY price",
            (article_id,)
        )
        rows = cur.fetchall()
        conn.close()
        return [{"price": p, "transactions": c, "total_revenue": r} for p, c, r in rows]

    def _load_price_data(self, max_rows=300_000):
        if self._price_cache is not None:
            return self._price_cache
        print(f"  Loading price data from CSV (up to {max_rows} rows)...")
        price_groups = defaultdict(lambda: defaultdict(int))
        with open(self.transactions_file, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader):
                if i >= max_rows:
                    break
                try:
                    price = float(row["price"])
                except (ValueError, KeyError):
                    continue
                if price > 0:
                    price_groups[row["article_id"]][round(price, 4)] += 1
        self._price_cache = {aid: dict(p) for aid, p in price_groups.items()}
        print(f"  Price data loaded for {len(self._price_cache)} articles")
        return self._price_cache

    def _get_product_name(self, article_id: str) -> str:
        with open(self.articles_file, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if row["article_id"] == article_id:
                    return row.get("prod_name", "Unknown")
        return "Unknown"

    # ── Public methods ────────────────────────────────────────────────────────

    def aggregate_product_data(self, article_id: str) -> dict | None:
        if self._use_sqlite():
            price_points = self._get_price_points_sqlite(article_id)
        else:
            prices = self._load_price_data().get(article_id, {})
            price_points = [
                {"price": p, "transactions": c, "total_revenue": round(p * c, 4)}
                for p, c in sorted(prices.items())
            ]

        if not price_points:
            return None

        return {
            "article_id":   article_id,
            "product_name": self._get_product_name(article_id),
            "price_points": price_points,
        }

    def analyze_pricing(self, article_id: str) -> dict | None:
        source = "SQLite" if self._use_sqlite() else "CSV"
        print(f"  Aggregating price data for {article_id} ({source})...")
        price_summary = self.aggregate_product_data(article_id)

        if not price_summary:
            print(f"  No transaction data found for {article_id}")
            return None

        print(
            f"  Found {len(price_summary['price_points'])} price point(s) "
            f"for {price_summary['product_name']}"
        )
        print("  Sending to Claude for analysis...")

        user_message = build_user_message(
            price_summary["article_id"],
            price_summary["product_name"],
            price_summary,
        )

        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=1024,
                system=[{
                    "type": "text",
                    "text": SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                }],
                messages=[{"role": "user", "content": user_message}],
            )
            raw = response.content[0].text.strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            result = json.loads(raw.strip())
            result["price_points_analyzed"] = len(price_summary["price_points"])
            result["description"] = price_summary["product_name"]
            return validate("pricing", result)

        except json.JSONDecodeError:
            print(f"  Claude returned invalid JSON for {article_id}")
            return None
        except anthropic.APIConnectionError:
            print("  Could not connect to Anthropic API")
            return None
        except anthropic.BadRequestError as e:
            print(f"  Bad request: {e}")
            return None
