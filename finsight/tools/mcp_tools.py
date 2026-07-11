"""
mcp_tools.py – MCP Toolset definitions for FinSight AI.

Both MCP servers use the official remote endpoints registered in
.agents/mcp_config.json. API keys are read from environment variables
only — never hardcoded.

Alpha Vantage MCP (alphavantage):
  Remote endpoint : https://mcp.alphavantage.co/mcp
  Transport       : Streamable HTTP  (StreamableHTTPConnectionParams)
  Auth            : apikey: <ALPHA_VANTAGE>  (HTTP header)
  Env var         : ALPHA_VANTAGE
  NOTE: The AV server is a Streamable HTTP server (returns application/json).
        The original 405 was caused by the API key being in the query string
        (?apikey=...), which the server rejects. Passing it as an HTTP header
        fixes the 405. Do NOT use SseConnectionParams — the SSE handshake
        silently fails against this server and registers 0 tools.

Financial Dataset MCP (financialdatasets):
  Remote endpoint : https://mcp.financialdatasets.ai/mcp
  Transport       : Streamable HTTP  (StreamableHTTPConnectionParams)
  Auth            : X-API-KEY: <FINANCIAL_DATASET>  (HTTP header)
  Env var         : FINANCIAL_DATASET
  Tools exposed   : income statements, balance sheets, cash flow,
                    financial metrics, earnings

Both toolsets are bound exclusively to AnalysisAgent.

NOTE: MCPToolset (PascalCase capital C) is deprecated in ADK ≥ 1.x.
      Use McpToolset (lowercase 'p') — the new BaseToolset-based API.
"""

import logging

from google.adk.tools.mcp_tool.mcp_toolset import (
    McpToolset,
    StreamableHTTPConnectionParams,
)

from finsight.config import ALPHA_VANTAGE_API_KEY, FINANCIAL_DATASET_API_KEY

log = logging.getLogger(__name__)


# ── Alpha Vantage remote MCP endpoint ────────────────────────────────────────
#
# Registered in: .agents/mcp_config.json  →  "alphavantage"
# Transport: Streamable HTTP — AV server returns application/json (not SSE).
# Auth: API key sent as "apikey" HTTP header — NOT as a query-parameter.
#   (Passing the key as ?apikey= in the query string causes HTTP 405.)
#
_AV_REMOTE_URL = "https://mcp.alphavantage.co/mcp"


def build_alpha_vantage_toolset() -> McpToolset:
    """
    Connect to the official Alpha Vantage remote MCP server.

    Transport: StreamableHTTPConnectionParams (Streamable HTTP / JSON-RPC POST).
    The AV server is NOT an SSE server — using SseConnectionParams silently
    fails the handshake and registers 0 tools, causing MALFORMED_FUNCTION_CALL.

    Root cause of the original HTTP 405: the API key was appended as a URL
    query-parameter (?apikey=...). The server rejects that form. Passing the
    key as the "apikey" HTTP request header resolves it.

    Key read from ALPHA_VANTAGE environment variable in .env.
    """
    connection_params = StreamableHTTPConnectionParams(
        url=_AV_REMOTE_URL,
        headers={
            "apikey": ALPHA_VANTAGE_API_KEY,
            "Accept": "application/json, text/event-stream",
        },
        timeout=60.0,
        sse_read_timeout=300.0,
    )

    log.info("Alpha Vantage MCP: Streamable HTTP endpoint %s", _AV_REMOTE_URL)
    return McpToolset(connection_params=connection_params)


# ── Financial Dataset remote MCP endpoint ────────────────────────────────────
#
# Registered in: .agents/mcp_config.json  →  "financialdatasets"
# Auth: API key sent as X-API-KEY HTTP header at runtime.
# Tools: income statements, balance sheets, cash flow, metrics, earnings.
#
_FD_REMOTE_URL = "https://mcp.financialdatasets.ai/mcp"


def build_financial_dataset_toolset() -> McpToolset:
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
    return McpToolset(connection_params=connection_params)
