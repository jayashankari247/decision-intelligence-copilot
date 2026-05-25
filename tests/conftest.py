"""
Shared fixtures for the golden test suite.

Routing tests  — fast, no API calls, run on every commit.
Integration tests — real API calls, marked @pytest.mark.integration,
                    run with: pytest -m integration
"""
import pytest
from orchestrator.orchestrator import Orchestrator

ARTICLE_ID = "0108775015"


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "integration: marks tests that make real API calls (deselect with -m 'not integration')"
    )


@pytest.fixture(scope="session")
def orchestrator():
    """Single orchestrator instance shared across the entire test session."""
    return Orchestrator()


@pytest.fixture(scope="session")
def article_id():
    return ARTICLE_ID
