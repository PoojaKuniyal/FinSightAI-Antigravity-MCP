"""
pipeline.py – ADK 2.0 Graph Pipeline for FinSight AI.

Assembles all five independent agents into a SequentialAgent graph.
Each agent is a node; session.state["output_key"] acts as the edges.

Graph topology:
  GuardrailAgent  →  RouterAgent  →  FAQAgent  ─┐
                                  →  AnalysisAgent ─┤→ SummaryAgent
                                  (conditional via before_agent_callback)

State flow:
  guardrail_result  : "SAFE" | "BLOCKED"
  route_decision    : "FAQ" | "ANALYSIS" | "OFF_TOPIC" | "BLOCKED"
  faq_result        : str (FAQ answer or "")
  analysis_result   : str (financial report or "")
  final_response    : str (merged, formatted, with disclaimer)
"""

import logging

from google.adk.agents import SequentialAgent

from finsight.agents.guardrail_agent import guardrail_agent
from finsight.agents.router_agent import router_agent
from finsight.agents.faq_agent import faq_agent
from finsight.agents.analysis_agent import analysis_agent
from finsight.agents.summary_agent import summary_agent

log = logging.getLogger(__name__)

# ── FinSight AI Graph Pipeline ────────────────────────────────────────────────
#
# SequentialAgent executes sub_agents in order, sharing a single
# InvocationContext (and its session.state) across all nodes.
# Conditional logic (FAQ vs ANALYSIS vs OFF_TOPIC) is handled inside
# each node via before_agent_callback — the graph definition itself
# is clean and declarative.
#
finsight_pipeline = SequentialAgent(
    name="FinSightAIPipeline",
    description=(
        "FinSight AI – Multi-Agent Equity Research Assistant. "
        "Executes: Guardrail → Router → [FAQ | Analysis] → Summary"
    ),
    sub_agents=[
        guardrail_agent,    # Node 1: safety check
        router_agent,       # Node 2: intent classification
        faq_agent,          # Node 3a: finance FAQ (conditional)
        analysis_agent,     # Node 3b: company analysis (conditional)
        summary_agent,      # Node 4: merge + disclaimer
    ],
)

# Expose the pipeline as the ADK root agent
root_agent = finsight_pipeline

log.info(
    "FinSight AI pipeline assembled: %d agents",
    len(finsight_pipeline.sub_agents),
)
