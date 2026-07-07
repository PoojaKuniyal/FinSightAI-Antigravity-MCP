"""
test_faq_agent.py – Tests for FAQAgent.

Strategy
--------
FAQAgent has one before_agent_callback: _run_only_for_faq.
It skips (returns empty Content) when route_decision != "FAQ".
It proceeds (returns None) when route_decision == "FAQ".

Test levels:
  1. Unit – callback logic directly
  2. Unit – agent construction
  3. Unit – instruction content (educational boundaries)
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _import_faq():
    from finsight.agents.faq_agent import faq_agent, _run_only_for_faq
    return faq_agent, _run_only_for_faq


# ---------------------------------------------------------------------------
# 1. Callback unit tests – _run_only_for_faq
# ---------------------------------------------------------------------------

class TestRunOnlyForFaqCallback:

    def test_returns_none_for_faq_route(self, mock_callback_context):
        """route_decision == FAQ → callback returns None (agent runs)."""
        _, cb = _import_faq()
        mock_callback_context.state["route_decision"] = "FAQ"
        result = cb(mock_callback_context)
        assert result is None

    def test_skips_for_analysis_route(self, mock_callback_context):
        """route_decision == ANALYSIS → callback short-circuits with empty Content."""
        from google.genai import types
        _, cb = _import_faq()
        mock_callback_context.state["route_decision"] = "ANALYSIS"
        result = cb(mock_callback_context)
        assert result is not None
        assert isinstance(result, types.Content)

    def test_skips_for_off_topic_route(self, mock_callback_context):
        _, cb = _import_faq()
        mock_callback_context.state["route_decision"] = "OFF_TOPIC"
        result = cb(mock_callback_context)
        assert result is not None

    def test_skips_for_blocked_route(self, mock_callback_context):
        _, cb = _import_faq()
        mock_callback_context.state["route_decision"] = "BLOCKED"
        result = cb(mock_callback_context)
        assert result is not None

    def test_sets_faq_result_empty_when_skipped(self, mock_callback_context):
        """When skipped, faq_result must be written as empty string."""
        _, cb = _import_faq()
        mock_callback_context.state["route_decision"] = "ANALYSIS"
        cb(mock_callback_context)
        assert mock_callback_context.state.get("faq_result") == ""

    def test_does_not_set_faq_result_when_proceeding(self, mock_callback_context):
        """When proceeding (FAQ route), callback should NOT overwrite faq_result."""
        _, cb = _import_faq()
        mock_callback_context.state["route_decision"] = "FAQ"
        cb(mock_callback_context)
        # faq_result should NOT be touched by the callback (LLM sets it later)
        assert "faq_result" not in mock_callback_context.state

    def test_case_insensitive_faq_route(self, mock_callback_context):
        """Mixed-case 'faq' should still be treated as FAQ."""
        _, cb = _import_faq()
        mock_callback_context.state["route_decision"] = "faq"
        result = cb(mock_callback_context)
        assert result is None

    def test_empty_route_skips(self, mock_callback_context):
        """No route_decision in state → skip (safe default)."""
        _, cb = _import_faq()
        # state is empty — no route_decision
        result = cb(mock_callback_context)
        assert result is not None
        assert mock_callback_context.state.get("faq_result") == ""


# ---------------------------------------------------------------------------
# 2. Agent construction tests
# ---------------------------------------------------------------------------

class TestFaqAgentConstruction:

    def test_agent_name(self):
        agent, _ = _import_faq()
        assert agent.name == "FAQAgent"

    def test_output_key(self):
        agent, _ = _import_faq()
        assert agent.output_key == "faq_result"

    def test_model_set(self):
        agent, _ = _import_faq()
        assert agent.model is not None

    def test_callback_registered(self):
        agent, _run_only_for_faq = _import_faq()
        assert agent.before_agent_callback is _run_only_for_faq

    def test_no_tools(self):
        """FAQ agent must have no MCP or external tools."""
        agent, _ = _import_faq()
        assert not agent.tools


# ---------------------------------------------------------------------------
# 3. Instruction content tests
# ---------------------------------------------------------------------------

class TestFaqAgentInstruction:

    @pytest.fixture(autouse=True)
    def _agent(self):
        self.agent, _ = _import_faq()

    def test_covers_pe_ratio(self):
        assert "P/E" in self.agent.instruction or "P/E Ratio" in self.agent.instruction

    def test_covers_eps(self):
        assert "EPS" in self.agent.instruction

    def test_covers_ebitda(self):
        assert "EBITDA" in self.agent.instruction

    def test_covers_roe(self):
        assert "ROE" in self.agent.instruction

    def test_covers_market_cap(self):
        assert "market cap" in self.agent.instruction.lower() or \
               "Market Cap" in self.agent.instruction

    def test_no_investment_advice(self):
        assert "advice" in self.agent.instruction.lower() or \
               "recommendation" in self.agent.instruction.lower()

    def test_warns_against_fabricating_company_numbers(self):
        """FAQ agent should refuse to fabricate live company data."""
        instr_lower = self.agent.instruction.lower()
        assert "fabricate" in instr_lower or \
               "hallucin" in instr_lower or \
               "do not" in instr_lower or \
               "never" in instr_lower

    def test_boundary_note_for_live_company_data(self):
        """Instruction must tell the agent to redirect company-specific queries."""
        assert "live" in self.agent.instruction.lower() or \
               "current" in self.agent.instruction.lower() or \
               "Analyse" in self.agent.instruction


# ---------------------------------------------------------------------------
# 4. Parametrized route skip scenarios
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("route,should_skip", [
    ("FAQ",       False),
    ("ANALYSIS",  True),
    ("OFF_TOPIC", True),
    ("BLOCKED",   True),
    ("",          True),
    ("faq",       False),   # case-insensitive
    ("analysis",  True),    # case-insensitive
])
def test_faq_callback_parametrized(route, should_skip, mock_callback_context):
    """Table-driven tests for all routing outcomes."""
    _, cb = _import_faq()
    mock_callback_context.state["route_decision"] = route
    result = cb(mock_callback_context)
    if should_skip:
        assert result is not None, f"Expected skip for route={route!r}"
    else:
        assert result is None, f"Expected proceed for route={route!r}"
