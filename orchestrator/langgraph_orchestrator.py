from langgraph.graph import StateGraph, START, END
from langgraph.types import Send

from orchestrator.retail_state import RetailState


AGENT_NODES = [
    "customer_voice",
    "pricing_profit",
    "product_discovery",
    "inventory_supply",
    "campaign_intelligence",
]


# ── Stub node functions ───────────────────────────────────────────────────────
# Each returns an empty dict (valid no-op state update).
# Replaced with real logic in Steps 4, 5, and 6.

def classify_intent_node(state: RetailState) -> dict:
    return {}

def customer_voice_node(state: RetailState) -> dict:
    return {}

def pricing_profit_node(state: RetailState) -> dict:
    return {}

def product_discovery_node(state: RetailState) -> dict:
    return {}

def inventory_supply_node(state: RetailState) -> dict:
    return {}

def campaign_intelligence_node(state: RetailState) -> dict:
    return {}

def synthesize_node(state: RetailState) -> dict:
    return {}


# ── Routing edge ──────────────────────────────────────────────────────────────
# Called by LangGraph after classify_intent_node runs.
# Reads the agent list from state and returns Send objects — one per agent —
# so LangGraph fans them out in parallel.
# Replaced with real logic in Step 5.

def route_to_agents(state: RetailState) -> list[Send]:
    return []  # stub — wired in Step 5


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

    # Conditional edge — route_to_agents inspects state and returns
    # which agent nodes to activate (and with what inputs) after classification
    graph.add_conditional_edges("classify_intent", route_to_agents)

    return graph.compile()


# Compiled graph — imported by the UI in Step 7
retail_graph = build_graph()
