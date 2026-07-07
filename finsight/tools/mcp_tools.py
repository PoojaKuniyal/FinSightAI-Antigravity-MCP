"""
mcp_tools.py – MCP Toolset definitions for FinSight AI.

Both MCP servers use the official remote endpoints registered in
.agents/mcp_config.json. API keys are read from environment variables
only — never hardcoded.

Alpha Vantage MCP (alphavantage):
  Remote endpoint : https://mcp.alphavantage.co/mcp
  Auth            : ?apikey=<ALPHA_VANTAGE>  (query-parameter)
  Env var         : ALPHA_VANTAGE

Financial Dataset MCP (financialdatasets):
  Remote endpoint : https://mcp.financialdatasets.ai/
  Auth            : X-API-KEY: <FINANCIAL_DATASET>  (HTTP header)
  Env var         : FINANCIAL_DATASET
  Tools exposed   : income statements, balance sheets, cash flow,
                    financial metrics, earnings

Both toolsets are bound exclusively to AnalysisAgent.
"""

import logging

from google.adk.tools.mcp_tool.mcp_toolset import (
    MCPToolset,
    StreamableHTTPConnectionParams,
)

from finsight.config import ALPHA_VANTAGE_API_KEY, FINANCIAL_DATASET_API_KEY

log = logging.getLogger(__name__)


# ── Alpha Vantage remote MCP endpoint ────────────────────────────────────────
#
# Registered in: .agents/mcp_config.json  →  "alphavantage"
# Auth: API key appended as ?apikey= query-parameter at runtime.
#
_AV_REMOTE_BASE_URL = "https://mcp.alphavantage.co/mcp"


def build_alpha_vantage_toolset() -> MCPToolset:
    """
    Connect to the official Alpha Vantage remote MCP server.
    The API key is appended as a URL query-parameter at runtime —
    read from the ALPHA_VANTAGE environment variable in .env.
    """
    url_with_key = f"{_AV_REMOTE_BASE_URL}?apikey={ALPHA_VANTAGE_API_KEY}"

    connection_params = StreamableHTTPConnectionParams(
        url=url_with_key,
        headers={"Accept": "application/json, text/event-stream"},
        timeout=60.0,
        sse_read_timeout=120.0,
    )

    log.info("Alpha Vantage MCP: remote endpoint %s", _AV_REMOTE_BASE_URL)
    return MCPToolset(connection_params=connection_params)


# ── Financial Dataset remote MCP endpoint ────────────────────────────────────
#
# Registered in: .agents/mcp_config.json  →  "financialdatasets"
# Auth: API key sent as X-API-KEY HTTP header at runtime.
# Tools: income statements, balance sheets, cash flow, metrics, earnings.
#
_FD_REMOTE_URL = "https://mcp.financialdatasets.ai/"


def build_financial_dataset_toolset() -> MCPToolset:
    """
    Connect to the official Financial Datasets remote MCP server.
    The API key is passed as the X-API-KEY HTTP header at runtime —
    read from the FINANCIAL_DATASET environment variable in .env.

    Exposes financial statement tools to AnalysisAgent:
      - get_income_statements
      - get_balance_sheets
      - get_cash_flow_statements
      - get_financial_metrics
      - get_earnings
    """
    connection_params = StreamableHTTPConnectionParams(
        url=_FD_REMOTE_URL,
        headers={
            "X-API-KEY": FINANCIAL_DATASET_API_KEY,
            "Accept": "application/json, text/event-stream",
        },
        timeout=60.0,
        sse_read_timeout=120.0,
    )

    log.info("Financial Dataset MCP: remote endpoint %s", _FD_REMOTE_URL)
    return MCPToolset(connection_params=connection_params)
