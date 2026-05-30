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
    return {}  # stub — wired in Step 6


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
