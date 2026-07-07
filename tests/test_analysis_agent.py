"""
test_analysis_agent.py – Tests for AnalysisAgent (CompanyAnalysisAgent).

Strategy
--------
AnalysisAgent is the most complex node:
  - Has before_agent_callback (_run_only_for_analysis)
  - Equipped with two MCPToolsets (Alpha Vantage, Financial Dataset)
  - Must only run for route_decision == "ANALYSIS"

MCP toolsets are patched at module import time so no real HTTP connections
are made.  We test:
  1. Callback unit tests
  2. Agent construction (with mocked toolsets)
  3. Instruction content (no-hallucination, no-advice rules)
  4. MCP toolset configuration
"""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


# ---------------------------------------------------------------------------
# Patch MCP toolset builders BEFORE the module is imported
# ---------------------------------------------------------------------------

_MOCK_AV_TOOLSET = MagicMock(name="MockAlphaVantageToolset")
_MOCK_FD_TOOLSET = MagicMock(name="MockFinancialDatasetToolset")


@pytest.fixture(scope="module", autouse=True)
def patch_mcp_toolsets():
    """
    Patch build_alpha_vantage_toolset and build_financial_dataset_toolset
    so analysis_agent.py never tries to open a real MCP connection.
    Scoped to 'module' so the patch is active for the whole file.
    """
    with patch(
        "finsight.tools.mcp_tools.build_alpha_vantage_toolset",
        return_value=_MOCK_AV_TOOLSET,
    ), patch(
        "finsight.tools.mcp_tools.build_financial_dataset_toolset",
        return_value=_MOCK_FD_TOOLSET,
    ):
        # Import AFTER patching to guarantee the module picks up mocks
        import importlib
        import finsight.agents.analysis_agent as _mod
        importlib.reload(_mod)
        yield _mod


def _import_analysis(patched_mod):
    return patched_mod.analysis_agent, patched_mod._run_only_for_analysis


# ---------------------------------------------------------------------------
# 1. Callback unit tests – _run_only_for_analysis
# ---------------------------------------------------------------------------

class TestRunOnlyForAnalysisCallback:

    def test_proceeds_for_analysis_route(self, patch_mcp_toolsets, mock_callback_context):
        """route_decision == ANALYSIS → returns None (agent runs)."""
        _, cb = _import_analysis(patch_mcp_toolsets)
        mock_callback_context.state["route_decision"] = "ANALYSIS"
        result = cb(mock_callback_context)
        assert result is None

    def test_skips_for_faq_route(self, patch_mcp_toolsets, mock_callback_context):
        """route_decision == FAQ → returns empty Content."""
        from google.genai import types
        _, cb = _import_analysis(patch_mcp_toolsets)
        mock_callback_context.state["route_decision"] = "FAQ"
        result = cb(mock_callback_context)
        assert result is not None
        assert isinstance(result, types.Content)

    def test_sets_analysis_result_empty_when_skipped(self, patch_mcp_toolsets, mock_callback_context):
        _, cb = _import_analysis(patch_mcp_toolsets)
        mock_callback_context.state["route_decision"] = "FAQ"
        cb(mock_callback_context)
        assert mock_callback_context.state.get("analysis_result") == ""

    def test_does_not_set_analysis_result_when_proceeding(self, patch_mcp_toolsets, mock_callback_context):
        _, cb = _import_analysis(patch_mcp_toolsets)
        mock_callback_context.state["route_decision"] = "ANALYSIS"
        cb(mock_callback_context)
        assert "analysis_result" not in mock_callback_context.state

    def test_skips_for_off_topic(self, patch_mcp_toolsets, mock_callback_context):
        _, cb = _import_analysis(patch_mcp_toolsets)
        mock_callback_context.state["route_decision"] = "OFF_TOPIC"
        result = cb(mock_callback_context)
        assert result is not None

    def test_skips_for_blocked(self, patch_mcp_toolsets, mock_callback_context):
        _, cb = _import_analysis(patch_mcp_toolsets)
        mock_callback_context.state["route_decision"] = "BLOCKED"
        result = cb(mock_callback_context)
        assert result is not None

    def test_skips_for_empty_state(self, patch_mcp_toolsets, mock_callback_context):
        _, cb = _import_analysis(patch_mcp_toolsets)
        result = cb(mock_callback_context)
        assert result is not None
        assert mock_callback_context.state.get("analysis_result") == ""

    def test_case_insensitive_analysis(self, patch_mcp_toolsets, mock_callback_context):
        _, cb = _import_analysis(patch_mcp_toolsets)
        mock_callback_context.state["route_decision"] = "analysis"
        result = cb(mock_callback_context)
        assert result is None


# ---------------------------------------------------------------------------
# 2. Agent construction tests
# ---------------------------------------------------------------------------

class TestAnalysisAgentConstruction:

    def test_agent_name(self, patch_mcp_toolsets):
        agent, _ = _import_analysis(patch_mcp_toolsets)
        assert agent.name == "AnalysisAgent"

    def test_output_key(self, patch_mcp_toolsets):
        agent, _ = _import_analysis(patch_mcp_toolsets)
        assert agent.output_key == "analysis_result"

    def test_model_set(self, patch_mcp_toolsets):
        agent, _ = _import_analysis(patch_mcp_toolsets)
        assert agent.model is not None

    def test_callback_registered(self, patch_mcp_toolsets):
        agent, cb = _import_analysis(patch_mcp_toolsets)
        assert agent.before_agent_callback is cb

    def test_tools_present(self, patch_mcp_toolsets):
        """AnalysisAgent must have tools (the two MCP toolsets)."""
        agent, _ = _import_analysis(patch_mcp_toolsets)
        assert agent.tools is not None
        assert len(agent.tools) >= 1


# ---------------------------------------------------------------------------
# 3. Instruction content tests
# ---------------------------------------------------------------------------

class TestAnalysisAgentInstruction:

    @pytest.fixture(autouse=True)
    def _agent(self, patch_mcp_toolsets):
        self.agent, _ = _import_analysis(patch_mcp_toolsets)

    def test_no_hallucination_rule(self):
        instr_lower = self.agent.instruction.lower()
        assert "hallucin" in instr_lower or "fabricat" in instr_lower or \
               "only use data" in instr_lower or "only data" in instr_lower

    def test_no_investment_advice_rule(self):
        instr_lower = self.agent.instruction.lower()
        assert "advice" in instr_lower or "recommendation" in instr_lower

    def test_covers_price_valuation(self):
        assert "price" in self.agent.instruction.lower() or \
               "Valuation" in self.agent.instruction

    def test_covers_income_statement(self):
        instr_lower = self.agent.instruction.lower()
        assert "revenue" in instr_lower or "income" in instr_lower

    def test_covers_balance_sheet(self):
        instr_lower = self.agent.instruction.lower()
        assert "balance sheet" in instr_lower or "assets" in instr_lower

    def test_covers_cash_flow(self):
        assert "cash flow" in self.agent.instruction.lower()

    def test_mentions_mcp_tools(self):
        instr_lower = self.agent.instruction.lower()
        assert "tool" in instr_lower or "mcp" in instr_lower

    def test_strict_rules_section(self):
        assert "STRICT" in self.agent.instruction or "RULES" in self.agent.instruction


# ---------------------------------------------------------------------------
# 4. MCP toolset configuration tests
# ---------------------------------------------------------------------------

class TestAnalysisMCPToolsets:

    def test_alpha_vantage_toolset_used(self, patch_mcp_toolsets):
        """The module-level toolset must be the mocked Alpha Vantage one."""
        assert patch_mcp_toolsets._alpha_vantage_tools is _MOCK_AV_TOOLSET

    def test_financial_dataset_toolset_used(self, patch_mcp_toolsets):
        assert patch_mcp_toolsets._financial_dataset_tools is _MOCK_FD_TOOLSET

    def test_both_toolsets_attached_to_agent(self, patch_mcp_toolsets):
        agent, _ = _import_analysis(patch_mcp_toolsets)
        tools = agent.tools
        assert _MOCK_AV_TOOLSET in tools
        assert _MOCK_FD_TOOLSET in tools


# ---------------------------------------------------------------------------
# 5. Parametrized route skip scenarios
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("route,should_skip", [
    ("ANALYSIS",  False),
    ("FAQ",       True),
    ("OFF_TOPIC", True),
    ("BLOCKED",   True),
    ("",          True),
    ("analysis",  False),  # case-insensitive
    ("faq",       True),
])
def test_analysis_callback_parametrized(route, should_skip, patch_mcp_toolsets, mock_callback_context):
    _, cb = _import_analysis(patch_mcp_toolsets)
    mock_callback_context.state["route_decision"] = route
    result = cb(mock_callback_context)
    if should_skip:
        assert result is not None, f"Expected skip for route={route!r}"
    else:
        assert result is None, f"Expected proceed for route={route!r}"
