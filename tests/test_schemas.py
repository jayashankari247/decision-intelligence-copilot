"""
Schema integration tests — makes real API calls.

Run with: pytest -m integration
Skip with: pytest -m "not integration"

Each test verifies that a known query returns a result whose
structure matches the Pydantic schema defined in shared/schemas.py.
This catches regressions where a prompt change causes Claude to
return fields with wrong names or missing required keys.
"""
import pytest
from shared.schemas import (
    PricingOutput,
    InventoryArticleOutput,
    InventorySummaryOutput,
    CampaignArticleOutput,
    CampaignSummaryOutput,
    CustomerVoiceSearchOutput,
    CustomerVoiceSummaryOutput,
    ProductDiscoverySearchOutput,
    ProductDiscoverySummaryOutput,
)


# ── Pricing ────────────────────────────────────────────────────────────────────

@pytest.mark.integration
def test_pricing_schema(agents, article_id):
    result = agents["pricing_profit"].analyze_pricing(article_id)
    assert result is not None, f"Pricing returned None for {article_id}"
    validated = PricingOutput.model_validate(result)
    assert validated.price_elasticity in ("elastic", "inelastic", "mixed")
    assert validated.confidence in ("low", "medium", "high")
    assert len(validated.revenue_scenarios) == 3
    assert validated.recommended_price > 0
    labels = [s.label for s in validated.revenue_scenarios]
    assert set(labels) == {"discount", "current", "premium"}


# ── Inventory ──────────────────────────────────────────────────────────────────

@pytest.mark.integration
def test_inventory_article_schema(agents, article_id):
    result = agents["inventory_supply"].analyze_article(article_id)
    assert result is not None, f"Inventory article returned None for {article_id}"
    validated = InventoryArticleOutput.model_validate(result)
    assert validated.replenishment_status in ("CRITICAL", "AT_RISK", "HEALTHY")
    assert validated.days_until_stockout >= 0
    assert validated.recommended_order_quantity >= 0
    assert validated.confidence in ("low", "medium", "high")


@pytest.mark.integration
def test_inventory_summary_schema(agents):
    result = agents["inventory_supply"].summarize_inventory()
    assert result is not None, "Inventory summary returned None"
    validated = InventorySummaryOutput.model_validate(result)
    assert validated.critical_count >= 0
    assert validated.projected_stockout_this_week >= 0
    assert len(validated.executive_summary) > 20


# ── Campaign ───────────────────────────────────────────────────────────────────

@pytest.mark.integration
def test_campaign_article_schema(agents, article_id):
    result = agents["campaign_intelligence"].analyze_article(article_id)
    assert result is not None, f"Campaign article returned None for {article_id}"
    validated = CampaignArticleOutput.model_validate(result)
    assert validated.promotion_recommendation in ("PROMOTE_NOW", "MONITOR", "HOLD")
    assert validated.campaign_type in (
        "PRICE_DISCOUNT", "BUNDLE", "SEASONAL_CLEARANCE", "LOYALTY_OFFER", "NONE"
    )
    assert 0 <= validated.suggested_discount_pct <= 70


@pytest.mark.integration
def test_campaign_summary_schema(agents):
    result = agents["campaign_intelligence"].summarize_campaigns()
    assert result is not None, "Campaign summary returned None"
    validated = CampaignSummaryOutput.model_validate(result)
    assert validated.high_urgency_count >= 0
    assert len(validated.executive_summary) > 20


# ── Customer Voice ─────────────────────────────────────────────────────────────

@pytest.mark.integration
def test_customer_voice_search_schema(agents):
    result = agents["customer_voice"].search_reviews(
        "customers complaining about sizing"
    )
    assert result is not None, "Customer voice search returned None"
    validated = CustomerVoiceSearchOutput.model_validate(result)
    assert len(validated.direct_answer) > 10
    assert validated.sentiment in ("positive", "negative", "mixed")


@pytest.mark.integration
def test_customer_voice_summary_schema(agents):
    reviews = agents["customer_voice"].analyze_from_csv(max_reviews=5)
    result  = agents["customer_voice"].summarize_results(reviews)
    assert result is not None, "Customer voice summary returned None"
    validated = CustomerVoiceSummaryOutput.model_validate(result)
    assert validated.total_reviews > 0
    assert len(validated.top_themes) > 0
    assert len(validated.executive_summary) > 20


# ── Product Discovery ──────────────────────────────────────────────────────────

@pytest.mark.integration
def test_product_discovery_search_schema(agents):
    result = agents["product_discovery"].search_catalog("black tops")
    assert result is not None, "Product discovery search returned None"
    validated = ProductDiscoverySearchOutput.model_validate(result)
    assert len(validated.direct_answer) > 10


@pytest.mark.integration
def test_product_discovery_summary_schema(agents):
    result = agents["product_discovery"].summarize_catalog()
    assert result is not None, "Product discovery summary returned None"
    validated = ProductDiscoverySummaryOutput.model_validate(result)
    assert len(validated.executive_summary) > 20


# ── LangGraph end-to-end ───────────────────────────────────────────────────────

@pytest.mark.integration
def test_single_agent_pipeline(retail_graph, article_id):
    """Single-agent query via retail_graph.invoke() — checks state fields are populated."""
    state = retail_graph.invoke(
        {"query": f"What is the replenishment status for article {article_id}?"}
    )
    assert state["agent_results"].get("inventory_supply") is not None
    assert len(state["synthesis"]) > 20


@pytest.mark.integration
def test_multi_agent_pipeline(retail_graph, article_id):
    """Multi-agent query via retail_graph.invoke() — both agents return results."""
    state = retail_graph.invoke(
        {"query": f"What do customers think about and what should we charge for article {article_id}?"}
    )
    ar = state["agent_results"]
    assert ar.get("customer_voice") is not None, "customer_voice agent returned None"
    assert ar.get("pricing_profit") is not None, "pricing_profit agent returned None"
    assert len(state["synthesis"]) > 20


@pytest.mark.integration
def test_logger_writes_entry(retail_graph, tmp_path, monkeypatch):
    """After graph.invoke(), a log entry should exist in the log file."""
    import orchestrator.langgraph_orchestrator as orch_module
    from shared.logger import AgentLogger
    log_path = tmp_path / "logs"
    monkeypatch.setattr(orch_module, "_logger", AgentLogger(log_dir=str(log_path)))
    retail_graph.invoke({"query": "What is the optimal price for article 0108775015?"})
    entries = AgentLogger(log_dir=str(log_path)).read_recent(n=1)
    assert len(entries) == 1
    assert entries[0]["success"] is True
    assert "pricing_profit" in entries[0]["agents_called"]
