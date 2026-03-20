# planner/planner.py
"""
Planner and replanning nodes.
"""

import json

from langchain_core.messages import HumanMessage, SystemMessage

from research_agent.config import SafetyConfig
from research_agent.llm import get_llm_with_structure,get_fallback_llm
from research_agent.prompts import PLANNER_SYSTEM_PROMPT, REPLANNING_PROMPT
from research_agent.state.schema import GraphState, PlannerDecisionOutput, ReplanningOutput
from research_agent.utils.helpers import check_global_limits
from research_agent.utils.logger import log


def research_planner(state: GraphState) -> GraphState:
    """
    Core planning node — decides which worker to run next.
    Enforces global step / call limits, then asks the LLM for a routing decision.
    Falls back to a force-terminate if limits are exceeded or an error occurs.
    """
    step = state.get("total_steps", 0)
    log.planner("Planner invoked", step=step)

    # ── Safety guards ──────────────────────────────────────────────────────────
    if state.get("total_steps", 0) >= SafetyConfig.MAX_TOTAL_STEPS:
        log.safety("Max total steps reached", f"{SafetyConfig.MAX_TOTAL_STEPS} steps")
        return {
            **state,
            "force_terminate":    True,
            "termination_reason": f"Max steps reached ({SafetyConfig.MAX_TOTAL_STEPS})",
            "next_worker":        "fallback",
        }

    if state.get("planner_call_count", 0) >= SafetyConfig.MAX_PLANNER_CALLS:
        log.safety("Max planner calls reached", f"{SafetyConfig.MAX_PLANNER_CALLS} calls")
        return {
            **state,
            "force_terminate":    True,
            "termination_reason": f"Max planner calls reached ({SafetyConfig.MAX_PLANNER_CALLS})",
            "next_worker":        "fallback",
        }

    # ── Build planner context ─────────────────────────────────────────────────
    summaries   = state.get("worker_summaries", {})
    last_eval   = state.get("last_worker_evaluation")
    should_retry= last_eval and last_eval.get("decision") == "retry"

    summary_list = [
        {
            "worker":  w,
            "summary": s.get("summary", ""),
            "status":  s.get("completion_status", ""),
        }
        for w, s in summaries.items()
    ]

    planner_input: dict = {
        "user_topic":         state.get("user_input", ""),
        "completed_workers":  list(summaries.keys()),
        "already_formatted":  state.get("references_formatted", False),
        "summaries":          summary_list,
        "retry_needed":       bool(should_retry),
        "retry_worker":       last_eval.get("worker_name") if should_retry else None,
        "retry_suggestions":  last_eval.get("suggestions", []) if should_retry else [],
    }

    replanning = state.get("replanning_context", "")
    if replanning:
        planner_input["replanning_context"] = replanning

    # ── LLM call ──────────────────────────────────────────────────────────────
    
    try:
        # llm = get_llm_with_structure(PlannerDecisionOutput, temperature=0.3)
        # result   = llm.invoke([
        #     SystemMessage(content=PLANNER_SYSTEM_PROMPT),
        #     HumanMessage(content=(
        #         f"State: {json.dumps(planner_input, indent=2)}\n\n"
        #         "Decide next worker. Use summaries for context.\n"
        #         "Use retry_suggestions when retrying the same worker.\n"
        #         "If replanning_context is present, apply it as feedback."
        #     )),
        # ])

        try:
            llm    = get_llm_with_structure(PlannerDecisionOutput, temperature=0.3)
            result   = llm.invoke([
            SystemMessage(content=PLANNER_SYSTEM_PROMPT),
            HumanMessage(content=(
                f"State: {json.dumps(planner_input, indent=2)}\n\n"
                "Decide next worker. Use summaries for context.\n"
                "Use retry_suggestions when retrying the same worker.\n"
                "If replanning_context is present, apply it as feedback."
            )),
        ])
            if result is None:
                raise ValueError("Primary returned None")
        except Exception as exc:
            log.warning(f"Primary failed: {exc} — using fallback")
            llm    = get_fallback_llm(PlannerDecisionOutput, temperature=0.3)
            result   = llm.invoke([
            SystemMessage(content=PLANNER_SYSTEM_PROMPT),
            HumanMessage(content=(
                f"State: {json.dumps(planner_input, indent=2)}\n\n"
                "Decide next worker. Use summaries for context.\n"
                "Use retry_suggestions when retrying the same worker.\n"
                "If replanning_context is present, apply it as feedback."
            )),
        ])

        response = result.model_dump()
        log.planner(
            f"Decision: → {response.get('next_worker')}  | Reasoning → {response.get('reasoning', '')} | Worker_input → {response.get("worker_input")}"
        )

        return {
            **state,
            "next_worker":        response.get("next_worker"),
            "worker_input":       response.get("worker_input"),
            "planner_call_count": state.get("planner_call_count", 0) + 1,
            "replanning_context": "",      # clear after use
            "execution_history":  [{
                "node":      "planner",
                "decision":  response.get("next_worker"),
                "reasoning": response.get("reasoning", ""),
            }],
        }

    except Exception as exc:
        log.error("Planner error", exc=exc)
        return {
            **state,
            "next_worker":        "fallback",
            "force_terminate":    True,
            "termination_reason": f"Planner error: {exc}",
            "errors":             [f"Planner failed: {exc}"],
        }


def replanning(state: GraphState) -> GraphState:
    """
    Replanning controller — interprets evaluation failures
    and prepares corrective guidance for the planner.
    """
    log.info("--- REPLANNING ---")
    llm = get_llm_with_structure(ReplanningOutput, temperature=0.2)

    replanning_input = {
        "evaluation_result": state.get("evaluation_result"),
        "execution_history": state.get("execution_history"),
        "retry_count":       state.get("retry_count", {}),
    }

    try:
        # llm = get_llm_with_structure(ReplanningOutput, temperature=0.2)
        # result = llm.invoke([
        #     SystemMessage(content=REPLANNING_PROMPT),
        #     HumanMessage(content=f"Replanning input:\n{replanning_input}"),
        # ])
        try:
            llm    = get_llm_with_structure(ReplanningOutput, temperature=0.2)
            result = llm.invoke([
            SystemMessage(content=REPLANNING_PROMPT),
            HumanMessage(content=f"Replanning input:\n{replanning_input}"),
        ])
            if result is None:
                raise ValueError("Primary returned None")
            
        except Exception as exc:
            log.warning(f"Primary failed: {exc} — using fallback")
            llm    = get_fallback_llm(ReplanningOutput, temperature=0.2)
            result = llm.invoke([
            SystemMessage(content=REPLANNING_PROMPT),
            HumanMessage(content=f"Replanning input:\n{replanning_input}"),
        ])
        log.debug(f"Replanning result: {result.model_dump()}")
        return {
            "replanning_context": result.model_dump(),
            "execution_history":  [{"replanning": result.model_dump()}],
        }
    except Exception as exc:
        log.error("Replanning error", exc=exc)
        return {"replanning_context": {}}
