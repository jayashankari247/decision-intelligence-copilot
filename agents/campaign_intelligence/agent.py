import anthropic
import csv
import json
import os
from dotenv import load_dotenv
from agents.campaign_intelligence.trend_analyzer import DemandTrendAnalyzer
from agents.campaign_intelligence.prompts import CAMPAIGN_ANALYSIS_PROMPT, CAMPAIGN_SUMMARY_PROMPT
from shared.schemas import validate


class CampaignIntelligenceAgent:

    def __init__(self):
        load_dotenv()
        self.client = anthropic.Anthropic()
        self.snapshot_file = os.getenv(
            "INVENTORY_SNAPSHOT_FILE", "data/inventory_supply/inventory_snapshot.csv"
        )
        self.transactions_file = os.getenv(
            "TRANSACTIONS_FILE", "data/product_discovery/transactions_train.csv"
        )
        self.articles_file = os.getenv(
            "ARTICLES_FILE", "data/product_discovery/articles.csv"
        )
        self.analyzer = DemandTrendAnalyzer(self.transactions_file)

    def _read_snapshot(self):
        with open(self.snapshot_file, newline="", encoding="utf-8") as f:
            return list(csv.DictReader(f))

    def _get_article_snapshot(self, article_id):
        with open(self.snapshot_file, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if row["article_id"] == article_id:
                    return row
        return None

    def _get_product_name(self, article_id):
        with open(self.articles_file, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if row["article_id"] == article_id:
                    return row.get("prod_name", "Unknown")
        return "Unknown"

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
            raw = raw.split("```")[0]
        start = raw.find("{")
        end   = raw.rfind("}") + 1
        if start != -1 and end > start:
            raw = raw[start:end]
        try:
            return json.loads(raw.strip())
        except json.JSONDecodeError:
            return None

    def analyze_article(self, article_id: str) -> dict | None:
        print(f"  Analyzing campaign opportunity for article: {article_id}")
        snapshot = self._get_article_snapshot(article_id)
        if not snapshot:
            print(f"  Article {article_id} not found in inventory snapshot")
            return None

        trend        = self.analyzer.get_trend(article_id)
        product_name = self._get_product_name(article_id)
        current_stock = int(snapshot["current_stock"])
        reorder_point = int(snapshot["reorder_point"])
        stock_ratio   = current_stock / max(reorder_point, 1)
        inventory_status = "HIGH" if stock_ratio > 3 else "NORMAL" if stock_ratio > 1 else "LOW"

        context = (
            f"Article ID: {article_id}\n"
            f"Product Name: {product_name}\n"
            f"Current Stock: {current_stock} units\n"
            f"Reorder Point: {reorder_point} units\n"
            f"Stock Ratio (current/reorder): {stock_ratio:.1f}x\n"
            f"Inventory Status: {inventory_status}\n"
            f"Warehouse: {snapshot['warehouse']}\n"
        )
        if trend:
            context += (
                f"Demand Trend: {trend['trend']}\n"
                f"Demand Change: {trend['demand_change_pct']}%\n"
                f"Recent Daily Demand: {trend['recent_daily_demand']:.2f} units/day\n"
                f"Earlier Daily Demand: {trend['earlier_daily_demand']:.2f} units/day\n"
                f"Date Range Analyzed: {trend.get('date_range', 'unknown')}"
            )
        else:
            context += "Demand Trend: UNKNOWN (no transaction data for this article)"

        try:
            response = self._call_claude(CAMPAIGN_ANALYSIS_PROMPT, context, max_tokens=512)
            result   = self._parse_json(response.content[0].text)
            if result is None:
                print("  Claude returned invalid JSON for campaign analysis")
                return None
            return validate("campaign_article", result)
        except anthropic.APIConnectionError:
            print("  Could not connect to Anthropic API")
            return None

    def summarize_campaigns(self) -> dict | None:
        print("  Identifying promotion candidates across catalog...")
        snapshot   = self._read_snapshot()
        candidates = self.analyzer.get_promotion_candidates(snapshot, top_n=20)

        if not candidates:
            print("  No promotion candidates found")
            return None

        print(f"  Found {len(candidates)} promotion candidates")
        candidate_text = "\n".join([
            f"- Article {c['article_id']} | Stock: {c['current_stock']} | "
            f"Reorder: {c['reorder_point']} | Warehouse: {c['warehouse']} | "
            f"Trend: {c['trend']} | Demand change: {c['demand_change_pct']}% | "
            f"Stock ratio: {c['stock_ratio']}x | Urgency: {c['urgency']}"
            for c in candidates
        ])
        prompt = (
            f"Total catalog sampled: {len(snapshot)} articles\n"
            f"Promotion candidates ({len(candidates)} identified):\n{candidate_text}"
        )

        try:
            response = self._call_claude(CAMPAIGN_SUMMARY_PROMPT, prompt, max_tokens=2048)
            result   = self._parse_json(response.content[0].text)
            if result is None:
                print("  Claude returned invalid JSON for campaign summary")
                return None
            result["total_candidates"] = len(candidates)
            return validate("campaign_summary", result)
        except anthropic.APIConnectionError:
            print("  Could not connect to Anthropic API")
            return None
