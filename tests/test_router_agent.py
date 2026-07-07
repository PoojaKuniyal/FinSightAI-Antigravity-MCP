"""
test_router_agent.py – Tests for RouterAgent.

Strategy
--------
RouterAgent has a before_agent_callback (_skip_if_blocked) that short-circuits
when guardrail_result == "BLOCKED".  All other queries reach the LLM which
must reply with FAQ | ANALYSIS | OFF_TOPIC.

Test levels:
  1. Unit – callback logic directly (no LLM, no Runner)
  2. Unit – agent construction
  3. Integration – full LLM-mocked Runner runs
"""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _import_router():
    from finsight.agents.router_agent import router_agent, _skip_if_blocked
    return router_agent, _skip_if_blocked


# ---------------------------------------------------------------------------
# 1. Callback unit tests – _skip_if_blocked
# ---------------------------------------------------------------------------

class TestSkipIfBlockedCallback:

    def test_returns_none_when_safe(self, mock_callback_context):
        """SAFE state → callback returns None so Router proceeds normally."""
        _, _skip_if_blocked = _import_router()
        mock_callback_context.state["guardrail_result"] = "SAFE"
        result = _skip_if_blocked(mock_callback_context)
        assert result is None

    def test_returns_content_when_blocked(self, mock_callback_context):
        """BLOCKED state → callback returns Content and writes route_decision."""
        from google.genai import types
        _, _skip_if_blocked = _import_router()
        mock_callback_context.state["guardrail_result"] = "BLOCKED"
        result = _skip_if_blocked(mock_callback_context)
        assert result is not None
        assert isinstance(result, types.Content)
        assert mock_callback_context.state.get("route_decision") == "BLOCKED"

    def test_skipped_response_text_is_blocked(self, mock_callback_context):
        _, _skip_if_blocked = _import_router()
        mock_callback_context.state["guardrail_result"] = "BLOCKED"
        result = _skip_if_blocked(mock_callback_context)
        text = result.parts[0].text if result.parts else ""
        assert text.upper() == "BLOCKED"

    def test_returns_none_when_state_is_empty(self, mock_callback_context):
        """Empty state means not BLOCKED → proceed."""
        _, _skip_if_blocked = _import_router()
        # state has no guardrail_result key
        result = _skip_if_blocked(mock_callback_context)
        assert result is None

    def test_case_insensitive_blocked_check(self, mock_callback_context):
        """Guard against mixed-case LLM output like 'Blocked'."""
        _, _skip_if_blocked = _import_router()
        mock_callback_context.state["guardrail_result"] = "blocked"
        result = _skip_if_blocked(mock_callback_context)
        assert result is not None
        assert mock_callback_context.state.get("route_decision") == "BLOCKED"


# ---------------------------------------------------------------------------
# 2. Agent construction tests
# ---------------------------------------------------------------------------

class TestRouterAgentConstruction:

    def test_agent_name(self):
        agent, _ = _import_router()
        assert agent.name == "RouterAgent"

    def test_output_key(self):
        agent, _ = _import_router()
        assert agent.output_key == "route_decision"

    def test_model_set(self):
        agent, _ = _import_router()
        assert agent.model is not None

    def test_instruction_contains_analysis(self):
        agent, _ = _import_router()
        assert "ANALYSIS" in agent.instruction

    def test_instruction_contains_faq(self):
        agent, _ = _import_router()
        assert "FAQ" in agent.instruction

    def test_instruction_contains_off_topic(self):
        agent, _ = _import_router()
        assert "OFF_TOPIC" in agent.instruction

    def test_tiebreaker_favours_analysis(self):
        """Router prompt must include a tiebreaker rule favouring ANALYSIS."""
        agent, _ = _import_router()
        assert "TIEBREAKER" in agent.instruction or "doubt" in agent.instruction.lower()

    def test_no_tools(self):
        agent, _ = _import_router()
        assert not agent.tools

    def test_callback_registered(self):
        agent, _skip_if_blocked = _import_router()
        assert agent.before_agent_callback is _skip_if_blocked


# ---------------------------------------------------------------------------
# 3. Classification instruction coverage
# ---------------------------------------------------------------------------

class TestRouterClassificationGuide:
    """Ensure the instruction includes examples for each classification."""

    @pytest.fixture(autouse=True)
    def _agent(self):
        self.agent, _ = _import_router()

    def test_company_name_triggers_analysis(self):
        instr = self.agent.instruction
        # At least one real company must appear as an example
        companies = ["Apple", "Microsoft", "Tesla", "Google", "Amazon", "NVDA", "AAPL"]
        assert any(c in instr for c in companies)

    def test_faq_examples_present(self):
        instr = self.agent.instruction
        assert "P/E" in instr or "EBITDA" in instr or "What is" in instr

    def test_rule_company_always_analysis(self):
        """Instruction must state the ticker/company → ANALYSIS rule explicitly."""
        instr = self.agent.instruction
        assert "company" in instr.lower() and "ANALYSIS" in instr


# ---------------------------------------------------------------------------
# 4. Integration – LLM-mocked Runner
# ---------------------------------------------------------------------------

class TestRouterAgentIntegration:
    """End-to-end runner tests with mocked LLM. Skipped in CI."""

    @pytest.fixture(autouse=True)
    def _patch_llm(self):
        self._mock_llm = MagicMock()
        patcher = patch(
            "google.genai.models.Models.generate_content",
            new=self._mock_llm,
        )
        patcher.start()
        yield
        patcher.stop()

    def _make_response(self, text: str):
        part = MagicMock(); part.text = text
        candidate = MagicMock()
        candidate.content.parts = [part]
        candidate.finish_reason = "STOP"
        resp = MagicMock(); resp.candidates = [candidate]; resp.text = text
        return resp

    def _run(self, guardrail_result: str, llm_reply: str) -> str:
        import asyncio
        from google.adk.runners import Runner
        from google.adk.sessions import InMemorySessionService
        from google.genai import types

        self._mock_llm.return_value = self._make_response(llm_reply)
        agent, _ = _import_router()
        svc = InMemorySessionService()
        runner = Runner(agent=agent, app_name="test_router", session_service=svc)

        async def _go():
            session = await svc.create_session(
                app_name="test_router", user_id="u", session_id="s"
            )
            # Pre-seed guardrail_result in state
            session.state["guardrail_result"] = guardrail_result
            content = types.Content(
                role="user", parts=[types.Part(text="What is Apple's P/E ratio?")]
            )
            async for _ in runner.run_async(user_id="u", session_id="s", new_message=content):
                pass
            s = await svc.get_session(app_name="test_router", user_id="u", session_id="s")
            return s.state.get("route_decision", "")

        return asyncio.run(_go())

    @pytest.mark.skipif(True, reason="Integration: requires real ADK environment")
    def test_safe_input_routes_to_analysis(self):
        route = self._run("SAFE", "ANALYSIS")
        assert route.strip().upper() == "ANALYSIS"

    @pytest.mark.skipif(True, reason="Integration: requires real ADK environment")
    def test_blocked_skips_llm(self):
        """BLOCKED input must skip LLM entirely."""
        route = self._run("BLOCKED", "")
        assert route.strip().upper() == "BLOCKED"
        self._mock_llm.assert_not_called()
