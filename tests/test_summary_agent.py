"""
test_summary_agent.py – Tests for SummaryAgent.

Strategy
--------
SummaryAgent has a before_agent_callback (_handle_special_routes) that:
  - Returns a pre-built BLOCKED response when guardrail says BLOCKED
  - Returns a pre-built OFF_TOPIC response when route_decision is OFF_TOPIC
  - Returns None (proceeds to LLM) for normal FAQ / ANALYSIS routes

We test:
  1. Callback unit tests for all special routes
  2. Agent construction
  3. Pre-built response content
  4. Instruction content
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _import_summary():
    from finsight.agents.summary_agent import (
        summary_agent,
        _handle_special_routes,
        _BLOCKED_RESPONSE,
        _OFF_TOPIC_RESPONSE,
    )
    return summary_agent, _handle_special_routes, _BLOCKED_RESPONSE, _OFF_TOPIC_RESPONSE


# ---------------------------------------------------------------------------
# 1. Callback unit tests – _handle_special_routes
# ---------------------------------------------------------------------------

class TestHandleSpecialRoutesCallback:

    # ── BLOCKED path ─────────────────────────────────────────────────────────

    def test_returns_blocked_response_when_guardrail_blocked(self, mock_callback_context):
        _, cb, blocked_resp, _ = _import_summary()
        mock_callback_context.state["guardrail_result"] = "BLOCKED"
        mock_callback_context.state["route_decision"] = ""
        result = cb(mock_callback_context)
        assert result is not None

    def test_sets_final_response_state_when_blocked(self, mock_callback_context):
        _, cb, blocked_resp, _ = _import_summary()
        mock_callback_context.state["guardrail_result"] = "BLOCKED"
        mock_callback_context.state["route_decision"] = ""
        cb(mock_callback_context)
        assert mock_callback_context.state.get("final_response") != ""

    def test_blocked_via_route_decision(self, mock_callback_context):
        """route_decision == BLOCKED (set by router skip callback) also short-circuits."""
        _, cb, _, _ = _import_summary()
        mock_callback_context.state["guardrail_result"] = "SAFE"
        mock_callback_context.state["route_decision"] = "BLOCKED"
        result = cb(mock_callback_context)
        assert result is not None

    def test_blocked_response_contains_safety_message(self, mock_callback_context):
        _, cb, _, _ = _import_summary()
        mock_callback_context.state["guardrail_result"] = "BLOCKED"
        mock_callback_context.state["route_decision"] = ""
        result = cb(mock_callback_context)
        text = result.parts[0].text if result and result.parts else ""
        assert "block" in text.lower() or "guardrail" in text.lower() or "⚠️" in text

    # ── OFF_TOPIC path ────────────────────────────────────────────────────────

    def test_returns_off_topic_response(self, mock_callback_context):
        _, cb, _, _ = _import_summary()
        mock_callback_context.state["guardrail_result"] = "SAFE"
        mock_callback_context.state["route_decision"] = "OFF_TOPIC"
        result = cb(mock_callback_context)
        assert result is not None

    def test_off_topic_response_text_is_helpful(self, mock_callback_context):
        _, cb, _, _ = _import_summary()
        mock_callback_context.state["guardrail_result"] = "SAFE"
        mock_callback_context.state["route_decision"] = "OFF_TOPIC"
        result = cb(mock_callback_context)
        text = result.parts[0].text if result and result.parts else ""
        assert "finance" in text.lower() or "financial" in text.lower() or "stock" in text.lower()

    def test_off_topic_sets_final_response_state(self, mock_callback_context):
        _, cb, _, _ = _import_summary()
        mock_callback_context.state["guardrail_result"] = "SAFE"
        mock_callback_context.state["route_decision"] = "OFF_TOPIC"
        cb(mock_callback_context)
        assert mock_callback_context.state.get("final_response") != ""

    # ── Normal paths (FAQ / ANALYSIS) → proceed to LLM ───────────────────────

    def test_proceeds_for_faq_route(self, mock_callback_context):
        _, cb, _, _ = _import_summary()
        mock_callback_context.state["guardrail_result"] = "SAFE"
        mock_callback_context.state["route_decision"] = "FAQ"
        result = cb(mock_callback_context)
        assert result is None

    def test_proceeds_for_analysis_route(self, mock_callback_context):
        _, cb, _, _ = _import_summary()
        mock_callback_context.state["guardrail_result"] = "SAFE"
        mock_callback_context.state["route_decision"] = "ANALYSIS"
        result = cb(mock_callback_context)
        assert result is None

    def test_proceeds_for_empty_state(self, mock_callback_context):
        """Empty state should not be treated as BLOCKED or OFF_TOPIC."""
        _, cb, _, _ = _import_summary()
        result = cb(mock_callback_context)
        assert result is None

    def test_case_insensitive_blocked(self, mock_callback_context):
        _, cb, _, _ = _import_summary()
        mock_callback_context.state["guardrail_result"] = "blocked"
        mock_callback_context.state["route_decision"] = ""
        result = cb(mock_callback_context)
        assert result is not None

    def test_case_insensitive_off_topic(self, mock_callback_context):
        _, cb, _, _ = _import_summary()
        mock_callback_context.state["guardrail_result"] = "SAFE"
        mock_callback_context.state["route_decision"] = "off_topic"
        result = cb(mock_callback_context)
        assert result is not None


# ---------------------------------------------------------------------------
# 2. Agent construction tests
# ---------------------------------------------------------------------------

class TestSummaryAgentConstruction:

    def test_agent_name(self):
        agent, *_ = _import_summary()
        assert agent.name == "SummaryAgent"

    def test_output_key(self):
        agent, *_ = _import_summary()
        assert agent.output_key == "final_response"

    def test_model_set(self):
        agent, *_ = _import_summary()
        assert agent.model is not None

    def test_callback_registered(self):
        agent, cb, *_ = _import_summary()
        assert agent.before_agent_callback is cb

    def test_no_tools(self):
        agent, *_ = _import_summary()
        assert not agent.tools


# ---------------------------------------------------------------------------
# 3. Pre-built static response content
# ---------------------------------------------------------------------------

class TestPreBuiltResponses:

    def test_blocked_response_is_content_object(self):
        from google.genai import types
        _, _, blocked, _ = _import_summary()
        assert isinstance(blocked, types.Content)

    def test_off_topic_response_is_content_object(self):
        from google.genai import types
        _, _, _, off_topic = _import_summary()
        assert isinstance(off_topic, types.Content)

    def test_blocked_response_has_text(self):
        _, _, blocked, _ = _import_summary()
        text = blocked.parts[0].text if blocked.parts else ""
        assert len(text) > 10

    def test_off_topic_response_has_text(self):
        _, _, _, off_topic = _import_summary()
        text = off_topic.parts[0].text if off_topic.parts else ""
        assert len(text) > 10

    def test_blocked_response_includes_disclaimer(self):
        _, _, blocked, _ = _import_summary()
        text = blocked.parts[0].text
        assert "educational" in text.lower() or "advice" in text.lower()

    def test_off_topic_response_includes_disclaimer(self):
        _, _, _, off_topic = _import_summary()
        text = off_topic.parts[0].text
        assert "educational" in text.lower() or "advice" in text.lower()

    def test_off_topic_lists_alternatives(self):
        """OFF_TOPIC response should suggest what the agent CAN help with."""
        _, _, _, off_topic = _import_summary()
        text = off_topic.parts[0].text
        assert "analyse" in text.lower() or "analysis" in text.lower() or \
               "p/e" in text.lower() or "stock" in text.lower()


# ---------------------------------------------------------------------------
# 4. Instruction content tests
# ---------------------------------------------------------------------------

class TestSummaryAgentInstruction:

    @pytest.fixture(autouse=True)
    def _agent(self):
        self.agent, *_ = _import_summary()

    def test_mentions_faq_result(self):
        assert "faq_result" in self.agent.instruction

    def test_mentions_analysis_result(self):
        assert "analysis_result" in self.agent.instruction

    def test_mentions_disclaimer(self):
        instr_lower = self.agent.instruction.lower()
        assert "disclaimer" in instr_lower or "educational" in instr_lower or \
               "not financial advice" in instr_lower

    def test_instructs_markdown_formatting(self):
        instr_lower = self.agent.instruction.lower()
        assert "markdown" in instr_lower or "##" in self.agent.instruction or \
               "format" in instr_lower

    def test_instructs_merge_outputs(self):
        instr_lower = self.agent.instruction.lower()
        assert "merge" in instr_lower or "combine" in instr_lower or \
               "non-empty" in instr_lower


# ---------------------------------------------------------------------------
# 5. Parametrized route scenarios
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("guardrail,route,expect_short_circuit", [
    ("SAFE",    "FAQ",       False),
    ("SAFE",    "ANALYSIS",  False),
    ("SAFE",    "OFF_TOPIC", True),
    ("BLOCKED", "FAQ",       True),
    ("BLOCKED", "ANALYSIS",  True),
    ("BLOCKED", "BLOCKED",   True),
    ("SAFE",    "BLOCKED",   True),
    ("",        "",          False),   # empty state → proceed
])
def test_summary_callback_parametrized(
    guardrail, route, expect_short_circuit, mock_callback_context
):
    _, cb, *_ = _import_summary()
    mock_callback_context.state["guardrail_result"] = guardrail
    mock_callback_context.state["route_decision"] = route
    result = cb(mock_callback_context)
    if expect_short_circuit:
        assert result is not None, \
            f"Expected short-circuit for guardrail={guardrail!r}, route={route!r}"
    else:
        assert result is None, \
            f"Expected proceed for guardrail={guardrail!r}, route={route!r}"
