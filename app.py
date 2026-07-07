"""
app.py – Flask web server for FinSight AI.

Endpoints:
  GET  /                 – Serve the chat UI
  POST /api/chat         – Run the ADK pipeline on a user message
  GET  /api/history      – Return chat history for the current session
  POST /api/clear        – Clear chat history for the current session
  GET  /api/status       – Health check (Redis, API keys)

The ADK pipeline is run synchronously via asyncio.run() so Flask's
standard WSGI mode works without async frameworks.
"""

import asyncio
import logging
import os
import uuid
from pathlib import Path

from flask import Flask, jsonify, render_template, request, session
from flask_cors import CORS

# ── Load env before importing finsight modules ───────────────────────────────
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")

from finsight.config import (
    FLASK_SECRET_KEY,
    FLASK_DEBUG,
    FLASK_PORT,
    GEMINI_API_KEY,
)
from finsight.redis_session import (
    append_history,
    clear_history,
    get_history,
    is_redis_available,
)

# ── ADK imports ───────────────────────────────────────────────────────────────
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types as adk_types

# ── Pipeline import ───────────────────────────────────────────────────────────
from finsight.graph.pipeline import root_agent

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.DEBUG if FLASK_DEBUG else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger(__name__)

# ── Flask app setup ───────────────────────────────────────────────────────────
app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = FLASK_SECRET_KEY
CORS(app)

# ── ADK session service & runner ──────────────────────────────────────────────
_session_service = InMemorySessionService()
_APP_NAME = "finsight_ai"

_runner = Runner(
    agent=root_agent,
    app_name=_APP_NAME,
    session_service=_session_service,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_or_create_session_id() -> str:
    """Return the Flask session ID, creating one if absent."""
    if "session_id" not in session:
        session["session_id"] = str(uuid.uuid4())
    return session["session_id"]


def _build_execution_path(state: dict) -> list[str]:
    """
    Derive the ordered list of agent names that actually executed for this
    query, based on session state keys written by each agent.

    Possible paths:
      BLOCKED  : ["Guardrail", "Blocked"]
      FAQ      : ["Guardrail", "Router", "FAQ", "Summary"]
      ANALYSIS : ["Guardrail", "Router", "Company Analysis", "Summary"]
      OFF_TOPIC: ["Guardrail", "Router", "Summary"]
      (fallback): ["Guardrail", "Router", "Summary"]
    """
    guardrail = state.get("guardrail_result", "").strip().upper()
    route = state.get("route_decision", "").strip().upper()

    if guardrail == "BLOCKED" or route == "BLOCKED":
        return ["Guardrail", "Blocked"]

    path = ["Guardrail", "Router"]

    if route == "FAQ":
        path.append("FAQ")
    elif route == "ANALYSIS":
        path.append("Company Analysis")
    # OFF_TOPIC goes straight to Summary (no specialist agent)

    path.append("Summary")
    return path


async def _run_pipeline(session_id: str, user_message: str) -> tuple[str, list[str]]:
    """
    Run the ADK SequentialAgent pipeline and return (response_text, execution_path).
    Creates or reuses an ADK session keyed by the Flask session ID.

    IMPORTANT: SequentialAgent emits a final_response event for EACH sub-agent.
    We must NOT break on the first event — we need the SummaryAgent's response
    (the last one). We collect all events and use the last non-empty final text.
    """
    # Ensure the ADK session exists
    adk_session = await _session_service.get_session(
        app_name=_APP_NAME, user_id="user", session_id=session_id
    )
    if adk_session is None:
        adk_session = await _session_service.create_session(
            app_name=_APP_NAME, user_id="user", session_id=session_id
        )

    # Build the user content
    content = adk_types.Content(
        role="user",
        parts=[adk_types.Part(text=user_message)],
    )

    # Collect ALL final-response events — SequentialAgent emits one per sub-agent.
    # We want the LAST non-empty one, which comes from SummaryAgent.
    final_text = ""
    async for event in _runner.run_async(
        user_id="user",
        session_id=session_id,
        new_message=content,
    ):
        if event.is_final_response():
            if event.content and event.content.parts:
                candidate = "".join(
                    p.text for p in event.content.parts if hasattr(p, "text") and p.text
                ).strip()
                if candidate:
                    log.debug(
                        "final_response event from agent, text preview: %.80s",
                        candidate,
                    )
                    final_text = candidate  # keep overwriting — last non-empty wins

    # Read session state to derive execution path and fallback response
    refreshed = await _session_service.get_session(
        app_name=_APP_NAME, user_id="user", session_id=session_id
    )
    state = refreshed.state if (refreshed and refreshed.state) else {}

    # Fallback: read final_response from session state (set by SummaryAgent output_key)
    if not final_text:
        final_text = state.get("final_response", "")
        if final_text:
            log.debug("Used session state fallback for final_response")

    if not final_text:
        final_text = "I was unable to generate a response. Please try again."

    execution_path = _build_execution_path(state)
    log.debug("Execution path: %s", " → ".join(execution_path))

    return final_text, execution_path



# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    """Serve the main chat UI."""
    return render_template("index.html")


@app.route("/api/chat", methods=["POST"])
def chat():
    """Process a user message through the ADK pipeline."""
    data = request.get_json(force=True, silent=True) or {}
    user_message = (data.get("message") or "").strip()

    if not user_message:
        return jsonify({"error": "Message cannot be empty."}), 400

    session_id = _get_or_create_session_id()

    try:
        # Run the async ADK pipeline in a synchronous context
        response_text, execution_path = asyncio.run(_run_pipeline(session_id, user_message))
    except Exception as exc:
        log.exception("Pipeline error for session %s", session_id)
        return jsonify({"error": f"Pipeline error: {str(exc)}"}), 500

    # Persist to Redis history
    append_history(session_id, "user", user_message)
    append_history(session_id, "assistant", response_text)

    return jsonify({
        "session_id": session_id,
        "response": response_text,
        "execution_path": execution_path,
    })


@app.route("/api/history", methods=["GET"])
def history():
    """Return the chat history for the current session."""
    session_id = _get_or_create_session_id()
    return jsonify({
        "session_id": session_id,
        "history": get_history(session_id),
    })


@app.route("/api/clear", methods=["POST"])
def clear():
    """Clear chat history for the current session."""
    session_id = _get_or_create_session_id()
    clear_history(session_id)
    # Also reset the Flask session so a new ADK session is created
    session.pop("session_id", None)
    return jsonify({"message": "Conversation cleared."})


@app.route("/api/status", methods=["GET"])
def status():
    """Health check endpoint."""
    return jsonify({
        "status": "ok",
        "app": "FinSight AI",
        "redis": "connected" if is_redis_available() else "unavailable (in-memory fallback)",
        "gemini_api_key_set": bool(GEMINI_API_KEY),
        "pipeline": root_agent.name,
        "agents": [a.name for a in root_agent.sub_agents],
    })


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    log.info("Starting FinSight AI on port %d", FLASK_PORT)
    app.run(
        host="0.0.0.0",
        port=FLASK_PORT,
        debug=FLASK_DEBUG,
        use_reloader=False,  # disable reloader to avoid duplicate MCP subprocesses
    )
