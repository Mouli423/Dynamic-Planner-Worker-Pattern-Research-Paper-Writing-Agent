
"""
Per-worker quality evaluator node.
Runs after every summarizer call to decide accept / retry.
"""

from langchain_core.messages import HumanMessage, SystemMessage

from research_agent.config import EvaluationConfig
from research_agent.llm import get_llm_with_structure
from research_agent.prompts.evaluator_prompts import get_worker_evaluation_prompt
from research_agent.state.schema import GraphState, WorkerEvaluationOutput
from research_agent.utils.logger import log

_OUTPUT_MAP = {
    "topic_clarifier":          "clarified_topic",
    "outline_designer":         "outline",
    "introduction_writer":      "introduction",
    "background_writer":        "background",
    "literature_review_writer": "literature_review",
    "research_gap_identifier":  "research_gaps",
    "methodology_designer":     "methodology",
    "results_writer":           "results",
    "discussion_writer":        "discussion",
    "conclusion_writer":        "conclusion",
    "references_writer":        "references",
}


def evaluate_worker_output(state: GraphState) -> GraphState:
    """Evaluate the latest worker's output and record the result in state."""
    if not EvaluationConfig.ENABLE_PER_WORKER_EVAL:
        return state

    current_worker = state.get("current_worker")
    if not current_worker:
        return state

    output_key    = _OUTPUT_MAP.get(current_worker)
    worker_output = state.get(output_key) if output_key else None

    if not worker_output:
        log.warning(f"No output from {current_worker} — automatic fail")
        evaluation = {
            "worker_name":   current_worker,
            "quality_score": 0.0,
            "passed":        False,
            "issues":        ["No output produced"],
            "suggestions":   [f"{current_worker} must produce output"],
            "decision":      "retry",
        }
        return {**state, "last_worker_evaluation": evaluation}

    # Check existing retry count for this worker
    worker_evals = state.get("worker_evaluations", {})
    prev_eval    = worker_evals.get(current_worker, {})
    retry_count  = prev_eval.get("retry_count", 0)

    if retry_count >= EvaluationConfig.MAX_RETRIES_PER_WORKER:
        log.warning(f"Max retries reached for {current_worker} — accepting as-is")
        return state

    llm = get_llm_with_structure(WorkerEvaluationOutput, temperature=0.3)
    prompt = get_worker_evaluation_prompt(current_worker)

    try:
        response = llm.invoke([
            SystemMessage(content=prompt),
            HumanMessage(content=(
                f"Worker: {current_worker}\n\n"
                f"FULL OUTPUT TO EVALUATE:\n{worker_output}\n\n"
                f"Evaluate based on the SPECIFIC criteria for {current_worker}."
            )),
        ])
        eval_data     = response.model_dump()
        quality_score = eval_data.get("quality_score", 0.5)
        passed        = quality_score >= EvaluationConfig.QUALITY_THRESHOLD
        decision      = "accept" if passed else "retry"

        evaluation = {
            "worker_name":   current_worker,
            "quality_score": quality_score,
            "passed":        passed,
            "issues":        eval_data.get("issues", [])[:8],
            "suggestions":   eval_data.get("suggestions", [])[:8],
            "decision":      decision,
            "retry_count":   retry_count,
        }

        log.evaluation(current_worker, quality_score, decision, evaluation["issues"])

        return {
            **state,
            "worker_evaluations":    {**worker_evals, current_worker: evaluation},
            "last_worker_evaluation": evaluation,
        }

    except Exception as exc:
        log.error(f"Evaluation error for {current_worker}", exc=exc)
        return {
            **state,
            "last_worker_evaluation": {
                "worker_name":   current_worker,
                "quality_score": 0.0,
                "passed":        False,
                "issues":        [],
                "suggestions":   [],
                "decision":      "retry",
                "retry_count":   retry_count,
            },
        }
