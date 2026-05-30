import json
import time
import anthropic
from langgraph.graph import StateGraph, START, END
from langgraph.types import Send

from orchestrator.retail_state import RetailState
from orchestrator.intent_classifier import IntentClassifier
from agents.customer_voice.agent import CustomerVoiceAgent
from agents.pricing_profit.agent import PricingProfitAgent
from agents.product_discovery.agent import ProductDiscoveryAgent
from agents.inventory_supply.agent import InventorySupplyAgent
from agents.campaign_intelligence.agent import CampaignIntelligenceAgent


AGENT_LABELS = {
    "customer_voice":        "Customer Voice Agent",
    "pricing_profit":        "Pricing & Profit Agent",
    "product_discovery":     "Product Discovery Agent",
    "inventory_supply":      "Inventory & Supply Agent",
    "campaign_intelligence": "Campaign Intelligence Agent",
}

_SYNTHESIS_SYSTEM = (
    "You are a senior retail business analyst synthesizing insights "
    "from multiple data sources."
)

AGENT_NODES = [
    "customer_voice",
    "pricing_profit",
    "product_discovery",
    "inventory_supply",
    "campaign_intelligence",
]

# Instantiated once at module load — reused across all graph invocations
_client     = anthropic.Anthropic()
_classifier = IntentClassifier(_client)
_agents = {
    "customer_voice":        CustomerVoiceAgent(),
    "pricing_profit":        PricingProfitAgent(),
    "product_discovery":     ProductDiscoveryAgent(),
    "inventory_supply":      InventorySupplyAgent(),
    "campaign_intelligence": CampaignIntelligenceAgent(),
}


# ── Node functions ────────────────────────────────────────────────────────────

def classify_intent_node(state: RetailState) -> dict:
    intent = _classifier.classify(state["query"])
    return {"intent": intent}


def customer_voice_node(state: RetailState) -> dict:
    intent       = state["intent"]
    mode         = intent.get("customer_voice_mode", "summarize")
    search_topic = intent.get("customer_voice_topic")
    article_id   = intent.get("customer_voice_article_id") or intent.get("stock_code")

    t0    = time.time()
    agent = _agents["customer_voice"]
    if article_id:
        result = agent.get_reviews_for_article(article_id)
    elif mode == "search" and search_topic:
        result = agent.search_reviews(search_topic)
    else:
        result = agent.summarize_results(agent.analyze_from_csv(max_reviews=20))

    return {
        "agent_results": {"customer_voice": result},
        "agent_timings": {"customer_voice": round(time.time() - t0, 2)},
    }


def pricing_profit_node(state: RetailState) -> dict:
    intent     = state["intent"]
    stock_code = intent.get("stock_code")
    if not stock_code:
        return {"agent_results": {}, "agent_timings": {}}

    t0     = time.time()
    result = _agents["pricing_profit"].analyze_pricing(stock_code)
    return {
        "agent_results": {"pricing_profit": result},
        "agent_timings": {"pricing_profit": round(time.time() - t0, 2)},
    }


def product_discovery_node(state: RetailState) -> dict:
    intent       = state["intent"]
    mode         = intent.get("product_discovery_mode", "summarize")
    search_topic = intent.get("product_search_topic")

    t0    = time.time()
    agent = _agents["product_discovery"]
    result = agent.search_catalog(search_topic) if (mode == "search" and search_topic) \
             else agent.summarize_catalog()
    return {
        "agent_results": {"product_discovery": result},
        "agent_timings": {"product_discovery": round(time.time() - t0, 2)},
    }


def inventory_supply_node(state: RetailState) -> dict:
    intent     = state["intent"]
    mode       = intent.get("inventory_mode", "summarize")
    article_id = intent.get("inventory_article_id")

    t0    = time.time()
    agent = _agents["inventory_supply"]
    result = agent.analyze_article(article_id) if (mode == "search" and article_id) \
             else agent.summarize_inventory()
    return {
        "agent_results": {"inventory_supply": result},
        "agent_timings": {"inventory_supply": round(time.time() - t0, 2)},
    }


def campaign_intelligence_node(state: RetailState) -> dict:
    intent     = state["intent"]
    mode       = intent.get("campaign_mode", "summarize")
    article_id = intent.get("campaign_article_id")

    t0    = time.time()
    agent = _agents["campaign_intelligence"]
    result = agent.analyze_article(article_id) if (mode == "analyze" and article_id) \
             else agent.summarize_campaigns()
    return {
        "agent_results": {"campaign_intelligence": result},
        "agent_timings": {"campaign_intelligence": round(time.time() - t0, 2)},
    }


def synthesize_node(state: RetailState) -> dict:
    agent_results = state["agent_results"]
    query         = state["query"]

    if len(agent_results) == 1:
        name, result = next(iter(agent_results.items()))
        text = _format_single(name, result)
    elif len(agent_results) > 1:
        text = _call_synthesize(query, agent_results)
    else:
        text = "No agents produced results for this query."

    return {"synthesis": text}


# ── Synthesis helpers ─────────────────────────────────────────────────────────

def _format_single(agent_name: str, result: dict) -> str:
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


def _call_synthesize(query: str, agent_results: dict) -> str:
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
    response = _client.messages.create(
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


def stream_synthesis(query: str, agent_results: dict):
    """Yields token chunks for the UI's st.write_stream() call."""
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
    with _client.messages.stream(
        model="claude-sonnet-4-6",
        max_tokens=512,
        system=[{
            "type": "text",
            "text": _SYNTHESIS_SYSTEM,
            "cache_control": {"type": "ephemeral"},
        }],
        messages=[{"role": "user", "content": prompt}],
    ) as s:
        for chunk in s.text_stream:
            yield chunk


# ── Routing edge ──────────────────────────────────────────────────────────────
# Called by LangGraph after classify_intent_node runs.
# Returns one Send object per agent — LangGraph fans them out in parallel.

def route_to_agents(state: RetailState) -> list[Send]:
    return [
        Send(agent_name, state)
        for agent_name in state["intent"].get("agents", [])
    ]


# ── Graph definition ──────────────────────────────────────────────────────────

def build_graph():
    graph = StateGraph(RetailState)

    # Register every node
    graph.add_node("classify_intent",       classify_intent_node)
    graph.add_node("customer_voice",        customer_voice_node)
    graph.add_node("pricing_profit",        pricing_profit_node)
    graph.add_node("product_discovery",     product_discovery_node)
    graph.add_node("inventory_supply",      inventory_supply_node)
    graph.add_node("campaign_intelligence", campaign_intelligence_node)
    graph.add_node("synthesize",            synthesize_node)

    # Fixed edges — deterministic transitions
    graph.add_edge(START, "classify_intent")
    graph.add_edge("customer_voice",        "synthesize")
    graph.add_edge("pricing_profit",        "synthesize")
    graph.add_edge("product_discovery",     "synthesize")
    graph.add_edge("inventory_supply",      "synthesize")
    graph.add_edge("campaign_intelligence", "synthesize")
    graph.add_edge("synthesize",            END)

    # Conditional edge — route_to_agents inspects state after classification
    # and returns Send objects for each agent to activate in parallel
    graph.add_conditional_edges("classify_intent", route_to_agents)

    return graph.compile()


# Compiled graph — imported by the UI in Step 7
retail_graph = build_graph()
