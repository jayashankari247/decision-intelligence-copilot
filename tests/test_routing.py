"""
Routing tests — fast, no API calls.

Verifies the intent classifier correctly routes each query type
to the expected agent(s). These run in seconds and act as a
regression guard for prompt changes in intent_classifier.py.
"""
import pytest

ROUTING_CASES = [
    # (query, expected_agents_subset)
    # Customer Voice
    ("What are customers saying about our products overall?",          ["customer_voice"]),
    ("How many customers complained about petite sizing?",             ["customer_voice"]),
    # Product Discovery
    ("How many options do we have for black tops?",                    ["product_discovery"]),
    ("Do we have casual tops available across multiple colours?",      ["product_discovery"]),
    ("Give me an overall summary of our product catalog by category.", ["product_discovery"]),
    # Pricing
    ("What is the optimal price for article 0108775015?",             ["pricing_profit"]),
    # Inventory
    ("Which products are at risk of stockout and need replenishment?", ["inventory_supply"]),
    ("What is the replenishment status for article 0108775015?",       ["inventory_supply"]),
    # Campaign
    ("Which products should we consider running a promotion on?",      ["campaign_intelligence"]),
    ("Should we run a campaign or discount for article 0108775015?",   ["campaign_intelligence"]),
    # Multi-agent
    ("What do customers think about and what should we charge for article 0108775015?",
     ["customer_voice", "pricing_profit"]),
]


@pytest.mark.parametrize("query,expected", ROUTING_CASES)
def test_routing(orchestrator, query, expected):
    intent = orchestrator.classifier.classify(query)
    routed = intent.get("agents", [])
    for agent in expected:
        assert agent in routed, (
            f"Expected '{agent}' in routing for:\n  '{query}'\n  Got: {routed}"
        )


def test_intent_has_reasoning(orchestrator):
    intent = orchestrator.classifier.classify("What are customers saying overall?")
    assert intent.get("reasoning"), "Intent classifier should always return reasoning"


def test_intent_agents_is_list(orchestrator):
    intent = orchestrator.classifier.classify("What is the replenishment status for 0108775015?")
    assert isinstance(intent.get("agents"), list)
    assert len(intent["agents"]) >= 1


def test_unknown_query_returns_fallback(orchestrator):
    """A completely unrelated query should route to at least one agent, not crash."""
    intent = orchestrator.classifier.classify(
        "What is the weather like in London today?"
    )
    assert isinstance(intent.get("agents"), list)
