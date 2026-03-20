# summarizer/summarizer.py
"""
Worker summarizer node — runs after every worker, before the evaluator.
Produces a short summary stored in state["worker_summaries"][worker_name].
"""

from langchain_core.messages import HumanMessage, SystemMessage

from research_agent.llm import get_llm_with_structure, get_fallback_llm
from research_agent.prompts.evaluator_prompts import SUMMARIZER_PROMPT
from research_agent.state.schema import GraphState, WorkerSummaryOutput
from research_agent.utils.logger import log

# Map worker name → state key that holds the worker's output
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


def create_worker_summary(state: GraphState) -> GraphState:
    """Summarise the most-recently-completed worker's output for the planner."""
    current_worker = state.get("current_worker")
    if not current_worker:
        return {}

    log.info(f"Summarising output of [{current_worker}]")

    output_key    = _OUTPUT_MAP.get(current_worker)
    worker_output = state.get(output_key) if output_key else None

    if not worker_output:
        summary = {"summary": f"{current_worker} produced no output"}
    else:
        
        try:
            # llm = get_llm_with_structure(WorkerSummaryOutput, temperature=0.2)
            # response = llm.invoke([
            #     SystemMessage(content=SUMMARIZER_PROMPT),
            #     HumanMessage(content=f"Worker: {current_worker}\nOutput:\n{worker_output}"),
            # ])

            try:
                llm    = get_llm_with_structure(WorkerSummaryOutput, temperature=0.2)
                response = llm.invoke([
                SystemMessage(content=SUMMARIZER_PROMPT),
                HumanMessage(content=f"Worker: {current_worker}\nOutput:\n{worker_output}"),
            ])
                if response is None:
                    raise ValueError("Primary returned None")   
            except Exception as exc:
                log.warning(f"Primary failed: {exc} — using fallback")
                llm    = get_fallback_llm(WorkerSummaryOutput, temperature=0.2)
                response = llm.invoke([
                SystemMessage(content=SUMMARIZER_PROMPT),
                HumanMessage(content=f"Worker: {current_worker}\nOutput:\n{worker_output}"),
            ])

            summary = response.model_dump()
            log.summary(current_worker, summary["summary"])

        except Exception as exc:
            log.warning(f"Summary failed for {current_worker}: {exc}")
            summary = {"summary": f"{current_worker} completed (summary unavailable)"}

    summaries = {**state.get("worker_summaries", {}), current_worker: summary}
    return {"worker_summaries": summaries}
