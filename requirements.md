# Requirements

- Use ADK 2.0 Graph Workflow.
- One responsibility per agent.

## Guardrail
Input → SAFE | BLOCKED
Detect:
- Prompt injection
- Jailbreak
- Prompt leakage
- Unsafe requests

## Router
Classify:
- FAQ
- ANALYSIS
- OFF_TOPIC

## FAQ
Answer finance basics:
- EPS
- P/E
- EBITDA
- ROE
- Market Cap

## Analysis
Use:
- Alpha Vantage MCP
- Financial Dataset MCP

Return:
- Price
- Revenue
- Profitability
- Cash Flow
- Financial Health

No investment advice.

## Summary
Merge outputs.
Append:
"Educational only. Not financial advice."

## Redis MCP
Store:
- Chat history
- Session
- Price cache (30s)
- Financial cache (24h)