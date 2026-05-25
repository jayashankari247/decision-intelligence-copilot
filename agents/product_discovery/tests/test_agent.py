import pytest
from agents.product_discovery.agent import ProductDiscoveryAgent
from agents.product_discovery.prompts import build_product_text

agent = ProductDiscoveryAgent()


def test_index_built():
    assert agent.embeddings.collection.count() > 0


def test_find_similar_returns_results():
    results = agent.find_similar_products("black casual top", n_results=3)
    assert len(results) == 3


def test_find_similar_result_schema():
    results = agent.find_similar_products("summer dress")
    for r in results:
        assert "article_id" in r
        assert "metadata" in r
        assert "distance" in r


def test_analyze_product_returns_result():
    results = agent.embeddings.collection.get(limit=1)
    article_id = results["ids"][0]
    result = agent.analyze_product(article_id)
    assert result is not None


def test_analyze_product_schema():
    results = agent.embeddings.collection.get(limit=1)
    article_id = results["ids"][0]
    result = agent.analyze_product(article_id)
    assert result is not None
    for key in ["product_name", "category", "style_attributes", "occasion"]:
        assert key in result


def test_discover_trends_returns_result():
    result = agent.discover_trends("Garment Upper body")
    assert result is not None
    assert "trend_summary" in result


def test_build_product_text():
    row = {
        "prod_name": "Strap top",
        "product_type_name": "Vest top",
        "colour_group_name": "Black",
        "detail_desc": "Jersey top with narrow straps"
    }
    text = build_product_text(row)
    assert "Strap top" in text
    assert "Black" in text


def test_image_path_construction():
    path = agent.embeddings.get_image_path("0108775015")
    assert path is None or path.endswith(".jpg")
