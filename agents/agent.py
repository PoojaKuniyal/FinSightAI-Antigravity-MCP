"""
agent.py – ADK Web Playground entry-point for FinSight AI.

This file satisfies ADK's agent discovery when adk web is pointed at the
project root:

    adk web .          (from stock_analysis_agent/)  ← app name: "agents"
    adk web agents/    (from stock_analysis_agent/)  ← discovers finsight_ai/

Both paths expose the same root_agent.

Correct structure:
    stock_analysis_agent/          ← agents_dir for  adk web .
      agents/                      ← agent named "agents"
        agent.py                   ← this file (root_agent exposed here)
        finsight_ai/
          agent.py                 ← also valid for  adk web agents/
"""

import sys
from pathlib import Path

# Project root = parent of agents/
_PROJECT_ROOT = Path(__file__).parent.parent   # agents/ → stock_analysis_agent/
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

# Load .env before any finsight imports (required for GEMINI_API_KEY, etc.)
from dotenv import load_dotenv                 # noqa: E402
_env_path = _PROJECT_ROOT / ".env"
if _env_path.exists():
    load_dotenv(dotenv_path=_env_path, override=False)

# Import the fully-assembled pipeline — this also triggers GOOGLE_API_KEY
# aliasing in finsight/config.py so the user's own key is always used.
from finsight.graph.pipeline import root_agent  # noqa: F401, E402

__all__ = ["root_agent"]
