"""
faq_agent.py – Node 3a in the FinSight AI graph pipeline.

Responsibility (single):
  Answer general finance concept questions (EPS, P/E ratio, EBITDA,
  ROE, market cap, etc.) with clear, beginner-friendly explanations.
  Does NOT handle company-specific analysis.

This agent only runs when route_decision == "FAQ".
Output: writes the explanation to session.state["faq_result"].

System prompt: prompts/faq.md
"""

from pathlib import Path
from typing import Optional

from google.adk.agents import LlmAgent
from google.adk.agents.callback_context import CallbackContext
from google.genai import types

from finsight.config import GEMINI_MODEL

# ── Load system prompt from file ─────────────────────────────────────────────
_PROMPT_PATH = Path(__file__).parent.parent.parent / "prompts" / "faq.md"
_FAQ_PROMPT = _PROMPT_PATH.read_text(encoding="utf-8")

_SYSTEM_PROMPT = f"""{_FAQ_PROMPT}

You are a financial education assistant. Explain financial concepts in plain language.
Cover topics such as:
  - EPS (Earnings Per Share)
  - P/E Ratio (Price-to-Earnings)
  - EBITDA
  - ROE (Return on Equity)
  - Market Capitalization
  - Revenue vs. Profit
  - Balance Sheet, Income Statement, Cash Flow Statement
  - Dividend Yield, Book Value, Beta

Keep explanations concise (2-4 sentences per concept), accurate, and jargon-free.
Never provide buy/sell recommendations or personalized investment advice.

IMPORTANT: If the question asks for current/live/actual data for a specific company
(e.g. "What is Apple's P/E ratio?", "What is Tesla's market cap?"), respond with:
  "I can only explain financial concepts. For live company data, please ask something
   like: 'Analyse Apple (AAPL)' and the Analysis agent will retrieve real-time data."
Do NOT fabricate any numbers for a real company.
"""


# ── before_agent_callback: run ONLY for FAQ route ────────────────────────────

def _run_only_for_faq(callback_context: CallbackContext) -> Optional[types.Content]:
    """Skip FAQ agent if the router did not classify this as FAQ."""
    route = callback_context.state.get("route_decision", "").strip().upper()
    if route != "FAQ":
        # Write empty result so summary agent knows this path was skipped
        callback_context.state["faq_result"] = ""
        return types.Content(
            role="model",
            parts=[types.Part(text="")],
        )
    return None  # proceed — this is an FAQ query


# ── Agent definition ─────────────────────────────────────────────────────────
faq_agent = LlmAgent(
    name="FAQAgent",
    model=GEMINI_MODEL,
    instruction=_SYSTEM_PROMPT,
    description=(
        "FAQ specialist: answers financial concept questions (EPS, P/E, EBITDA, "
        "ROE, market cap) with simple, educational explanations."
    ),
    before_agent_callback=_run_only_for_faq,
    output_key="faq_result",   # written to session.state["faq_result"]
)
