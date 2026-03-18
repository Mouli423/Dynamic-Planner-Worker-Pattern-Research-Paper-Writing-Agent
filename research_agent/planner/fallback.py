# planner/fallback.py
"""
Fallback handler — activated when safety limits are reached or errors occur.
Attempts graceful termination while preserving whatever was produced.
"""

from research_agent.state.schema import GraphState
from research_agent.utils.logger import log


def fallback_handler(state: GraphState) -> GraphState:
    """
    Gracefully terminate the pipeline, logging what was completed.
    """
    log.safety("FALLBACK HANDLER ACTIVATED")

    reason = state.get("termination_reason", "Unknown safety limit reached")

    artifacts = {k: state.get(k) for k in [
        "clarified_topic", "outline", "introduction", "background",
        "literature_review", "research_gaps", "methodology",
        "results", "discussion", "conclusion", "references",
    ]}
    completed = sum(1 for v in artifacts.values() if v is not None)

    message = (
        f"\nFALLBACK TERMINATION\n"
        f"Reason: {reason}\n"
        f"Total Steps: {state.get('total_steps', 0)}\n"
        f"Completed Artifacts: {completed}/11\n"
        f"Status: Partial completion — work saved\n"
    )
    log.warning(message)

    return {
        **state,
        "force_terminate":    True,
        "termination_reason": reason,
        "warnings":           [message],
        "execution_history":  [{
            "node":             "fallback_handler",
            "action":           "graceful_termination",
            "reason":           reason,
            "artifacts_saved":  completed,
        }],
    }
