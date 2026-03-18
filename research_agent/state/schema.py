# state/schema.py
"""
All Pydantic output models and the LangGraph GraphState TypedDict.
Nothing else — no logic, no LLM calls.
"""

import operator
from typing import Annotated, Any, Dict, List, Literal, Optional, TypedDict

from pydantic import BaseModel, Field


# ══════════════════════════════════════════════════════════════════════════════
# Worker output models
# ══════════════════════════════════════════════════════════════════════════════

class TopicClarifierOutput(BaseModel):
    clarified_topic: str = Field(description="Clear, specific research topic")
    research_scope: List[str] = Field(
        default=[],
        description="3+ concrete research scope items", min_length=3
    )
    key_aspects: List[str] = Field(
        default=[],
        description="3+ actionable research questions", min_length=3
    )


class OutlineSection(BaseModel):
    section_name: str
    points: List[str] = Field(min_length=1, max_length=8)


class OutlineDesignerOutput(BaseModel):
    sections: List[OutlineSection] = Field(
        description="List of paper sections with their points"
    )


class IntroductionWriterOutput(BaseModel):
    introduction: str = Field(
        description="Full introduction text with problem statement and contributions"
    )
    key_contributions: List[str] = Field(
        default=[],
        description="3+ specific, measurable contributions"
    )


class BackgroundWriterOutput(BaseModel):
    background: Optional[str] = Field(
        default=None,
        description="Background text explaining foundational concepts with citations"
    )
    key_concepts: Optional[List[str]] = Field(
        default=None,
        description="List of key concepts covered"
    )


class LiteratureReviewWriterOutput(BaseModel):
    literature_review: str = Field(
        description="Literature review text with comparisons, trends, and citations"
    )
    covered_themes: List[str] = Field(default=[],description="Main themes covered in the review")


class ResearchGap(BaseModel):
    gap: str          = Field(description="Specific, concrete research gap")
    justification: str = Field(description="Why this is a gap based on literature")


class ResearchGapIdentifierOutput(BaseModel):
    research_gaps: List[ResearchGap] = Field(
        default=[],
        description="3+ specific research gaps with justifications", min_length=3
    )


class MethodologyDesignerOutput(BaseModel):
    methodology: Optional[Dict[str, Any]] = Field( default=None,
        description="Methodology details: research_approach, data_sources, analysis_techniques"
    )


class ResultsWriterOutput(BaseModel):
    results_section: str = Field(
        description="Results section with data, statistics, and analysis"
    )
    results_type: Literal["actual", "expected"] = Field(
        default="expected",
        description="Whether these are actual or expected/placeholder results",
    )


class DiscussionWriterOutput(BaseModel):
    discussion: str   = Field(description="Discussion text interpreting results")
    limitations: str  = Field(description="Specific limitations of the study")
    future_work: List[str] = Field(default=[],description="Concrete future research directions")


class ConclusionWriterOutput(BaseModel):
    conclusion: str = Field(description="Conclusion text summarising contributions")
    key_takeaways: List[str] = Field(
        default=[],
        description="3+ key takeaways from the research", min_length=3
    )


class ReferencesWriterOutput(BaseModel):
    references:     List[str]      = Field(default=[],   description="List of formatted references")
    citation_count: Optional[int]  = Field(default=None, description="Total number of references")
    citation_style: Optional[str]  = Field(default=None, description="Citation style used (APA, IEEE, MLA…)")

class CitationFormatterOutput(BaseModel):
    formatted_citations: str  = Field(description="Formatted citations text")
    formatting_notes: List[str] = Field(default=[],description="Notes on citation formatting changes")


# ── Control / meta models ─────────────────────────────────────────────────────

class WorkerSummaryOutput(BaseModel):
    summary: str = Field(description="2–3 sentence summary of worker output")


class WorkerEvaluationOutput(BaseModel):
    quality_score: float          = Field(ge=0.0, le=1.0)
    passed: bool
    decision: Literal["accept", "retry"]
    issues: List[str]      = Field(default_factory=list, max_length=10)
    suggestions: List[str] = Field(default_factory=list, max_length=10)


class PlannerDecisionOutput(BaseModel):
    next_worker: str  = Field(description="Name of the next worker to execute")
    worker_input: str = Field(default="", description="Context for the next worker")
    reasoning: str    = Field(default="",description="Why this worker was chosen")


class EvaluationIssue(BaseModel):
    section: str                              = Field(description="Section with the issue")
    issue: str                                = Field(description="Issue description")
    severity: Literal["low", "medium", "high"] = Field(description="Issue severity")


class ResearchEvaluationOutput(BaseModel):
    overall_score: float           = Field(ge=0.0, le=1.0)
    section_scores: Dict[str, float]
    issues: List[EvaluationIssue]  = Field(default=[])
    missing_sections: List[str]    = Field(default=[])
    citation_gaps: List[str]       = Field(default=[])
    decision: Literal["accept", "replan"]


class ReplanningOutput(BaseModel):
    replanning_needed: bool = Field(description="Whether replanning is needed")
    priority_fixes: List[Dict[str, str]] = Field(
        default=[], description="Priority fixes: target_workers, issues"
    )


# ══════════════════════════════════════════════════════════════════════════════
# Runtime types
# ══════════════════════════════════════════════════════════════════════════════

class WorkerMetrics(TypedDict):
    execution_count:     int
    success_count:       int
    failure_count:       int
    last_execution_time: Optional[str]
    last_output:         Optional[Any]
    last_error:          Optional[str]
    is_circuit_broken:   bool
    circuit_break_count: int


class GraphState(TypedDict):
    """Full LangGraph state with safety tracking."""

    # ── User Input ────────────────────────────────────────────────────────────
    user_input:        str
    user_requirements: Optional[str]
    citation_style:    str

    # ── Research Artefacts ────────────────────────────────────────────────────
    clarified_topic:   Optional[Any]
    outline:           Optional[Dict[str, Any]]
    introduction:      Optional[Any]
    background:        Optional[Any]
    literature_review: Optional[Any]
    key_sources:       Optional[List[str]]
    research_gaps:     Optional[Any]
    methodology:       Optional[Dict[str, Any]]
    results:           Optional[Any]
    discussion:        Optional[Any]
    conclusion:        Optional[Any]
    references:        Optional[Any]
    references_formatted: bool

    # ── Control Flow ──────────────────────────────────────────────────────────
    next_worker:           Optional[str]
    worker_input:          Optional[str]
    final_paper:           Optional[Dict[str, Any]]
    execution_history:     List[Dict[str, Any]]
    current_worker:        Optional[str]
    worker_summaries:      Dict[str, Dict[str, Any]]
    worker_evaluations:    Dict[str, Dict[str, Any]]
    last_worker_evaluation: Optional[Dict[str, Any]]

    # ── Safety Tracking ───────────────────────────────────────────────────────
    total_steps:                    int
    planner_call_count:             int
    worker_metrics:                 Dict[str, WorkerMetrics]
    consecutive_failures:           int
    circuit_breaker_active:         bool
    circuit_breaker_cooldown_remaining: int

    # ── Evaluation ────────────────────────────────────────────────────────────
    evaluation_result:   Optional[Dict[str, Any]]
    replanning_context:  Optional[Dict[str, Any]]

    # ── Errors / Warnings (Annotated so LangGraph appends rather than replaces)
    errors:   Annotated[List[str], operator.add]
    warnings: Annotated[List[str], operator.add]

    # ── Termination ───────────────────────────────────────────────────────────
    force_terminate:     bool
    termination_reason:  Optional[str]
