import pytest
from agents.customer_voice.agent import CustomerVoiceAgent
from agents.customer_voice.prompts import build_user_message

agent = CustomerVoiceAgent()


def test_positive_review():
    result = agent.analyze_review("I absolutely love this dress. Perfect fit, beautiful fabric.")
    assert result is not None
    assert result["sentiment"] == "positive"
    assert result["score"] > 0


def test_negative_review():
    result = agent.analyze_review("Terrible quality. Fell apart after one wash. Complete waste of money.")
    assert result is not None
    assert result["sentiment"] == "negative"
    assert result["score"] < 0


def test_mixed_review():
    result = agent.analyze_review("Love the style but the sizing runs very small and stitching is poor.")
    assert result is not None
    assert result["sentiment"] == "mixed"
    assert len(result["positives"]) > 0
    assert len(result["negatives"]) > 0


def test_output_schema():
    result = agent.analyze_review("Nice blouse, comfortable to wear.")
    assert result is not None
    for key in ["sentiment", "score", "themes", "positives", "negatives", "unmet_needs"]:
        assert key in result


def test_empty_review_handled():
    result = agent.analyze_review("")
    assert result is None or isinstance(result, dict)


def test_build_user_message_with_all_fields():
    msg = build_user_message("Great fit!", title="Love it", department="Dresses")
    assert "Great fit!" in msg
    assert "Love it" in msg
    assert "Dresses" in msg


def test_build_user_message_without_optional_fields():
    msg = build_user_message("Great fit!")
    assert "Great fit!" in msg
    assert "Title" not in msg
    assert "Department" not in msg


def test_review_index_built():
    assert agent.embeddings.collection.count() > 0


def test_search_reviews_returns_result():
    result = agent.search_reviews("complaints about petite sizing", n_results=10)
    assert result is not None
    assert "direct_answer" in result
    assert "supporting_evidence" in result
    assert "recommendation" in result