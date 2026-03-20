# workers/base.py

from datetime import datetime
from typing import Any, Callable, Optional, Type

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel

from research_agent.config import LLMConfig, SafetyConfig
from research_agent.llm.provider import get_fallback_llm, get_llm_with_structure
from research_agent.state.schema import GraphState
from research_agent.utils.helpers import (
    blocked_worker_state,
    check_worker_can_execute,
    update_worker_metrics,
)
from research_agent.utils.logger import log


def run_worker(
    state:            GraphState,
    worker_name:      str,
    output_model:     type[BaseModel],   # ← was: llm
    system_prompt:    str,
    human_message:    str,
    output_key:       str,
    temperature:      float = LLMConfig.DEFAULT_TEMPERATURE,  # ← new
    result_transform: Optional[Callable[[Any], Any]] = None,
) -> GraphState:

    can_run, reason = check_worker_can_execute(state, worker_name)
    if not can_run:
        return blocked_worker_state(state, reason)

    log.worker(worker_name, "Starting", status="running")

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=human_message),
    ]

    try:
        # ── Primary ───────────────────────────────────────────────────────────
        try:
            llm    = get_llm_with_structure(output_model, temperature=temperature)
            result = llm.invoke(messages)
            if result is None:
                raise ValueError(f"Primary model returned None")
        except Exception as primary_exc:
            log.warning(
                f"[{worker_name}] Primary failed: {primary_exc} "
                f"— switching to fallback ({LLMConfig.FALLBACK_MODEL})"
            )
            llm    = get_fallback_llm(output_model, temperature=temperature)
            result = llm.invoke(messages)
            if result is None:
                raise ValueError(f"Fallback model also returned None")

        output  = result_transform(result) if result_transform else result.model_dump()
        metrics = update_worker_metrics(state, worker_name, success=True, output=output)
        log.worker(worker_name, "Completed successfully", status="success", worker_output=output)

        return {
           
            output_key:              output,
            "current_worker":        worker_name,
            "worker_metrics":        metrics,
            "total_steps":           state.get("total_steps", 0) + 1,
            "consecutive_failures":  0,
            "execution_history": [{
                "worker":    worker_name,
                "status":    "success",
                "timestamp": datetime.now().isoformat(),
            }],
        }

    except Exception as exc:
        log.error(f"{worker_name} failed", exc=exc)
        metrics     = update_worker_metrics(state, worker_name, success=False, error=str(exc))
        consecutive = state.get("consecutive_failures", 0) + 1

        if consecutive >= SafetyConfig.MAX_CONSECUTIVE_FAILURES:
            log.circuit_breaker("Activated", worker_name=worker_name, consecutive=consecutive)

        return {
            
            "worker_metrics":        metrics,
            "total_steps":           state.get("total_steps", 0) + 1,
            "consecutive_failures":  consecutive,
            "errors":                [f"{worker_name} failed: {exc}"],
            "execution_history": [{
                "worker":    worker_name,
                "status":    "failure",
                "error":     str(exc),
                "timestamp": datetime.now().isoformat(),
            }],
        }