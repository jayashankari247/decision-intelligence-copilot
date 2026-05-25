import anthropic
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv
from orchestrator.intent_classifier import IntentClassifier
from agents.customer_voice.agent import CustomerVoiceAgent
from agents.pricing_profit.agent import PricingProfitAgent
from agents.product_discovery.agent import ProductDiscoveryAgent
from agents.inventory_supply.agent import InventorySupplyAgent
from agents.campaign_intelligence.agent import CampaignIntelligenceAgent
from shared.logger import AgentLogger

AGENT_LABELS = {
    "customer_voice":         "Customer Voice Agent",
    "pricing_profit":         "Pricing & Profit Agent",
    "product_discovery":      "Product Discovery Agent",
    "inventory_supply":       "Inventory & Supply Agent",
    "campaign_intelligence":  "Campaign Intelligence Agent",
}

_SYNTHESIS_SYSTEM = (
    "You are a senior retail business analyst synthesizing insights "
    "from multiple data sources."
)


class Orchestrator:

    def __init__(self):
        load_dotenv()
        self.client = anthropic.Anthropic()
        self.classifier = IntentClassifier(self.client)
        self.agents = {
            "customer_voice":        CustomerVoiceAgent(),
            "pricing_profit":        PricingProfitAgent(),
            "product_discovery":     ProductDiscoveryAgent(),
            "inventory_supply":      InventorySupplyAgent(),
            "campaign_intelligence": CampaignIntelligenceAgent(),
        }
        self.logger = AgentLogger()

    # ── Agent dispatch ────────────────────────────────────────────────────────

    def _call_agent(self, agent_name: str, intent: dict):
        if agent_name == "customer_voice":
            mode = intent.get("customer_voice_mode", "summarize")
            search_topic = intent.get("customer_voice_topic")
            article_id = intent.get("customer_voice_article_id") or intent.get("stock_code")
            if article_id:
                return self.agents["customer_voice"].get_reviews_for_article(article_id)
            elif mode == "search" and search_topic:
                return self.agents["customer_voice"].search_reviews(search_topic)
            else:
                reviews = self.agents["customer_voice"].analyze_from_csv(max_reviews=20)
                return self.agents["customer_voice"].summarize_results(reviews)

        elif agent_name == "product_discovery":
            mode = intent.get("product_discovery_mode", "summarize")
            search_topic = intent.get("product_search_topic")
            if mode == "search" and search_topic:
                return self.agents["product_discovery"].search_catalog(search_topic)
            else:
                return self.agents["product_discovery"].summarize_catalog()

        elif agent_name == "pricing_profit":
            stock_code = intent.get("stock_code")
            if not stock_code:
                print("  No article ID in query — skipping pricing agent")
                return None
            return self.agents["pricing_profit"].analyze_pricing(stock_code)

        elif agent_name == "campaign_intelligence":
            mode = intent.get("campaign_mode", "summarize")
            article_id = intent.get("campaign_article_id")
            if mode == "analyze" and article_id:
                return self.agents["campaign_intelligence"].analyze_article(article_id)
            else:
                return self.agents["campaign_intelligence"].summarize_campaigns()

        elif agent_name == "inventory_supply":
            mode = intent.get("inventory_mode", "summarize")
            article_id = intent.get("inventory_article_id")
            if mode == "search" and article_id:
                return self.agents["inventory_supply"].analyze_article(article_id)
            else:
                return self.agents["inventory_supply"].summarize_inventory()

        return None

    # ── Main entry point ──────────────────────────────────────────────────────

    def run(self, query: str, stream_synthesis: bool = False) -> dict:
        print(f"\nQuery: {query}")
        print("-" * 60)
        t_start = time.time()

        # Step 1 — classify intent
        print("Step 1: Classifying intent...")
        intent = self.classifier.classify(query)
        print(f"  Routing to : {intent['agents']}")
        print(f"  Reasoning  : {intent['reasoning']}")

        # Step 2 — dispatch agents (parallel when >1)
        print("\nStep 2: Running agents...")
        agent_results: dict = {}
        agent_timings: dict = {}
        agents_to_run = intent["agents"]

        if len(agents_to_run) <= 1:
            for name in agents_to_run:
                print(f"\n  [{name}]")
                t0 = time.time()
                agent_results[name] = self._call_agent(name, intent)
                agent_timings[name] = round(time.time() - t0, 2)
                print(f"  [{name}] completed in {agent_timings[name]}s")
        else:
            print(f"  Running {len(agents_to_run)} agents in parallel...")
            with ThreadPoolExecutor(max_workers=len(agents_to_run)) as pool:
                future_map = {
                    pool.submit(self._call_agent, name, intent): name
                    for name in agents_to_run
                }
                for future in as_completed(future_map):
                    name = future_map[future]
                    t0 = time.time()
                    try:
                        agent_results[name] = future.result()
                        agent_timings[name] = round(time.time() - t0, 2)
                        print(f"  [{name}] done ({agent_timings[name]}s)")
                    except Exception as exc:
                        print(f"  [{name}] failed: {exc}")
                        agent_results[name] = None
                        agent_timings[name] = 0.0

        # Step 3 — format or synthesize
        print("\nStep 3: Synthesizing response...")
        if len(agent_results) == 1:
            name = list(agent_results.keys())[0]
            formatted = self._format_single(name, agent_results[name])
        elif len(agent_results) > 1:
            formatted = None if stream_synthesis else self._synthesize(query, agent_results)
        else:
            formatted = "No agents produced results for this query."

        total_latency = round(time.time() - t_start, 2)
        print(f"\nTotal latency: {total_latency}s")

        self.logger.log(
            query=query,
            intent=intent,
            agent_timings=agent_timings,
            total_latency=total_latency,
            success=any(v is not None for v in agent_results.values()),
        )

        return {
            "query":             query,
            "intent":            intent,
            "agent_results":     agent_results,
            "agent_timings":     agent_timings,
            "total_latency_sec": total_latency,
            "formatted":         formatted or "Agent returned no results.",
        }

    # ── Streaming synthesis (used by UI) ──────────────────────────────────────

    def stream_synthesis(self, query: str, agent_results: dict):
        """Yields text chunks for the multi-agent synthesis step."""
        agent_blocks = "\n\n".join([
            f"{AGENT_LABELS.get(n, n.upper())}:\n{json.dumps(r, indent=2)}"
            for n, r in agent_results.items()
            if r is not None
        ])
        prompt = (
            f'A user asked: "{query}"\n\n'
            f"{len(agent_results)} specialist agents produced the following findings:\n\n"
            f"{agent_blocks}\n\n"
            "Write a unified 3-4 sentence business recommendation that:\n"
            "1. Connects the findings across all agents into one coherent picture\n"
            "2. Highlights the single most important action the business should take\n"
            "3. Notes any tension or alignment between the different perspectives\n\n"
            "Be direct and business-focused. No bullet points — flowing prose."
        )
        with self.client.messages.stream(
            model="claude-sonnet-4-6",
            max_tokens=512,
            system=[{
                "type": "text",
                "text": _SYNTHESIS_SYSTEM,
                "cache_control": {"type": "ephemeral"},
            }],
            messages=[{"role": "user", "content": prompt}],
        ) as stream:
            for chunk in stream.text_stream:
                yield chunk

    # ── Formatting helpers ────────────────────────────────────────────────────

    def _format_single(self, agent_name, result):
        if not result:
            return "Agent returned no results."

        if agent_name == "customer_voice":
            if "direct_answer" in result:
                return (
                    f"Customer Voice — Targeted Search\n"
                    f"  Answer     : {result['direct_answer']}\n"
                    f"  Sentiment  : {result['sentiment']}\n"
                    f"  Departments: {', '.join(result.get('departments_affected', []))}\n"
                    f"  Evidence   : {result['supporting_evidence'][0] if result.get('supporting_evidence') else 'none'}\n"
                    f"  Action     : {result['recommendation']}"
                )
            return (
                f"Customer Voice — Broad Summary\n"
                f"  Reviews analyzed : {result['total_reviews']}\n"
                f"  Avg sentiment    : {result['avg_sentiment_score']}\n"
                f"  Top themes       : {', '.join(result['top_themes'])}\n"
                f"  Top negatives    : {', '.join(result['top_negatives'])}\n"
                f"  Unmet needs      : {', '.join(result['top_unmet_needs'])}\n"
                f"  Summary          : {result['executive_summary']}"
            )

        if agent_name == "product_discovery":
            if "direct_answer" in result:
                return (
                    f"Product Discovery — Catalog Search\n"
                    f"  Answer     : {result['direct_answer']}\n"
                    f"  Matches    : {result.get('total_matches', '?')}\n"
                    f"  Colours    : {', '.join(result.get('colour_variety', []))}\n"
                    f"  Styles     : {', '.join(result.get('style_variety', []))}\n"
                    f"  Coverage   : {result.get('coverage_assessment', '')}\n"
                    f"  Gap        : {result.get('gap_identified', '')}"
                )
            return (
                f"Product Discovery — Catalog Summary\n"
                f"  Products sampled  : {result.get('total_products_sampled', '?')}\n"
                f"  Categories        : {', '.join(result.get('categories_represented', []))}\n"
                f"  Dominant colours  : {', '.join(result.get('dominant_colours', []))}\n"
                f"  Dominant styles   : {', '.join(result.get('dominant_styles', []))}\n"
                f"  Strengths         : {', '.join(result.get('catalog_strengths', []))}\n"
                f"  Gaps              : {', '.join(result.get('catalog_gaps', []))}\n"
                f"  Summary           : {result.get('executive_summary', '')}"
            )

        if agent_name == "pricing_profit":
            return (
                f"Pricing Analysis — {result.get('description', '')}\n"
                f"  Elasticity    : {result['price_elasticity']}\n"
                f"  Recommended   : {result['recommended_price']}\n"
                f"  Rationale     : {result['recommendation_rationale']}\n"
                f"  Confidence    : {result['confidence']}"
            )

        if agent_name == "campaign_intelligence":
            if "promotion_recommendation" in result:
                return (
                    f"Campaign Intelligence — Article {result.get('article_id', '')}\n"
                    f"  Recommendation  : {result['promotion_recommendation']}\n"
                    f"  Campaign type   : {result.get('campaign_type', '?')}\n"
                    f"  Suggested disc  : {result.get('suggested_discount_pct', 0)}%\n"
                    f"  Demand trend    : {result.get('demand_trend', '?')} "
                    f"({result.get('demand_change_pct', 0)}%)\n"
                    f"  Timing          : {result.get('campaign_timing', '')}\n"
                    f"  Rationale       : {result.get('rationale', '')}\n"
                    f"  Risk of inaction: {result.get('risk_of_inaction', '')}"
                )
            return (
                f"Campaign Intelligence — Portfolio Summary\n"
                f"  Candidates       : {result.get('total_candidates', '?')}\n"
                f"  High urgency     : {result.get('high_urgency_count', '?')}\n"
                f"  Campaign types   : {', '.join(result.get('recommended_campaign_types', []))}\n"
                f"  Actions          : {'; '.join(result.get('immediate_actions', []))}\n"
                f"  Summary          : {result.get('executive_summary', '')}"
            )

        if agent_name == "inventory_supply":
            if "recommended_order_quantity" in result:
                return (
                    f"Inventory Analysis — Article {result.get('article_id', '')}\n"
                    f"  Status           : {result['replenishment_status']}\n"
                    f"  Days to stockout : {result['days_until_stockout']}\n"
                    f"  Order quantity   : {result['recommended_order_quantity']} units\n"
                    f"  Order by         : {result['recommended_order_date']}\n"
                    f"  Rationale        : {result['rationale']}\n"
                    f"  Confidence       : {result['confidence']}"
                )
            return (
                f"Inventory Health Summary\n"
                f"  At-risk articles  : {result.get('total_at_risk', '?')}\n"
                f"  Critical          : {result.get('critical_count', '?')}\n"
                f"  Stockout this week: {result.get('projected_stockout_this_week', '?')}\n"
                f"  Top priorities    : {', '.join(result.get('top_priority_articles', []))}\n"
                f"  Actions           : {'; '.join(result.get('immediate_actions', []))}\n"
                f"  Summary           : {result.get('executive_summary', '')}"
            )

        return str(result)

    def _synthesize(self, query, agent_results):
        agent_blocks = "\n\n".join([
            f"{AGENT_LABELS.get(n, n.upper())}:\n{json.dumps(r, indent=2)}"
            for n, r in agent_results.items()
            if r is not None
        ])
        prompt = (
            f'A user asked: "{query}"\n\n'
            f"{len(agent_results)} specialist agents produced the following findings:\n\n"
            f"{agent_blocks}\n\n"
            "Write a unified 3-4 sentence business recommendation that:\n"
            "1. Connects the findings across all agents into one coherent picture\n"
            "2. Highlights the single most important action the business should take\n"
            "3. Notes any tension or alignment between the different perspectives\n\n"
            "Be direct and business-focused. No bullet points — flowing prose."
        )
        response = self.client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=512,
            system=[{
                "type": "text",
                "text": _SYNTHESIS_SYSTEM,
                "cache_control": {"type": "ephemeral"},
            }],
            messages=[{"role": "user", "content": prompt}],
        )
        return f"Unified Recommendation:\n\n{response.content[0].text}"
