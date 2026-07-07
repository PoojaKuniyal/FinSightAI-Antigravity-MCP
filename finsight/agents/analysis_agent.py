"""
analysis_agent.py – Node 3b in the FinSight AI graph pipeline.

Responsibility (single):
  Perform quantitative company analysis using live financial data
  retrieved exclusively via the Alpha Vantage MCP and Financial Dataset MCP.

Data retrieved:
  - Real-time stock price
  - Company overview & profile
  - Income statement (revenue, net income, EPS)
  - Balance sheet (assets, liabilities, equity)
  - Cash flow statement (operating, investing, financing)

Rules:
  - Use ONLY data returned by MCP tools. No hallucination.
  - No investment advice. Factual analysis only.
  - Only runs when route_decision == "ANALYSIS".

Output: writes structured analysis to session.state["analysis_result"].

System prompt: prompts/analysis.md
"""

from pathlib import Path
from typing import Optional

from google.adk.agents import LlmAgent
from google.adk.agents.callback_context import CallbackContext
from google.genai import types

from finsight.config import GEMINI_MODEL
from finsight.tools.mcp_tools import (
    build_alpha_vantage_toolset,
    build_financial_dataset_toolset,
)

# ── Load system prompt from file ─────────────────────────────────────────────
_PROMPT_PATH = Path(__file__).parent.parent.parent / "prompts" / "analysis.md"
_ANALYSIS_PROMPT = _PROMPT_PATH.read_text(encoding="utf-8")

_SYSTEM_PROMPT = f"""{_ANALYSIS_PROMPT}

You are a professional equity research analyst. You have access to real-time
financial data via MCP tools. Your workflow for every company analysis request:

1. Extract the company name or ticker symbol from the user's message.
2. Use the MCP tools to retrieve:
   a. Current stock price
   b. Company overview (sector, industry, market cap, description)
   c. Income statement (revenue, gross profit, operating income, net income, EPS)
   d. Balance sheet (total assets, total liabilities, shareholder equity, debt)
   e. Cash flow statement (operating cash flow, free cash flow, capex)
3. Summarize the retrieved data into clear sections:
   - 📈 Price & Valuation
   - 🏢 Company Overview
   - 💰 Revenue & Profitability
   - 📊 Balance Sheet Health
   - 💵 Cash Flow Analysis
4. Highlight key financial ratios where calculable (P/E, ROE, Debt/Equity).
5. Conclude with a brief Financial Health Summary (factual only).

STRICT RULES:
- Only use data returned by the tools. If a tool returns no data, say so.
- Never fabricate numbers or make up financial figures.
- Never provide buy/sell/hold recommendations.
- Never give personalized investment advice.
"""


# ── before_agent_callback: run ONLY for ANALYSIS route ───────────────────────

def _run_only_for_analysis(callback_context: CallbackContext) -> Optional[types.Content]:
    """Skip analysis agent if the router did not classify this as ANALYSIS."""
    route = callback_context.state.get("route_decision", "").strip().upper()
    if route != "ANALYSIS":
        callback_context.state["analysis_result"] = ""
        return types.Content(
            role="model",
            parts=[types.Part(text="")],
        )
    return None  # proceed — this is an analysis query


# ── MCP Toolsets ─────────────────────────────────────────────────────────────
# Built at module load time; the toolset manages its own subprocess lifecycle.
_alpha_vantage_tools = build_alpha_vantage_toolset()
_financial_dataset_tools = build_financial_dataset_toolset()


# ── Agent definition ─────────────────────────────────────────────────────────
analysis_agent = LlmAgent(
    name="AnalysisAgent",
    model=GEMINI_MODEL,
    instruction=_SYSTEM_PROMPT,
    description=(
        "Company analysis specialist: retrieves live stock price, revenue, "
        "profitability, balance sheet, and cash flow data via MCP tools "
        "and produces a structured factual report."
    ),
    before_agent_callback=_run_only_for_analysis,
    tools=[_alpha_vantage_tools, _financial_dataset_tools],
    output_key="analysis_result",   # written to session.state["analysis_result"]
)
