"""
config.py – Load environment variables from .env for FinSight AI.
All API keys and configuration are read from the .env file.
Never hardcode keys here.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from the project root (parent of finsight/)
_ROOT = Path(__file__).parent.parent
load_dotenv(dotenv_path=_ROOT / ".env")


def _require(key: str) -> str:
    """Return env var value, raise if missing."""
    value = os.getenv(key)
    if not value:
        raise EnvironmentError(
            f"Required environment variable '{key}' is not set. "
            f"Please add it to your .env file."
        )
    return value


# ── LLM ─────────────────────────────────────────────────────────────────────
GEMINI_API_KEY: str = _require("GEMINI_API_KEY")

# Ensure the google-genai SDK (used internally by ADK's LlmAgent) always
# picks up the user's own API key from .env rather than any hosted quota.
# The SDK checks GOOGLE_API_KEY first; GEMINI_API_KEY is a recognised alias
# but setting GOOGLE_API_KEY explicitly guarantees priority regardless of
# SDK version.
if not os.environ.get("GOOGLE_API_KEY"):
    os.environ["GOOGLE_API_KEY"] = GEMINI_API_KEY

# ── MCP Data Sources ─────────────────────────────────────────────────────────
ALPHA_VANTAGE_API_KEY: str = _require("ALPHA_VANTAGE")
FINANCIAL_DATASET_API_KEY: str = _require("FINANCIAL_DATASET")

# ── Redis ────────────────────────────────────────────────────────────────────
REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")

# ── Models ──────────────────────────────────────────────────────────────────
GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

# ── Cache TTLs (seconds) ─────────────────────────────────────────────────────
PRICE_CACHE_TTL: int = int(os.getenv("PRICE_CACHE_TTL", "30"))
FINANCIAL_CACHE_TTL: int = int(os.getenv("FINANCIAL_CACHE_TTL", str(24 * 3600)))
HISTORY_MAX_TURNS: int = int(os.getenv("HISTORY_MAX_TURNS", "50"))

# ── Flask ────────────────────────────────────────────────────────────────────
FLASK_SECRET_KEY: str = os.getenv("FLASK_SECRET_KEY", "finsight-dev-secret-change-me")
FLASK_DEBUG: bool = os.getenv("FLASK_DEBUG", "false").lower() == "true"
FLASK_PORT: int = int(os.getenv("FLASK_PORT", "5000"))
