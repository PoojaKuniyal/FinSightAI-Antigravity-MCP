"""
router_agent.py – Node 2 in the FinSight AI graph pipeline.

Responsibility (single):
  Classify the user's intent into one of three categories:
    FAQ        – general finance concept question
    ANALYSIS   – request for company/stock data analysis
    OFF_TOPIC  – unrelated to finance

This agent only runs when guardrail_result == "SAFE".
Output: writes the label to session.state["route_decision"].

System prompt: prompts/router.md
"""

from pathlib import Path
from typing import Optional

from google.adk.agents import LlmAgent
from google.adk.agents.callback_context import CallbackContext
from google.genai import types

from finsight.config import GEMINI_MODEL

# ── Load system prompt from file ─────────────────────────────────────────────
_PROMPT_PATH = Path(__file__).parent.parent.parent / "prompts" / "router.md"
_ROUTER_PROMPT = _PROMPT_PATH.read_text(encoding="utf-8")

_SYSTEM_PROMPT = f"""{_ROUTER_PROMPT}

CRITICAL OUTPUT RULE:
Respond with ONLY one of these three labels — no punctuation, no explanation:
  FAQ
  ANALYSIS
  OFF_TOPIC

Classification guide:
- ANALYSIS   : ANY query that mentions a specific company name, stock ticker, or asks
               for CURRENT / LIVE / ACTUAL data for a real company.
               Examples → "What is Apple's P/E ratio?", "AAPL market cap",
               "Analyse Microsoft", "Tesla's revenue", "current EPS of Google",
               "What is NVDA trading at?", "Show me Amazon's balance sheet"
               RULE: if a company name OR ticker symbol appears in the query → ALWAYS ANALYSIS.

- FAQ        : questions asking to EXPLAIN or DEFINE a general financial concept
               with NO company name and NO request for live/current data.
               Examples → "What is a P/E ratio?", "Explain EBITDA",
               "How does market cap work?", "What does ROE mean?"

- OFF_TOPIC  : anything not related to finance, stocks, or investing at all.

TIEBREAKER: When in doubt between FAQ and ANALYSIS, choose ANALYSIS.
"""


# ── before_agent_callback: skip if BLOCKED ───────────────────────────────────

def _skip_if_blocked(callback_context: CallbackContext) -> Optional[types.Content]:
    """Skip router if guardrail blocked the input."""
    result = callback_context.state.get("guardrail_result", "").strip().upper()
    if result == "BLOCKED":
        # Write the default route so downstream agents handle it cleanly
        callback_context.state["route_decision"] = "BLOCKED"
        return types.Content(
            role="model",
            parts=[types.Part(text="BLOCKED")],
        )
    return None  # proceed normally


# ── Agent definition ─────────────────────────────────────────────────────────
router_agent = LlmAgent(
    name="RouterAgent",
    model=GEMINI_MODEL,
    instruction=_SYSTEM_PROMPT,
    description=(
        "Intent router: classifies safe user queries into FAQ, ANALYSIS, "
        "or OFF_TOPIC to direct the workflow to the correct specialist agent."
    ),
    before_agent_callback=_skip_if_blocked,
    output_key="route_decision",   # written to session.state["route_decision"]
)
