"""
agent.py – ADK Web Playground entry-point for FinSight AI.

This file follows the ADK convention required by `adk web`:
  agents_dir/<agent_folder>/agent.py  must export  root_agent

Usage:
  From the project root, run:
    adk web agents/

The playground will auto-discover this file and launch the FinSight AI
multi-agent pipeline in the browser-based chat UI.
"""

# Ensure .env is loaded and GOOGLE_API_KEY is set before any ADK code runs.
import sys
from pathlib import Path

# Add project root to sys.path so `finsight.*` imports resolve correctly.
_PROJECT_ROOT = Path(__file__).parent.parent.parent  # agents/finsight_ai/ → project root
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

# Load environment variables (must happen before importing finsight modules)
from dotenv import load_dotenv
load_dotenv(dotenv_path=_PROJECT_ROOT / ".env")

# Import the assembled pipeline — this also triggers GOOGLE_API_KEY aliasing
# in finsight/config.py, ensuring the user's own key is always used.
from finsight.graph.pipeline import root_agent  # noqa: F401  (re-exported for ADK)

__all__ = ["root_agent"]
