import pytest
import csv
import os
from unittest.mock import patch, MagicMock
from agents.inventory_supply.forecaster import DemandForecaster
from agents.inventory_supply.agent import InventorySupplyAgent

SNAPSHOT_FILE = "data/inventory_supply/inventory_snapshot.csv"
TRANSACTIONS_FILE = "data/product_discovery/transactions_train.csv"


# --- Forecaster unit tests ---

def test_forecaster_loads_demand():
    forecaster = DemandForecaster(TRANSACTIONS_FILE, max_rows=5000)
    demand = forecaster._load_demand_csv()
    assert len(demand) > 0, "Should load demand data from transactions"


def test_forecaster_daily_rate_is_positive():
    forecaster = DemandForecaster(TRANSACTIONS_FILE, max_rows=5000)
    demand = forecaster._load_demand_csv()
    for article_id, metrics in list(demand.items())[:10]:
        assert metrics["daily_demand_rate"] > 0, f"Daily rate should be positive for {article_id}"


def test_forecaster_cache_is_reused():
    forecaster = DemandForecaster(TRANSACTIONS_FILE, max_rows=5000)
    demand1 = forecaster._load_demand_csv()
    demand2 = forecaster._load_demand_csv()
    assert demand1 is demand2, "Second call should return cached result"


# --- Inventory snapshot tests ---

def test_snapshot_file_exists():
    assert os.path.exists(SNAPSHOT_FILE), f"Inventory snapshot not found at {SNAPSHOT_FILE}"


def test_snapshot_has_required_columns():
    with open(SNAPSHOT_FILE, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames
    required = ["article_id", "current_stock", "reorder_point", "lead_time_days", "warehouse"]
    for col in required:
        assert col in headers, f"Missing column: {col}"


def test_snapshot_has_rows():
    with open(SNAPSHOT_FILE, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) > 0, "Snapshot file should have data rows"


# --- Agent integration tests ---

def test_agent_analyze_article_returns_dict():
    agent = InventorySupplyAgent()
    with open(SNAPSHOT_FILE, newline="", encoding="utf-8") as f:
        first_row = next(csv.DictReader(f))
    article_id = first_row["article_id"]
    result = agent.analyze_article(article_id)
    assert result is not None, "analyze_article should return a result"
    assert isinstance(result, dict), "Result should be a dictionary"


def test_agent_analyze_article_has_status():
    agent = InventorySupplyAgent()
    with open(SNAPSHOT_FILE, newline="", encoding="utf-8") as f:
        first_row = next(csv.DictReader(f))
    result = agent.analyze_article(first_row["article_id"])
    assert result is not None
    assert "replenishment_status" in result, "Result should contain replenishment_status"
    assert result["replenishment_status"] in ["CRITICAL", "AT_RISK", "HEALTHY"]


def test_agent_summarize_inventory_returns_dict():
    agent = InventorySupplyAgent()
    result = agent.summarize_inventory()
    assert result is not None, "summarize_inventory should return a result"
    assert isinstance(result, dict), "Result should be a dictionary"


def test_agent_summarize_has_executive_summary():
    agent = InventorySupplyAgent()
    result = agent.summarize_inventory()
    assert result is not None
    assert "executive_summary" in result, "Summary result should contain executive_summary"
    assert len(result["executive_summary"]) > 10, "Executive summary should have content"


def test_agent_unknown_article_returns_none():
    agent = InventorySupplyAgent()
    result = agent.analyze_article("9999999999")
    assert result is None, "Unknown article_id should return None"
