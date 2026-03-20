
"""
Final research evaluation node — evaluates the complete assembled paper.
"""

from datetime import datetime

from langchain_core.messages import HumanMessage, SystemMessage

from research_agent.config import SafetyConfig
from research_agent.llm import get_llm_with_structure, get_fallback_llm
from research_agent.prompts.evaluator_prompts import RESEARCH_EVALUATOR_PROMPT
from research_agent.state.schema import GraphState, ResearchEvaluationOutput
from research_agent.utils.helpers import (
    blocked_worker_state,
    check_worker_can_execute,
    update_worker_metrics,
)
from research_agent.utils.logger import log

_WORKER = "research_evaluation"


def research_evaluator(state: GraphState) -> GraphState:
    """Evaluate the complete research paper and decide accept or replan."""
    can_run, reason = check_worker_can_execute(state, _WORKER)
    if not can_run:
        return blocked_worker_state(state, reason)

    log.info("--- RESEARCH_EVALUATOR ---")

    evaluator_input = {k: state.get(k) for k in [
        "clarified_topic", "outline", "introduction", "background",
        "literature_review", "research_gaps", "methodology",
        "results", "discussion", "conclusion", "references",
    ]}

    
    try:
        # llm = get_llm_with_structure(ResearchEvaluationOutput, temperature=0.3)
        # result  = llm.invoke([
        #     SystemMessage(content=RESEARCH_EVALUATOR_PROMPT),
        #     HumanMessage(content=f"Evaluation input:\n{evaluator_input}"),
        # ])

        try:
            llm    = get_llm_with_structure(ResearchEvaluationOutput, temperature=0.3)
            result  = llm.invoke([
            SystemMessage(content=RESEARCH_EVALUATOR_PROMPT),
            HumanMessage(content=f"Evaluation input:\n{evaluator_input}"),
        ])
            if result is None:
                raise ValueError("Primary returned None")
        except Exception as exc:
            log.warning(f"Primary failed: {exc} — using fallback")
            llm    = get_fallback_llm(ResearchEvaluationOutput, temperature=0.3)
            result  = llm.invoke([
            SystemMessage(content=RESEARCH_EVALUATOR_PROMPT),
            HumanMessage(content=f"Evaluation input:\n{evaluator_input}"),
        ])

        metrics = update_worker_metrics(state, _WORKER, success=True, output=result.model_dump())
        log.success(f"Research evaluation complete — score={result.overall_score:.2f} decision={result.decision}")

        return {
            "evaluation_result":  result.model_dump(),
            "worker_metrics":     metrics,
            "total_steps":        state.get("total_steps", 0) + 1,
            "consecutive_failures": 0,
            "execution_history":  [{
                "worker":    _WORKER,
                "status":    "success",
                "timestamp": datetime.now().isoformat(),
            }],
        }

    except Exception as exc:
        log.error(f"{_WORKER} failed", exc=exc)
        consecutive = state.get("consecutive_failures", 0) + 1
        metrics     = update_worker_metrics(state, _WORKER, success=False, error=str(exc))

        if consecutive >= SafetyConfig.MAX_CONSECUTIVE_FAILURES:
            log.circuit_breaker("Activated", worker_name=_WORKER, consecutive=consecutive)

        return {
            "worker_metrics":      metrics,
            "total_steps":         state.get("total_steps", 0) + 1,
            "consecutive_failures": consecutive,
            "errors":              [f"{_WORKER} failed: {exc}"],
            "execution_history":   [{
                "worker":    _WORKER,
                "status":    "failure",
                "error":     str(exc),
                "timestamp": datetime.now().isoformat(),
            }],
        }
