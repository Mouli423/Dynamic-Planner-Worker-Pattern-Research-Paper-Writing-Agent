# graph/builder.py
"""
Builds and compiles the LangGraph StateGraph.

Node layout
-----------
START → planner → [worker]* → summarizer ─┐
                             → evaluator  ─┴→ post_eval → planner  (loop)
                     ↓ (on failure)
                   planner  (skip summarizer/evaluator)

planner → research_evaluation → [output_generator | replanning | fallback]
planner → fallback → END  (on safety trip)
"""

from langgraph.graph import END, START, StateGraph

from research_agent.evaluators import evaluate_worker_output, research_evaluator
from research_agent.planner import fallback_handler, replanning, research_planner
from research_agent.state.schema import GraphState
from research_agent.output_generator import generate_output
from research_agent.summarizer import create_worker_summary
from research_agent.utils.helpers import check_global_limits
from research_agent.workers import (
    background_writer,
    conclusion_writer,
    discussion_writer,
    introduction_writer,
    literature_review_writer,
    methodology_designer,
    outline_designer,
    references_writer,
    research_gap_identifier,
    results_writer,
    topic_clarifier,
)

# ── Worker list ────────────────────────────────────────────────────────────────
_CONTENT_WORKERS = [
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
]

_ALLOWED_WORKERS = set(_CONTENT_WORKERS) | {"research_evaluation"}


# ── Router functions ───────────────────────────────────────────────────────────

def planner_router(state: GraphState) -> str:
    """Route from planner to worker or fallback."""
    if state.get("force_terminate"):
        return "fallback"
    next_worker = state.get("next_worker", "")
    if not next_worker or next_worker == "fallback" or next_worker not in _ALLOWED_WORKERS:
        return "fallback"
    return next_worker


def worker_router(state: GraphState) -> str | list[str]:
    """
    Route AFTER a worker executes.

    Success path : worker → [summarizer, evaluator] in parallel → post_eval → planner
    Failure path : worker → planner  (skip summarizer/evaluator entirely)
    """
    if state.get("force_terminate"):
        return "fallback"

    history = state.get("execution_history") or []
    if history:
        last = history[-1]
        if isinstance(last, dict) and last.get("status") == "failure":
            return "planner"   # failure → skip both, go straight to planner

    # Success — fan out to both in parallel
    return ["summarizer", "evaluator"]


def post_eval_router(state: GraphState) -> str:
    """
    Route after both summarizer and evaluator have completed.
    Mirrors the old evaluation_router logic.
    """
    if state.get("force_terminate"):
        return "fallback"
    decision = (state.get("evaluation_result") or {}).get("decision", "accept")
    if decision == "accept":
        return "planner"
    limit_reached, _ = check_global_limits(state)
    return "fallback" if limit_reached else "replanning"


def evaluation_router(state: GraphState) -> str:
    """Route after research_evaluation (final paper quality check)."""
    if state.get("force_terminate"):
        return "fallback"
    decision = (state.get("evaluation_result") or {}).get("decision", "accept")
    if decision == "accept":
        return "output_generator"
    limit_reached, _ = check_global_limits(state)
    return "fallback" if limit_reached else "replanning"


# ── Join node ──────────────────────────────────────────────────────────────────

def post_eval_join(state: GraphState) -> GraphState:
    """
    Passthrough join node — LangGraph waits for BOTH summarizer and evaluator
    to complete before executing this node. Their state updates are merged
    automatically. We just pass state through to post_eval_router.
    """
    return state


# ── Graph builder ──────────────────────────────────────────────────────────────

def build_graph(checkpointer=None) -> StateGraph:
    """Construct and compile the research-agent StateGraph."""
    g = StateGraph(GraphState)

    # ── Nodes ──────────────────────────────────────────────────────────────────
    g.add_node("planner",                      research_planner)
    g.add_node("topic_clarifier",              topic_clarifier)
    g.add_node("outline_designer",             outline_designer)
    g.add_node("introduction_writer",          introduction_writer)
    g.add_node("background_writer",            background_writer)
    g.add_node("literature_review_writer",     literature_review_writer)
    g.add_node("research_gap_identifier",      research_gap_identifier)
    g.add_node("methodology_designer",         methodology_designer)
    g.add_node("results_writer",               results_writer)
    g.add_node("discussion_writer",            discussion_writer)
    g.add_node("conclusion_writer",            conclusion_writer)
    g.add_node("references_writer",            references_writer)
    g.add_node("research_evaluation",          research_evaluator)
    g.add_node("output_generator",             generate_output)
    g.add_node("replanning",                   replanning)
    g.add_node("fallback",                     fallback_handler)
    g.add_node("summarizer",                   create_worker_summary)
    g.add_node("evaluator",                    evaluate_worker_output)
    g.add_node("post_eval",                    post_eval_join)   # ← new join node

    # ── Edges ──────────────────────────────────────────────────────────────────
    g.add_edge(START, "planner")

    # planner → worker (conditional)
    g.add_conditional_edges(
        "planner",
        planner_router,
        {w: w for w in _ALLOWED_WORKERS} | {"fallback": "fallback"},
    )

    # Every content worker → fan out to summarizer + evaluator in parallel
    # OR → planner directly on failure
    for w in _CONTENT_WORKERS:
        g.add_conditional_edges(
            w,
            worker_router,
            {
                "summarizer": "summarizer",  # parallel branch 1
                "evaluator":  "evaluator",   # parallel branch 2
                "planner":    "planner",     # failure shortcut
                "fallback":   "fallback",    # force terminate
            },
        )

    # Both summarizer and evaluator feed into post_eval join node
    # LangGraph waits for both before firing post_eval
    g.add_edge("summarizer", "post_eval")
    g.add_edge("evaluator",  "post_eval")

    # post_eval → planner (accept) or replanning/fallback (reject)
    g.add_conditional_edges(
        "post_eval",
        post_eval_router,
        {
            "planner":    "planner",
            "replanning": "replanning",
            "fallback":   "fallback",
        },
    )

    # research_evaluation → final routing
    g.add_conditional_edges(
        "research_evaluation",
        evaluation_router,
        {
            "output_generator": "output_generator",
            "replanning":       "replanning",
            "fallback":         "fallback",
        },
    )

    g.add_edge("output_generator", END)
    g.add_edge("replanning",       "planner")
    g.add_edge("fallback",         END)

    return g.compile(checkpointer=checkpointer)