# FinSight AI 📊

> **Multi-Agent Equity Research Assistant** — powered by Google ADK & Gemini  
> _For informational purposes only. Not investment advice._

![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)
![Google ADK](https://img.shields.io/badge/Google%20ADK-1.0%2B-4285F4?logo=google&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.0%2B-000000?logo=flask&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-5.0%2B-DC382D?logo=redis&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)

---

## Overview

FinSight AI is a **five-agent equity research pipeline** that answers financial questions and delivers company-level stock analysis in plain language. It uses Google's [Agent Development Kit (ADK)](https://google.github.io/adk-docs/) to orchestrate specialised LLM agents through a sequential graph, with real-time market data sourced via two remote MCP servers.

**Key capabilities:**

- 🛡️ **Prompt safety** — every query passes through a guardrail before any agent processes it
- 🧭 **Smart routing** — intent is classified as FAQ, Company Analysis, or Off-Topic
- 📚 **Finance FAQ** — plain-language explanations of financial concepts (P/E, EBITDA, ROE …)
- 📊 **Live company analysis** — stock price, overview, income statement, balance sheet, cash flow
- ✨ **Structured summaries** — a dedicated agent merges outputs into a clean, readable report
- 💬 **Session memory** — Redis-backed conversation history (in-memory fallback when Redis is unavailable)

---

## Agent Workflow

```
┌─────────────────────────────────────────────────────────────────┐
│                        FinSight AI Pipeline                     │
│                     (ADK SequentialAgent)                       │
└─────────────────────────────────────────────────────────────────┘

  User Query
      │
      ▼
┌─────────────┐   BLOCKED ──────────────────────────────────────┐
│  🛡️ Node 1   │                                                 │
│  Guardrail  │ Classifies input as SAFE or BLOCKED             │
│   Agent     │ Catches: prompt injection, jailbreaks,          │
└──────┬──────┘ harmful / off-policy content                     │
       │ SAFE                                                    │
       ▼                                                         │
┌─────────────┐                                                  │
│  🧭 Node 2   │ Classifies intent:                              │
│   Router    │   FAQ        → finance concept question          │
│   Agent     │   ANALYSIS   → company / ticker query           │
└──────┬──────┘   OFF_TOPIC  → not finance-related              │
       │                                                         │
       ├─── FAQ ──────────────────────┐                         │
       │                              ▼                         │
       │                     ┌─────────────────┐                │
       │                     │   📚 Node 3a     │                │
       │                     │   FAQ Agent      │                │
       │                     │                  │                │
       │                     │ Answers general  │                │
       │                     │ finance concepts │                │
       │                     └────────┬────────┘                │
       │                              │                         │
       ├─── ANALYSIS ─────────────────┤                         │
       │                              │                         │
       │              ┌───────────────┘                         │
       │              │                                         │
       │              ▼                                         │
       │     ┌─────────────────┐   MCP Servers                  │
       │     │   📊 Node 3b     │◄──────────────────────────┐   │
       │     │ Company Analysis │                            │   │
       │     │     Agent        │  Alpha Vantage MCP         │   │
       │     │                  │  ├─ Stock Price            │   │
       │     │  Retrieves live  │  ├─ Company Overview       │   │
       │     │  financial data  │  └─ Income Statement       │   │
       │     └────────┬────────┘                             │   │
       │              │         Financial Datasets MCP        │   │
       │              │         ├─ Balance Sheet             │   │
       │              │         ├─ Cash Flow Statement       │   │
       │              │         ├─ Key Metrics               │   │
       │              │         └─ Earnings                  │   │
       │              │                                      │   │
       ├─── OFF_TOPIC ────────────────────────────────┐      │   │
       │                                              │      │   │
       └──────────────────────────┐                   │      │   │
                                  ▼                   │      │   │
                         ┌─────────────────┐          │      │   │
                         │   ✨ Node 4      │          │      │   │
                         │ Summary Agent   │◄──────────┘      │   │
                         │                 │◄─────────────────┘   │
                         │ Merges outputs, │◄─────────────────────┘
                         │ formats report, │
                         │ appends notice  │
                         └────────┬────────┘
                                  │
                                  ▼
                         ┌─────────────────┐
                         │  📦 Redis Cache  │
                         │  Session Store   │
                         └────────┬────────┘
                                  │
                                  ▼
                            Final Response
                          (streamed to UI)
```

### State Flow (Session Keys)

| Key | Written by | Values |
|-----|-----------|--------|
| `guardrail_result` | GuardrailAgent | `SAFE` \| `BLOCKED` |
| `route_decision` | RouterAgent | `FAQ` \| `ANALYSIS` \| `OFF_TOPIC` \| `BLOCKED` |
| `faq_result` | FAQAgent | FAQ answer string (or `""`) |
| `analysis_result` | CompanyAnalysisAgent | Financial report string (or `""`) |
| `final_response` | SummaryAgent | Merged, formatted response |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Agent Framework** | [Google ADK](https://google.github.io/adk-docs/) (`google-adk >= 1.0.0`) |
| **LLM** | Google Gemini (`gemini-2.0-flash` / `gemini-2.5-flash`) |
| **Web Server** | Flask 3.0 + Flask-CORS |
| **Session Store** | Redis 5 (in-memory fallback) |
| **Data Sources** | Alpha Vantage MCP · Financial Datasets MCP |
| **Protocol** | Model Context Protocol (MCP) over Streamable HTTP |
| **Frontend** | Vanilla HTML / CSS / JavaScript |

---

## Project Structure

```
stock_analysis_agent/
│
├── app.py                     # Flask entry point & API routes
│
├── finsight/
│   ├── agents/
│   │   ├── guardrail_agent.py # Node 1 — safety check
│   │   ├── router_agent.py    # Node 2 — intent classification
│   │   ├── faq_agent.py       # Node 3a — finance FAQ
│   │   ├── analysis_agent.py  # Node 3b — company analysis (MCP)
│   │   └── summary_agent.py   # Node 4  — merge & format
│   │
│   ├── graph/
│   │   └── pipeline.py        # ADK SequentialAgent assembly
│   │
│   ├── tools/
│   │   └── mcp_tools.py       # Alpha Vantage & Financial Datasets toolsets
│   │
│   ├── redis_session.py       # Redis-backed chat history
│   └── config.py              # Environment variable loading
│
├── prompts/                   # System prompt markdown files
│   ├── guardrail.md
│   ├── router.md
│   ├── faq.md
│   ├── analysis.md
│   └── summary.md
│
├── templates/
│   └── index.html             # Chat UI
│
├── static/
│   ├── app.js                 # Frontend logic
│   └── style.css              # Styling
│
├── tests/                     # pytest test suite
├── .agents/
│   └── mcp_config.json        # MCP server definitions & bindings
├── .env.example               # Environment variable template
└── requirements.txt
```

---

## Getting Started

### Prerequisites

- Python 3.11+
- Redis server (optional — falls back to in-memory if unavailable)
- API keys:
  - [Google AI Studio](https://aistudio.google.com/app/apikey) — Gemini API key
  - [Alpha Vantage](https://www.alphavantage.co/support/#api-key) — stock data
  - [Financial Datasets](https://financialdatasets.ai/) — financial statements

### 1. Clone the repository

```bash
git clone https://github.com/your-username/stock_analysis_agent.git
cd stock_analysis_agent
```

### 2. Create a virtual environment

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` and fill in your keys:

```env
# Required
GEMINI_API_KEY=your-gemini-api-key-here
ALPHA_VANTAGE=your-alpha-vantage-key-here
FINANCIAL_DATASET=your-financial-dataset-key-here

# Optional
GEMINI_MODEL=gemini-2.0-flash
REDIS_URL=redis://localhost:6379
FLASK_SECRET_KEY=change-me-in-production
FLASK_PORT=5000
FLASK_DEBUG=false
```

### 5. (Optional) Start Redis

```bash
# Docker
docker run -d -p 6379:6379 redis:alpine

# Or use a local Redis installation
redis-server
```

### 6. Run the app

```bash
python app.py
```

Open your browser at **http://localhost:5000**

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Serve the chat UI |
| `POST` | `/api/chat` | Run the ADK pipeline on a user message |
| `GET` | `/api/history` | Return chat history for the current session |
| `POST` | `/api/clear` | Clear chat history for the current session |
| `GET` | `/api/status` | Health check (Redis, API keys, pipeline) |

### POST /api/chat

**Request:**
```json
{ "message": "Analyse Apple (AAPL) stock" }
```

**Response:**
```json
{
  "session_id": "uuid-string",
  "response": "## Apple Inc. (AAPL) — Company Analysis\n..."
}
```

---

## MCP Servers

Both data sources are consumed by **CompanyAnalysisAgent** via the Model Context Protocol.

| Server | Transport | Tools |
|--------|-----------|-------|
| **Alpha Vantage** | Streamable HTTP | Stock price, company overview, income statement |
| **Financial Datasets** | Streamable HTTP | Balance sheet, cash flow, key metrics, earnings |

MCP bindings are declared in [`.agents/mcp_config.json`](.agents/mcp_config.json).  
API keys are injected at runtime from environment variables — never hardcoded.

---

## Running Tests

```bash
pytest
```

Test files are in `tests/` and cover each agent individually:

```
tests/
├── test_guardrail_agent.py
├── test_router_agent.py
├── test_faq_agent.py
├── test_analysis_agent.py
└── test_summary_agent.py
```

---

## Example Queries

| Type | Example |
|------|---------|
| Company Analysis | `Analyse Apple (AAPL) stock` |
| Company Analysis | `Show me Microsoft (MSFT) financials` |
| Company Analysis | `What is Tesla's revenue?` |
| Finance FAQ | `What is a P/E ratio?` |
| Finance FAQ | `Explain EBITDA` |
| Finance FAQ | `How does market capitalisation work?` |

---

## Disclaimer

> FinSight AI provides financial information **for informational purposes only**.  
> It does **not** constitute investment advice, and no content should be relied upon for making investment decisions.  
> Always consult a qualified financial advisor before making investment decisions.

---

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
