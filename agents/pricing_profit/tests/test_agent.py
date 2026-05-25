import pytest
from agents.pricing_profit.agent import PricingProfitAgent
from agents.pricing_profit.prompts import build_user_message

agent = PricingProfitAgent()
TEST_ARTICLE_ID = "0108775015"


def test_price_data_loads():
    data = agent._load_price_data(max_rows=50000)
    assert len(data) > 0, "Should load price data from transactions"


def test_known_article_returns_result():
    result = agent.analyze_pricing(TEST_ARTICLE_ID)
    assert result is not None, f"Should return a result for article {TEST_ARTICLE_ID}"


def test_output_schema():
    result = agent.analyze_pricing(TEST_ARTICLE_ID)
    assert result is not None
    for key in ["price_elasticity", "recommended_price", "revenue_scenarios",
                "confidence", "recommendation_rationale"]:
        assert key in result, f"Missing key: {key}"


def test_revenue_scenarios_have_three_entries():
    result = agent.analyze_pricing(TEST_ARTICLE_ID)
    assert result is not None
    assert len(result["revenue_scenarios"]) == 3


def test_invalid_article_returns_none():
    result = agent.analyze_pricing("9999999999")
    assert result is None, "Unknown article_id should return None"


def test_aggregation_has_positive_prices():
    summary = agent.aggregate_product_data(TEST_ARTICLE_ID)
    assert summary is not None, "Should find price data for known article"
    for entry in summary["price_points"]:
        assert entry["transactions"] > 0
        assert entry["price"] > 0


def test_build_user_message_contains_article():
    price_summary = {
        "price_points": [
            {"price": 0.0508, "transactions": 42, "total_revenue": 2.1336}
        ]
    }
    msg = build_user_message(TEST_ARTICLE_ID, "Strap top", price_summary)
    assert TEST_ARTICLE_ID in msg
    assert "Strap top" in msg
    assert "0.0508" in msg
