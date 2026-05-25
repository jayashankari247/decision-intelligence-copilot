import anthropic
import csv
import json
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from agents.inventory_supply.forecaster import DemandForecaster
from agents.inventory_supply.prompts import INVENTORY_ANALYSIS_PROMPT, INVENTORY_SUMMARY_PROMPT
from shared.schemas import validate

DEFAULT_DAILY_DEMAND = 1.0


class InventorySupplyAgent:

    def __init__(self):
        load_dotenv()
        self.client = anthropic.Anthropic()
        self.snapshot_file = os.getenv(
            "INVENTORY_SNAPSHOT_FILE", "data/inventory_supply/inventory_snapshot.csv"
        )
        self.transactions_file = os.getenv(
            "TRANSACTIONS_FILE", "data/product_discovery/transactions_train.csv"
        )
        self.forecaster = DemandForecaster(self.transactions_file)

    def _read_snapshot(self):
        with open(self.snapshot_file, newline="", encoding="utf-8") as f:
            return list(csv.DictReader(f))

    def _get_article_snapshot(self, article_id):
        with open(self.snapshot_file, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if row["article_id"] == article_id:
                    return row
        return None

    def _compute_replenishment(self, snapshot, demand):
        current_stock = int(snapshot["current_stock"])
        reorder_point = int(snapshot["reorder_point"])
        lead_time     = int(snapshot["lead_time_days"])
        daily_rate    = demand["daily_demand_rate"] if demand else DEFAULT_DAILY_DEMAND

        days_until_stockout = int(current_stock / daily_rate) if daily_rate > 0 else 999
        safety_stock        = int(daily_rate * lead_time * 1.5)
        recommended_qty     = max(0, safety_stock + reorder_point - current_stock)
        order_date          = datetime.today() + timedelta(days=max(0, days_until_stockout - lead_time))

        if days_until_stockout <= lead_time:
            status = "CRITICAL"
        elif current_stock < reorder_point:
            status = "AT_RISK"
        else:
            status = "HEALTHY"

        return {
            "current_stock":    current_stock,
            "reorder_point":    reorder_point,
            "lead_time":        lead_time,
            "daily_rate":       daily_rate,
            "days_until_stockout": days_until_stockout,
            "recommended_qty":  recommended_qty,
            "order_date":       order_date.strftime("%Y-%m-%d"),
            "status":           status,
            "warehouse":        snapshot["warehouse"],
        }

    def _call_claude(self, system_prompt, user_content, max_tokens=512):
        return self.client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=max_tokens,
            system=[{
                "type": "text",
                "text": system_prompt,
                "cache_control": {"type": "ephemeral"},
            }],
            messages=[{"role": "user", "content": user_content}],
        )

    @staticmethod
    def _parse_json(raw: str) -> dict | None:
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        try:
            return json.loads(raw.strip())
        except json.JSONDecodeError:
            return None

    def analyze_article(self, article_id: str) -> dict | None:
        print(f"  Analyzing inventory for article: {article_id}")
        snapshot = self._get_article_snapshot(article_id)
        if not snapshot:
            print(f"  Article {article_id} not found in inventory snapshot")
            return None

        demand  = self.forecaster.get_demand(article_id)
        metrics = self._compute_replenishment(snapshot, demand)

        context = (
            f"Article ID: {article_id}\n"
            f"Current Stock: {metrics['current_stock']} units\n"
            f"Reorder Point: {metrics['reorder_point']} units\n"
            f"Lead Time: {metrics['lead_time']} days\n"
            f"Warehouse: {metrics['warehouse']}\n"
            f"Daily Demand Rate: {metrics['daily_rate']:.2f} units/day\n"
            f"Days Until Stockout: {metrics['days_until_stockout']}\n"
            f"Recommended Order Quantity: {metrics['recommended_qty']} units\n"
            f"Suggested Order Date: {metrics['order_date']}\n"
            f"Status: {metrics['status']}"
        )

        try:
            response = self._call_claude(INVENTORY_ANALYSIS_PROMPT, context, max_tokens=512)
            result   = self._parse_json(response.content[0].text)
            if result is None:
                print("  Claude returned invalid JSON for inventory analysis")
                return None
            return validate("inventory_article", result)
        except anthropic.APIConnectionError:
            print("  Could not connect to Anthropic API")
            return None

    def summarize_inventory(self) -> dict | None:
        print("  Scanning inventory for at-risk products...")
        snapshot = self._read_snapshot()
        at_risk  = self.forecaster.get_at_risk_articles(snapshot, top_n=20)

        if not at_risk:
            print("  No at-risk articles found")
            return None

        print(f"  Found {len(at_risk)} at-risk articles for analysis")
        at_risk_text = "\n".join([
            f"- Article {a['article_id']} | Stock: {a['current_stock']} | "
            f"Reorder: {a['reorder_point']} | Lead: {a['lead_time_days']}d | "
            f"Warehouse: {a['warehouse']} | "
            f"Daily demand: {a['daily_demand_rate']:.2f} | "
            f"Days until stockout: {a['days_until_stockout']}"
            for a in at_risk
        ])
        prompt = (
            f"Total inventory snapshot: {len(snapshot)} articles\n"
            f"At-risk articles ({len(at_risk)} shown):\n{at_risk_text}"
        )

        try:
            response = self._call_claude(INVENTORY_SUMMARY_PROMPT, prompt, max_tokens=1024)
            result   = self._parse_json(response.content[0].text)
            if result is None:
                print("  Claude returned invalid JSON for inventory summary")
                return None
            result["total_at_risk"] = len(at_risk)
            return validate("inventory_summary", result)
        except anthropic.APIConnectionError:
            print("  Could not connect to Anthropic API")
            return None
