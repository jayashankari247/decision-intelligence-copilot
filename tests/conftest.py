"""
Shared fixtures for the golden test suite.

Routing tests  — fast, no API calls, run on every commit.
Integration tests — real API calls, marked @pytest.mark.integration,
                    run with: pytest -m integration
"""
import pytest
from dotenv import load_dotenv
load_dotenv()


ARTICLE_ID = "0108775015"


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "integration: marks tests that make real API calls (deselect with -m 'not integration')"
    )


@pytest.fixture(scope="session")
def retail_graph():
    """Compiled LangGraph instance shared across the entire test session."""
    from orchestrator.langgraph_orchestrator import retail_graph as graph
    return graph


@pytest.fixture(scope="session")
def agents():
    """The five specialist agent instances, shared across the test session."""
    from orchestrator.langgraph_orchestrator import _agents
    return _agents


@pytest.fixture(scope="session")
def classifier():
    """The intent classifier instance, shared across the test session."""
    from orchestrator.langgraph_orchestrator import _classifier
    return _classifier


@pytest.fixture(scope="session")
def article_id():
    return ARTICLE_ID
