# utils/helpers.py
"""
Shared helper functions — NO imports from state/ or utils/logger to avoid circular imports.
Uses plain dict type hints instead of GraphState/WorkerMetrics.
"""

from datetime import datetime
from typing import Any, Dict, Optional, Tuple

from research_agent.config import SafetyConfig


# ── Worker list (single source of truth) ──────────────────────────────────────
WORKER_LIST = [
    "topic_clarifier",
    "outline_designer",
    "introduction_writer",
    "background_writer",
    "literature_review_writer",
    "research_gap_identifier",
    "methodology_designer",
    "results_writer",
    "discussion_writer",
    "conclusion_writer",
    "references_writer",
    "research_evaluation",
]


def initialize_worker_metrics() -> Dict[str, dict]:
    """Return a fresh metrics dict for every known worker."""
    return {
        w: {
            "execution_count":     0,
            "success_count":       0,
            "failure_count":       0,
            "last_execution_time": None,
            "last_output":         None,
            "last_error":          None,
            "is_circuit_broken":   False,
            "circuit_break_count": 0,
        }
        for w in WORKER_LIST
    }


def check_worker_can_execute(
    state: dict, worker_name: str
) -> Tuple[bool, Optional[str]]:
    """
    Check all safety gates before running a worker.
    Returns (True, None) if OK, or (False, reason) if blocked.
    """
    metrics = state.get("worker_metrics", {}).get(worker_name, {})

    if metrics.get("is_circuit_broken", False):
        return False, f"Circuit breaker active for {worker_name}"

    execution_count = metrics.get("execution_count", 0)
    limit = SafetyConfig.WORKER_EXECUTION_LIMITS.get(
        worker_name, SafetyConfig.MAX_WORKER_RETRIES
    )
    if execution_count >= limit:
        return False, f"{worker_name} reached execution limit ({execution_count}/{limit})"

    if state.get("total_steps", 0) >= SafetyConfig.MAX_TOTAL_STEPS:
        return False, f"Maximum total steps reached ({SafetyConfig.MAX_TOTAL_STEPS})"

    if state.get("planner_call_count", 0) >= SafetyConfig.MAX_PLANNER_CALLS:
        return False, f"Maximum planner calls reached ({SafetyConfig.MAX_PLANNER_CALLS})"

    return True, None


def check_global_limits(state: dict) -> Tuple[bool, Optional[str]]:
    """Return (limit_reached, reason_or_None)."""
    if state.get("total_steps", 0) >= SafetyConfig.MAX_TOTAL_STEPS:
        return True, f"Max steps: {state['total_steps']}/{SafetyConfig.MAX_TOTAL_STEPS}"
    if state.get("planner_call_count", 0) >= SafetyConfig.MAX_PLANNER_CALLS:
        return True, f"Max planner calls: {state['planner_call_count']}/{SafetyConfig.MAX_PLANNER_CALLS}"
    return False, None


def update_worker_metrics(
    state: dict,
    worker_name: str,
    success: bool,
    output: Any = None,
    error: str  = None,
) -> Dict[str, dict]:
    """Return an updated worker_metrics dict. Does NOT mutate state in-place."""
    all_metrics = state.get("worker_metrics", {})
    wm = dict(all_metrics.get(worker_name, initialize_worker_metrics()[worker_name]))

    wm["execution_count"]     += 1
    wm["last_execution_time"]  = datetime.now().isoformat()

    if success:
        wm["success_count"]       += 1
        wm["last_output"]          = output
        wm["last_error"]           = None
        wm["is_circuit_broken"]    = False
        wm["circuit_break_count"]  = 0
    else:
        wm["failure_count"] += 1
        wm["last_error"]     = error
        consecutive = state.get("consecutive_failures", 0) + 1
        if consecutive >= SafetyConfig.MAX_CONSECUTIVE_FAILURES:
            wm["is_circuit_broken"]   = True
            wm["circuit_break_count"] = wm.get("circuit_break_count", 0) + 1

    return {**all_metrics, worker_name: wm}


def blocked_worker_state(state: dict, reason: str) -> dict:
    """
    Standard state patch returned when a worker is blocked by a safety check.
    Imports logger lazily to avoid circular import at module load time.
    """
    # Lazy import — logger imports nothing from utils/helpers
    from research_agent.utils.logger import log
    log.safety(f"Worker blocked: {reason}")
    return {
        **state,
        "next_worker":          "fallback",
        "force_terminate":      True,
        "termination_reason":   reason,
        "total_steps":          state.get("total_steps", 0) + 1,
        "consecutive_failures": state.get("consecutive_failures", 0) + 1,
        "errors":               [reason],
    }
