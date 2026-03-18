# workers/content_workers.py
"""
All content-writing worker nodes.
Each function is a LangGraph node: (GraphState) -> GraphState.
"""

from research_agent.llm import get_llm_with_structure
from research_agent.prompts import (
    TOPIC_CLARIFIER_PROMPT,
    OUTLINE_DESIGNER_PROMPT,
    INTRODUCTION_WRITER_PROMPT,
    BACKGROUND_WRITER_PROMPT,
    LITERATURE_REVIEW_WRITER_PROMPT,
    RESEARCH_GAP_IDENTIFIER_PROMPT,
    METHODOLOGY_DESIGNER_PROMPT,
    RESULTS_WRITER_PROMPT,
    DISCUSSION_WRITER_PROMPT,
    CONCLUSION_WRITER_PROMPT,
)
from research_agent.state.schema import (
    TopicClarifierOutput,
    OutlineDesignerOutput,
    IntroductionWriterOutput,
    BackgroundWriterOutput,
    LiteratureReviewWriterOutput,
    ResearchGapIdentifierOutput,
    MethodologyDesignerOutput,
    ResultsWriterOutput,
    DiscussionWriterOutput,
    ConclusionWriterOutput,
    GraphState,
)
from .base import run_worker


# ── 1. Topic Clarifier ────────────────────────────────────────────────────────

def topic_clarifier(state: GraphState) -> GraphState:
    return run_worker(
        state        = state,
        worker_name  = "topic_clarifier",
        llm          = get_llm_with_structure(TopicClarifierOutput, temperature=0.7),
        system_prompt= TOPIC_CLARIFIER_PROMPT,
        human_message= f"Input context:\n{state.get('worker_input', '')}",
        output_key   = "clarified_topic",
    )


# ── 2. Outline Designer ───────────────────────────────────────────────────────

def outline_designer(state: GraphState) -> GraphState:
    return run_worker(
        state        = state,
        worker_name  = "outline_designer",
        llm          = get_llm_with_structure(OutlineDesignerOutput, temperature=0.7),
        system_prompt= OUTLINE_DESIGNER_PROMPT,
        human_message= f"Input context:\n{state.get('worker_input', '')}",
        output_key   = "outline",
    )


# ── 3. Introduction Writer ────────────────────────────────────────────────────

def introduction_writer(state: GraphState) -> GraphState:
    return run_worker(
        state        = state,
        worker_name  = "introduction_writer",
        llm          = get_llm_with_structure(IntroductionWriterOutput, temperature=0.6),
        system_prompt= INTRODUCTION_WRITER_PROMPT,
        human_message= f"Input context:\n{state.get('worker_input', '')}",
        output_key   = "introduction",
    )


# ── 4. Background Writer ──────────────────────────────────────────────────────

def background_writer(state: GraphState) -> GraphState:
    return run_worker(
        state        = state,
        worker_name  = "background_writer",
        llm          = get_llm_with_structure(BackgroundWriterOutput, temperature=0.6),
        system_prompt= BACKGROUND_WRITER_PROMPT,
        human_message= f"Input context:\n{state.get('worker_input', '')}",
        output_key   = "background",
        result_transform= lambda r: r,   # background_writer returns object directly
    )


# ── 5. Literature Review Writer ───────────────────────────────────────────────

def literature_review_writer(state: GraphState) -> GraphState:
    return run_worker(
        state        = state,
        worker_name  = "literature_review_writer",
        llm          = get_llm_with_structure(LiteratureReviewWriterOutput, temperature=0.7),
        system_prompt= LITERATURE_REVIEW_WRITER_PROMPT,
        human_message= f"Input context:\n{state.get('worker_input', '')}",
        output_key   = "literature_review",
    )


# ── 6. Research Gap Identifier ────────────────────────────────────────────────

def research_gap_identifier(state: GraphState) -> GraphState:
    return run_worker(
        state        = state,
        worker_name  = "research_gap_identifier",
        llm          = get_llm_with_structure(ResearchGapIdentifierOutput, temperature=0.7),
        system_prompt= RESEARCH_GAP_IDENTIFIER_PROMPT,
        human_message= f"Input context:\n{state.get('worker_input', '')}",
        output_key   = "research_gaps",
    )


# ── 7. Methodology Designer ───────────────────────────────────────────────────

def methodology_designer(state: GraphState) -> GraphState:
    return run_worker(
        state        = state,
        worker_name  = "methodology_designer",
        llm          = get_llm_with_structure(MethodologyDesignerOutput, temperature=0.7),
        system_prompt= METHODOLOGY_DESIGNER_PROMPT,
        human_message= f"Input context:\n{state.get('worker_input', '')}",
        output_key   = "methodology",
    )


# ── 8. Results Writer ─────────────────────────────────────────────────────────

def results_writer(state: GraphState) -> GraphState:
    return run_worker(
        state        = state,
        worker_name  = "results_writer",
        llm          = get_llm_with_structure(ResultsWriterOutput, temperature=0.7),
        system_prompt= RESULTS_WRITER_PROMPT,
        human_message= f"Input context:\n{state.get('worker_input', '')}",
        output_key   = "results",
    )


# ── 9. Discussion Writer ──────────────────────────────────────────────────────

def discussion_writer(state: GraphState) -> GraphState:
    return run_worker(
        state        = state,
        worker_name  = "discussion_writer",
        llm          = get_llm_with_structure(DiscussionWriterOutput, temperature=0.6),
        system_prompt= DISCUSSION_WRITER_PROMPT,
        human_message= f"Input context:\n{state.get('worker_input', '')}",
        output_key   = "discussion",
        result_transform= lambda r: r,   # store object directly
    )


# ── 10. Conclusion Writer ─────────────────────────────────────────────────────

def conclusion_writer(state: GraphState) -> GraphState:
    return run_worker(
        state        = state,
        worker_name  = "conclusion_writer",
        llm          = get_llm_with_structure(ConclusionWriterOutput, temperature=0.6),
        system_prompt= CONCLUSION_WRITER_PROMPT,
        human_message= f"Input context:\n{state.get('worker_input', '')}",
        output_key   = "conclusion",
        result_transform= lambda r: r,   # store object directly
    )
