"""
redis_session.py – Redis-backed session state, chat history, and data caching.

Caching strategy (per requirements.md):
  - Chat history   : JSON list per session_id, no TTL (persists until cleared)
  - Session state  : JSON dict per session_id
  - Price cache    : 30-second TTL  (PRICE_CACHE_TTL)
  - Financial cache: 24-hour TTL    (FINANCIAL_CACHE_TTL)

Falls back to in-memory dict if Redis is unavailable, so the app
continues to work without a Redis server running.
"""

import json
import logging
from typing import Any, Optional

import redis

from finsight.config import (
    REDIS_URL,
    PRICE_CACHE_TTL,
    FINANCIAL_CACHE_TTL,
    HISTORY_MAX_TURNS,
)

log = logging.getLogger(__name__)

# ── Redis client (lazy, with fallback) ──────────────────────────────────────

_redis_client: Optional[redis.Redis] = None
_memory_fallback: dict[str, Any] = {}   # in-memory fallback store


def _get_client() -> Optional[redis.Redis]:
    global _redis_client
    if _redis_client is not None:
        return _redis_client
    try:
        client = redis.from_url(REDIS_URL, decode_responses=True, socket_connect_timeout=2)
        client.ping()  # verify connection
        _redis_client = client
        log.info("Redis connected: %s", REDIS_URL)
    except Exception as exc:
        log.warning("Redis unavailable (%s). Using in-memory fallback.", exc)
        _redis_client = None
    return _redis_client


# ── Internal helpers ─────────────────────────────────────────────────────────

def _set(key: str, value: Any, ttl: Optional[int] = None) -> None:
    """Serialize and store a value; falls back to memory."""
    serialized = json.dumps(value)
    client = _get_client()
    if client:
        try:
            if ttl:
                client.setex(key, ttl, serialized)
            else:
                client.set(key, serialized)
            return
        except Exception as exc:
            log.warning("Redis SET error: %s", exc)
    # fallback
    _memory_fallback[key] = {"value": serialized, "ttl": ttl}


def _get(key: str) -> Optional[Any]:
    """Retrieve and deserialize a stored value; falls back to memory."""
    client = _get_client()
    if client:
        try:
            raw = client.get(key)
            return json.loads(raw) if raw else None
        except Exception as exc:
            log.warning("Redis GET error: %s", exc)
    # fallback
    entry = _memory_fallback.get(key)
    return json.loads(entry["value"]) if entry else None


def _delete(key: str) -> None:
    client = _get_client()
    if client:
        try:
            client.delete(key)
            return
        except Exception as exc:
            log.warning("Redis DELETE error: %s", exc)
    _memory_fallback.pop(key, None)


# ── Public API ───────────────────────────────────────────────────────────────

# Chat History ----------------------------------------------------------------

def get_history(session_id: str) -> list[dict]:
    """Return the chat history list for a session."""
    return _get(f"history:{session_id}") or []


def append_history(session_id: str, role: str, content: str) -> None:
    """Append a single turn to the session's chat history (capped at max turns)."""
    history = get_history(session_id)
    history.append({"role": role, "content": content})
    # Cap to HISTORY_MAX_TURNS
    if len(history) > HISTORY_MAX_TURNS:
        history = history[-HISTORY_MAX_TURNS:]
    _set(f"history:{session_id}", history)


def clear_history(session_id: str) -> None:
    """Delete the chat history for a session."""
    _delete(f"history:{session_id}")


# Session State ---------------------------------------------------------------

def get_session_state(session_id: str) -> dict:
    """Return the session state dict."""
    return _get(f"session:{session_id}") or {}


def set_session_state(session_id: str, state: dict) -> None:
    """Overwrite the session state."""
    _set(f"session:{session_id}", state)


def update_session_state(session_id: str, updates: dict) -> None:
    """Merge updates into the existing session state."""
    state = get_session_state(session_id)
    state.update(updates)
    set_session_state(session_id, state)


# Price Cache -----------------------------------------------------------------

def get_price_cache(symbol: str) -> Optional[dict]:
    """Return cached price data for a ticker symbol (30-second TTL)."""
    return _get(f"price:{symbol.upper()}")


def set_price_cache(symbol: str, data: dict) -> None:
    """Cache price data for a ticker symbol with 30-second TTL."""
    _set(f"price:{symbol.upper()}", data, ttl=PRICE_CACHE_TTL)


# Financial Cache -------------------------------------------------------------

def get_financial_cache(symbol: str, data_type: str) -> Optional[dict]:
    """Return cached financial data (24-hour TTL).
    data_type: 'overview' | 'income' | 'balance' | 'cashflow'
    """
    return _get(f"financial:{data_type}:{symbol.upper()}")


def set_financial_cache(symbol: str, data_type: str, data: dict) -> None:
    """Cache financial data with 24-hour TTL."""
    _set(f"financial:{data_type}:{symbol.upper()}", data, ttl=FINANCIAL_CACHE_TTL)


# Health check ----------------------------------------------------------------

def is_redis_available() -> bool:
    """Return True if Redis is reachable."""
    return _get_client() is not None
