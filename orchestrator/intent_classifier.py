import anthropic
import json
from dotenv import load_dotenv


class IntentClassifier:

    def __init__(self, client):
        self.client = client

    def classify(self, query):
        response = self.client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=256,
            system="""You are a query router for a retail Decision Intelligence system.
Given a user question, decide which specialist agents should handle it and how.

Available agents:
- customer_voice: questions about customer sentiment, reviews, feedback, themes, complaints, unmet needs for a specific product or overall
- pricing_profit: questions about pricing, price elasticity, revenue, margins, optimal price points
- product_discovery: questions about product catalog coverage, available options, color/style variety, product trends, what products exist
- inventory_supply: questions about stock levels, replenishment, stockouts, supply chain, inventory health, which products need reordering
- campaign_intelligence: questions about promotions, price discounts, marketing campaigns, demand slowdowns, off-season products, when to run a sale

For customer_voice queries, also determine the query mode:
- "search": specific targeted question about a particular issue or topic (e.g. "complaints about petite sizing", "skirt quality feedback")
- "summarize": broad overview of customer feedback (e.g. "what are customers saying overall")

For product_discovery queries, also determine the query mode:
- "search": specific question about catalog coverage or options (e.g. "how many black tops do we have", "casual tops across multiple colors")
- "summarize": broad overview of catalog by categories (e.g. "what does our catalog look like overall", "summarize our product range")

For inventory_supply queries, also determine the query mode:
- "search": question about a specific article (e.g. "what is the replenishment status for article 0663713001", "does article 0108775015 need reordering")
- "summarize": broad overview of inventory health (e.g. "which products are at risk of stockout", "give me an inventory health summary")

For campaign_intelligence queries, also determine the query mode:
- "analyze": question about a specific article (e.g. "should we run a promotion for article 0108775015", "is article 0663713001 ready for a discount")
- "summarize": portfolio-wide view (e.g. "which products should we promote", "where should we run campaigns this month")

Return ONLY a JSON object:
{
    "agents": ["list of agent names to call — one or more"],
    "reasoning": "one sentence explaining the routing decision",
    "stock_code": "H&M article ID (10-digit number) if mentioned, otherwise null",
    "customer_voice_article_id": "H&M article ID if the customer voice question is about a specific product, otherwise null",
    "requires_synthesis": true or false,
    "customer_voice_mode": "search" or "summarize" or null,
    "customer_voice_topic": "specific topic for customer voice search, otherwise null",
    "product_discovery_mode": "search" or "summarize" or null,
    "product_search_topic": "specific topic for product catalog search, otherwise null",
    "inventory_mode": "search" or "summarize" or null,
    "inventory_article_id": "article ID if a specific product is mentioned, otherwise null",
    "campaign_mode": "analyze" or "summarize" or null,
    "campaign_article_id": "article ID if a specific product is mentioned for campaign analysis, otherwise null"
}
Return only the JSON. No explanation, no markdown, no code blocks.""",
            messages=[{"role": "user", "content": query}]
        )

        try:
            return json.loads(response.content[0].text)
        except json.JSONDecodeError:
            return {
                "agents": ["customer_voice"],
                "reasoning": "Could not parse intent — defaulting to customer voice summarize",
                "stock_code": None,
                "requires_synthesis": False,
                "customer_voice_mode": "summarize",
                "customer_voice_topic": None,
                "product_discovery_mode": None,
                "product_search_topic": None,
                "inventory_mode": None,
                "inventory_article_id": None,
                "campaign_mode": None,
                "campaign_article_id": None,
                "customer_voice_article_id": None
            }
