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
def test_pricing_schema(orchestrator, article_id):
    result = orchestrator.agents["pricing_profit"].analyze_pricing(article_id)
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
def test_inventory_article_schema(orchestrator, article_id):
    result = orchestrator.agents["inventory_supply"].analyze_article(article_id)
    assert result is not None, f"Inventory article returned None for {article_id}"
    validated = InventoryArticleOutput.model_validate(result)
    assert validated.replenishment_status in ("CRITICAL", "AT_RISK", "HEALTHY")
    assert validated.days_until_stockout >= 0
    assert validated.recommended_order_quantity >= 0
    assert validated.confidence in ("low", "medium", "high")


@pytest.mark.integration
def test_inventory_summary_schema(orchestrator):
    result = orchestrator.agents["inventory_supply"].summarize_inventory()
    assert result is not None, "Inventory summary returned None"
    validated = InventorySummaryOutput.model_validate(result)
    assert validated.critical_count >= 0
    assert validated.projected_stockout_this_week >= 0
    assert len(validated.executive_summary) > 20


# ── Campaign ───────────────────────────────────────────────────────────────────

@pytest.mark.integration
def test_campaign_article_schema(orchestrator, article_id):
    result = orchestrator.agents["campaign_intelligence"].analyze_article(article_id)
    assert result is not None, f"Campaign article returned None for {article_id}"
    validated = CampaignArticleOutput.model_validate(result)
    assert validated.promotion_recommendation in ("PROMOTE_NOW", "MONITOR", "HOLD")
    assert validated.campaign_type in (
        "PRICE_DISCOUNT", "BUNDLE", "SEASONAL_CLEARANCE", "LOYALTY_OFFER", "NONE"
    )
    assert 0 <= validated.suggested_discount_pct <= 70


@pytest.mark.integration
def test_campaign_summary_schema(orchestrator):
    result = orchestrator.agents["campaign_intelligence"].summarize_campaigns()
    assert result is not None, "Campaign summary returned None"
    validated = CampaignSummaryOutput.model_validate(result)
    assert validated.high_urgency_count >= 0
    assert len(validated.executive_summary) > 20


# ── Customer Voice ─────────────────────────────────────────────────────────────

@pytest.mark.integration
def test_customer_voice_search_schema(orchestrator):
    result = orchestrator.agents["customer_voice"].search_reviews(
        "customers complaining about sizing"
    )
    assert result is not None, "Customer voice search returned None"
    validated = CustomerVoiceSearchOutput.model_validate(result)
    assert len(validated.direct_answer) > 10
    assert validated.sentiment in ("positive", "negative", "mixed")


@pytest.mark.integration
def test_customer_voice_summary_schema(orchestrator):
    reviews = orchestrator.agents["customer_voice"].analyze_from_csv(max_reviews=5)
    result  = orchestrator.agents["customer_voice"].summarize_results(reviews)
    assert result is not None, "Customer voice summary returned None"
    validated = CustomerVoiceSummaryOutput.model_validate(result)
    assert validated.total_reviews > 0
    assert len(validated.top_themes) > 0
    assert len(validated.executive_summary) > 20


# ── Product Discovery ──────────────────────────────────────────────────────────

@pytest.mark.integration
def test_product_discovery_search_schema(orchestrator):
    result = orchestrator.agents["product_discovery"].search_catalog("black tops")
    assert result is not None, "Product discovery search returned None"
    validated = ProductDiscoverySearchOutput.model_validate(result)
    assert len(validated.direct_answer) > 10


@pytest.mark.integration
def test_product_discovery_summary_schema(orchestrator):
    result = orchestrator.agents["product_discovery"].summarize_catalog()
    assert result is not None, "Product discovery summary returned None"
    validated = ProductDiscoverySummaryOutput.model_validate(result)
    assert len(validated.executive_summary) > 20


# ── Orchestrator end-to-end ────────────────────────────────────────────────────

@pytest.mark.integration
def test_single_agent_pipeline(orchestrator, article_id):
    """Full run() call for a single-agent query — checks formatted output is non-empty."""
    result = orchestrator.run(f"What is the replenishment status for article {article_id}?")
    assert result["agent_results"].get("inventory_supply") is not None
    assert len(result["formatted"]) > 20
    assert result["total_latency_sec"] > 0


@pytest.mark.integration
def test_multi_agent_pipeline(orchestrator, article_id):
    """Full run() call for a multi-agent query — both agents return results."""
    result = orchestrator.run(
        f"What do customers think about and what should we charge for article {article_id}?"
    )
    ar = result["agent_results"]
    assert ar.get("customer_voice") is not None, "customer_voice agent returned None"
    assert ar.get("pricing_profit") is not None, "pricing_profit agent returned None"
    assert result["total_latency_sec"] > 0


@pytest.mark.integration
def test_logger_writes_entry(orchestrator, tmp_path, monkeypatch):
    """After a run(), a log entry should exist in the log file."""
    from shared.logger import AgentLogger
    log_path = tmp_path / "logs"
    monkeypatch.setattr(orchestrator, "logger", AgentLogger(log_dir=str(log_path)))
    orchestrator.run("What is the optimal price for article 0108775015?")
    entries = AgentLogger(log_dir=str(log_path)).read_recent(n=1)
    assert len(entries) == 1
    assert entries[0]["success"] is True
    assert "pricing_profit" in entries[0]["agents_called"]
