"""
summary_agent.py – Node 4 (final) in the FinSight AI graph pipeline.

Responsibility (single):
  Merge the outputs of all specialist agents (FAQ or Analysis) into
  a single, well-formatted, concise final response.
  Always appends the mandatory educational disclaimer.

Routing logic:
  - Skipped entirely if guardrail_result == "BLOCKED" (returns block message).
  - Skipped if route_decision == "OFF_TOPIC" (returns polite decline).
  - Otherwise merges faq_result or analysis_result.

Output: writes the final user-facing response to session.state["final_response"].

System prompt: prompts/summary.md
"""

from pathlib import Path
from typing import Optional

from google.adk.agents import LlmAgent
from google.adk.agents.callback_context import CallbackContext
from google.genai import types

from finsight.config import GEMINI_MODEL

# ── Load system prompt from file ─────────────────────────────────────────────
_PROMPT_PATH = Path(__file__).parent.parent.parent / "prompts" / "summary.md"
_SUMMARY_PROMPT = _PROMPT_PATH.read_text(encoding="utf-8")

_SYSTEM_PROMPT = f"""{_SUMMARY_PROMPT}

You will receive the outputs of the upstream specialist agents in the session state.
Your task:

1. Read session.state to understand what route was taken:
   - "faq_result"      contains the FAQ agent's explanation (if route was FAQ)
   - "analysis_result" contains the Analysis agent's report (if route was ANALYSIS)

2. Merge any non-empty agent outputs into one clean, readable response.

3. Format the response clearly using markdown:
   - Use headers (##) for sections
   - Use bullet points for lists
   - Bold key numbers and metrics

4. ALWAYS append this disclaimer as the final line, exactly as written:
   ---
   *For educational purposes only. Not financial advice.*

5. Keep the tone professional and neutral.
6. Do not repeat information unnecessarily.
7. If both results are empty (which should not happen), politely ask the user to rephrase.
"""

# ── Pre-built responses for special routes ───────────────────────────────────

_BLOCKED_RESPONSE = types.Content(
    role="model",
    parts=[types.Part(text=(
        "⚠️ Your request has been blocked by our safety guardrail.\n\n"
        "FinSight AI is designed for financial research and education only. "
        "Please rephrase your question and focus on financial topics such as "
        "stock analysis, company financials, or finance concepts.\n\n"
        "---\n*For educational purposes only. Not financial advice.*"
    ))],
)

_OFF_TOPIC_RESPONSE = types.Content(
    role="model",
    parts=[types.Part(text=(
        "I'm sorry, but that question is outside my area of expertise. 🎯\n\n"
        "FinSight AI specialises in **financial research and education**. "
        "I can help you with:\n"
        "- 📊 Company stock analysis (e.g., \"Analyse Apple stock\")\n"
        "- 📚 Finance concept explanations (e.g., \"What is P/E ratio?\")\n"
        "- 💹 Financial metrics (EPS, EBITDA, ROE, Market Cap)\n\n"
        "Please ask a finance-related question and I'll be happy to help!\n\n"
        "---\n*For educational purposes only. Not financial advice.*"
    ))],
)


# ── before_agent_callback: handle special routes before LLM call ─────────────

def _handle_special_routes(callback_context: CallbackContext) -> Optional[types.Content]:
    """
    Short-circuit the summary agent for BLOCKED and OFF_TOPIC routes.
    For these cases we return a pre-built response without calling the LLM.
    """
    state = callback_context.state
    guardrail = state.get("guardrail_result", "").strip().upper()
    route = state.get("route_decision", "").strip().upper()

    if guardrail == "BLOCKED" or route == "BLOCKED":
        state["final_response"] = _BLOCKED_RESPONSE.parts[0].text
        return _BLOCKED_RESPONSE

    if route == "OFF_TOPIC":
        state["final_response"] = _OFF_TOPIC_RESPONSE.parts[0].text
        return _OFF_TOPIC_RESPONSE

    return None  # proceed to LLM summarization


# ── Agent definition ─────────────────────────────────────────────────────────
summary_agent = LlmAgent(
    name="SummaryAgent",
    model=GEMINI_MODEL,
    instruction=_SYSTEM_PROMPT,
    description=(
        "Summary agent: merges specialist agent outputs into a single, "
        "clean, formatted response. Always appends the educational disclaimer."
    ),
    before_agent_callback=_handle_special_routes,
    output_key="final_response",   # written to session.state["final_response"]
)
