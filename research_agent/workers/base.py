# workers/base.py
"""
Shared execution pattern for all worker nodes.

Each worker calls `run_worker()` which handles:
- Pre-execution safety checks
- LLM invocation
- Success / failure state merging
- Logging
"""

from datetime import datetime
from typing import Any, Callable, Optional, Type

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel

from research_agent.state.schema import GraphState
from research_agent.utils.helpers import (
    blocked_worker_state,
    check_worker_can_execute,
    update_worker_metrics,
)
from research_agent.utils.logger import log
from research_agent.config import SafetyConfig


def run_worker(
    state: GraphState,
    worker_name: str,
    llm,                        # structured-output LLM
    system_prompt: str,
    human_message: str,
    output_key: str,            # which GraphState key gets the result
    result_transform: Optional[Callable[[Any], Any]] = None,
) -> GraphState:
    """
    Standard worker execution wrapper.

    Parameters
    ----------
    state            : current graph state
    worker_name      : e.g. "topic_clarifier"
    llm              : result of get_llm_with_structure(...)
    system_prompt    : the worker's system prompt string
    human_message    : the human-turn message string
    output_key       : state key to store the result in
    result_transform : optional function to post-process the model result
                       before storing (default: .model_dump())
    """
    # ── Safety gate ───────────────────────────────────────────────────────────
    can_run, reason = check_worker_can_execute(state, worker_name)
    if not can_run:
        return blocked_worker_state(state, reason)

    log.worker(worker_name, "Starting", status="running")

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=human_message),
    ]

    try:
        result  = llm.invoke(messages)
        output  = result
        metrics = update_worker_metrics(state, worker_name, success=True, output=output)

        log.worker(worker_name, "Completed successfully", status="success" , worker_output=output)

        return {
            **state,
            output_key:          output,
            "current_worker":    worker_name,
            "worker_metrics":    metrics,
            "total_steps":       state.get("total_steps", 0) + 1,
            "consecutive_failures": 0,
            "execution_history": [{
                "worker":    worker_name,
                "status":    "success",
                "timestamp": datetime.now().isoformat(),
            }],
        }

    except Exception as exc:
        log.error(f"{worker_name} failed", exc=exc)

        metrics             = update_worker_metrics(state, worker_name, success=False, error=str(exc))
        consecutive         = state.get("consecutive_failures", 0) + 1

        if consecutive >= SafetyConfig.MAX_CONSECUTIVE_FAILURES:
            log.circuit_breaker("Activated", worker_name=worker_name, consecutive=consecutive)

        return {
            **state,
            "worker_metrics":    metrics,
            "total_steps":       state.get("total_steps", 0) + 1,
            "consecutive_failures": consecutive,
            "errors":            [f"{worker_name} failed: {exc}"],
            "execution_history": [{
                "worker":    worker_name,
                "status":    "failure",
                "error":     str(exc),
                "timestamp": datetime.now().isoformat(),
            }],
        }
