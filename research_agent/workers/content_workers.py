# workers/content_workers.py

from research_agent.state.schema import (
    TopicClarifierOutput, OutlineDesignerOutput,
    IntroductionWriterOutput, BackgroundWriterOutput,
    LiteratureReviewWriterOutput, ResearchGapIdentifierOutput,
    MethodologyDesignerOutput, ResultsWriterOutput,
    DiscussionWriterOutput, ConclusionWriterOutput, GraphState,
)
from research_agent.prompts import (
    TOPIC_CLARIFIER_PROMPT, OUTLINE_DESIGNER_PROMPT,
    INTRODUCTION_WRITER_PROMPT, BACKGROUND_WRITER_PROMPT,
    LITERATURE_REVIEW_WRITER_PROMPT, RESEARCH_GAP_IDENTIFIER_PROMPT,
    METHODOLOGY_DESIGNER_PROMPT, RESULTS_WRITER_PROMPT,
    DISCUSSION_WRITER_PROMPT, CONCLUSION_WRITER_PROMPT,
)
from .base import run_worker


def topic_clarifier(state: GraphState) -> GraphState:
    return run_worker(
        state=state, worker_name="topic_clarifier",
        output_model=TopicClarifierOutput, temperature=0.7,
        system_prompt=TOPIC_CLARIFIER_PROMPT,
        human_message=f"Input context:\n{state.get('worker_input', '')}",
        output_key="clarified_topic",
    )

def outline_designer(state: GraphState) -> GraphState:
    return run_worker(
        state=state, worker_name="outline_designer",
        output_model=OutlineDesignerOutput, temperature=0.7,
        system_prompt=OUTLINE_DESIGNER_PROMPT,
        human_message=f"Input context:\n{state.get('worker_input', '')}",
        output_key="outline",
    )

def introduction_writer(state: GraphState) -> GraphState:
    return run_worker(
        state=state, worker_name="introduction_writer",
        output_model=IntroductionWriterOutput, temperature=0.6,
        system_prompt=INTRODUCTION_WRITER_PROMPT,
        human_message=f"Input context:\n{state.get('worker_input', '')}",
        output_key="introduction",
    )

def background_writer(state: GraphState) -> GraphState:
    return run_worker(
        state=state, worker_name="background_writer",
        output_model=BackgroundWriterOutput, temperature=0.6,
        system_prompt=BACKGROUND_WRITER_PROMPT,
        human_message=f"Input context:\n{state.get('worker_input', '')}",
        output_key="background",
        result_transform=lambda r: r,
    )

def literature_review_writer(state: GraphState) -> GraphState:
    return run_worker(
        state=state, worker_name="literature_review_writer",
        output_model=LiteratureReviewWriterOutput, temperature=0.7,
        system_prompt=LITERATURE_REVIEW_WRITER_PROMPT,
        human_message=f"Input context:\n{state.get('worker_input', '')}",
        output_key="literature_review",
    )

def research_gap_identifier(state: GraphState) -> GraphState:
    return run_worker(
        state=state, worker_name="research_gap_identifier",
        output_model=ResearchGapIdentifierOutput, temperature=0.7,
        system_prompt=RESEARCH_GAP_IDENTIFIER_PROMPT,
        human_message=f"Input context:\n{state.get('worker_input', '')}",
        output_key="research_gaps",
    )

def methodology_designer(state: GraphState) -> GraphState:
    return run_worker(
        state=state, worker_name="methodology_designer",
        output_model=MethodologyDesignerOutput, temperature=0.7,
        system_prompt=METHODOLOGY_DESIGNER_PROMPT,
        human_message=f"Input context:\n{state.get('worker_input', '')}",
        output_key="methodology",
    )

def results_writer(state: GraphState) -> GraphState:
    return run_worker(
        state=state, worker_name="results_writer",
        output_model=ResultsWriterOutput, temperature=0.7,
        system_prompt=RESULTS_WRITER_PROMPT,
        human_message=f"Input context:\n{state.get('worker_input', '')}",
        output_key="results",
    )

def discussion_writer(state: GraphState) -> GraphState:
    return run_worker(
        state=state, worker_name="discussion_writer",
        output_model=DiscussionWriterOutput, temperature=0.6,
        system_prompt=DISCUSSION_WRITER_PROMPT,
        human_message=f"Input context:\n{state.get('worker_input', '')}",
        output_key="discussion",
        result_transform=lambda r: r,
    )

def conclusion_writer(state: GraphState) -> GraphState:
    return run_worker(
        state=state, worker_name="conclusion_writer",
        output_model=ConclusionWriterOutput, temperature=0.6,
        system_prompt=CONCLUSION_WRITER_PROMPT,
        human_message=f"Input context:\n{state.get('worker_input', '')}",
        output_key="conclusion",
        result_transform=lambda r: r,
    )