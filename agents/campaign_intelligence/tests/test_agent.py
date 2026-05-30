import csv
import pytest
from agents.campaign_intelligence.trend_analyzer import DemandTrendAnalyzer
from agents.campaign_intelligence.agent import CampaignIntelligenceAgent

TRANSACTIONS_FILE = "data/product_discovery/transactions_train.csv"
SNAPSHOT_FILE = "data/inventory_supply/inventory_snapshot.csv"


# --- Trend analyzer unit tests ---

def test_trend_analyzer_loads_data():
    analyzer = DemandTrendAnalyzer(TRANSACTIONS_FILE, max_rows=5000)
    trends = analyzer._load_trends_csv()
    assert len(trends) > 0, "Should compute trends for at least one article"


def test_trend_values_are_valid():
    analyzer = DemandTrendAnalyzer(TRANSACTIONS_FILE, max_rows=5000)
    trends = analyzer._load_trends_csv()
    valid_trends = {"DECLINING", "STABLE", "GROWING"}
    for article_id, data in list(trends.items())[:20]:
        assert data["trend"] in valid_trends, f"Invalid trend '{data['trend']}' for {article_id}"


def test_trend_cache_is_reused():
    analyzer = DemandTrendAnalyzer(TRANSACTIONS_FILE, max_rows=5000)
    trends1 = analyzer._load_trends_csv()
    trends2 = analyzer._load_trends_csv()
    assert trends1 is trends2, "Second call should return the cached result"


def test_promotion_candidates_returns_list():
    analyzer = DemandTrendAnalyzer(TRANSACTIONS_FILE, max_rows=5000)
    with open(SNAPSHOT_FILE, newline="", encoding="utf-8") as f:
        snapshot = list(csv.DictReader(f))
    candidates = analyzer.get_promotion_candidates(snapshot, top_n=10)
    assert isinstance(candidates, list), "Should return a list"


def test_promotion_candidates_have_urgency():
    analyzer = DemandTrendAnalyzer(TRANSACTIONS_FILE, max_rows=5000)
    with open(SNAPSHOT_FILE, newline="", encoding="utf-8") as f:
        snapshot = list(csv.DictReader(f))
    candidates = analyzer.get_promotion_candidates(snapshot, top_n=10)
    for c in candidates:
        assert c["urgency"] in {"HIGH", "MEDIUM"}, f"Invalid urgency: {c['urgency']}"


# --- Agent integration tests ---

def test_agent_analyze_article_returns_dict():
    agent = CampaignIntelligenceAgent()
    with open(SNAPSHOT_FILE, newline="", encoding="utf-8") as f:
        first_row = next(csv.DictReader(f))
    result = agent.analyze_article(first_row["article_id"])
    assert result is not None, "analyze_article should return a result"
    assert isinstance(result, dict), "Result should be a dictionary"


def test_agent_analyze_article_has_recommendation():
    agent = CampaignIntelligenceAgent()
    with open(SNAPSHOT_FILE, newline="", encoding="utf-8") as f:
        first_row = next(csv.DictReader(f))
    result = agent.analyze_article(first_row["article_id"])
    assert result is not None
    assert "promotion_recommendation" in result
    assert result["promotion_recommendation"] in {"PROMOTE_NOW", "MONITOR", "HOLD"}


def test_agent_analyze_article_has_campaign_type():
    agent = CampaignIntelligenceAgent()
    with open(SNAPSHOT_FILE, newline="", encoding="utf-8") as f:
        first_row = next(csv.DictReader(f))
    result = agent.analyze_article(first_row["article_id"])
    assert result is not None
    valid_types = {"PRICE_DISCOUNT", "BUNDLE", "SEASONAL_CLEARANCE", "LOYALTY_OFFER", "NONE"}
    assert result.get("campaign_type") in valid_types


def test_agent_summarize_campaigns_returns_dict():
    agent = CampaignIntelligenceAgent()
    result = agent.summarize_campaigns()
    assert result is not None, "summarize_campaigns should return a result"
    assert isinstance(result, dict), "Result should be a dictionary"


def test_agent_summarize_has_executive_summary():
    agent = CampaignIntelligenceAgent()
    result = agent.summarize_campaigns()
    assert result is not None
    assert "executive_summary" in result
    assert len(result["executive_summary"]) > 10


def test_agent_unknown_article_returns_none():
    agent = CampaignIntelligenceAgent()
    result = agent.analyze_article("9999999999")
    assert result is None, "Unknown article_id should return None"
