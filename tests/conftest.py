"""
conftest.py – Shared fixtures and environment setup for FinSight AI pytest suite.

Sets up the minimum environment variables required so that finsight.config
can be imported without raising EnvironmentError, and patches MCP toolsets
so no real network connections are made during any test.
"""

import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ── Make sure the project root is on sys.path ────────────────────────────────
_PROJECT_ROOT = Path(__file__).parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


# ── Inject stub environment variables before any finsight import ─────────────
def pytest_configure(config):
    """Called by pytest before collection. Set env vars early."""
    os.environ.setdefault("GEMINI_API_KEY", "test-gemini-key")
    os.environ.setdefault("GOOGLE_API_KEY", "test-gemini-key")
    os.environ.setdefault("ALPHA_VANTAGE", "test-av-key")
    os.environ.setdefault("FINANCIAL_DATASET", "test-fd-key")
    os.environ.setdefault("GEMINI_MODEL", "gemini-2.0-flash")
    os.environ.setdefault("REDIS_URL", "redis://localhost:6379")


# ── Shared MCP mock fixture ───────────────────────────────────────────────────

def _make_mock_toolset(tool_names: list) -> MagicMock:
    """Return a MagicMock that looks like an MCPToolset."""
    toolset = MagicMock()
    toolset.__aenter__ = AsyncMock(return_value=toolset)
    toolset.__aexit__ = AsyncMock(return_value=False)
    toolset.get_tools = AsyncMock(return_value=[])
    return toolset


@pytest.fixture(scope="session")
def mock_alpha_vantage_toolset():
    return _make_mock_toolset(["get_stock_price", "get_company_overview"])


@pytest.fixture(scope="session")
def mock_financial_dataset_toolset():
    return _make_mock_toolset([
        "get_income_statements",
        "get_balance_sheets",
        "get_cash_flow_statements",
        "get_financial_metrics",
        "get_earnings",
    ])


# ── ADK callback context mock ─────────────────────────────────────────────────

@pytest.fixture
def mock_callback_context():
    """
    Return a lightweight mock that mimics ADK's CallbackContext.
    Tests can pre-populate .state and read it back after the callback runs.
    """
    ctx = MagicMock()
    ctx.state = {}
    return ctx
