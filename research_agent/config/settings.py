
"""
Central configuration for the Research Paper Agent.
All tunable parameters live here — no magic numbers elsewhere.
"""

from typing import Dict


class SafetyConfig:
    """Execution safety limits and circuit-breaker thresholds."""

    # ── Step / call limits ────────────────────────────────────────────────────
    MAX_TOTAL_STEPS: int       = 80   # Hard cap on total LangGraph steps
    MAX_WORKER_RETRIES: int    = 4    # Max retries for a single worker
    MAX_PLANNER_CALLS: int     = 60   # Max planner invocations per run

    # ── Circuit breaker ───────────────────────────────────────────────────────
    MAX_CONSECUTIVE_FAILURES: int   = 3   # Failures before circuit trips
    CIRCUIT_BREAKER_COOLDOWN: int   = 5   # Steps to wait before re-enabling

    # ── Per-worker execution limits ───────────────────────────────────────────
    WORKER_EXECUTION_LIMITS: Dict[str, int] = {
        "topic_clarifier":          3,
        "outline_designer":         3,
        "introduction_writer":      3,
        "background_writer":        3,
        "literature_review_writer": 4,
        "research_gap_identifier":  3,
        "methodology_designer":     3,
        "results_writer":           3,
        "discussion_writer":        3,
        "conclusion_writer":        3,
        "references_writer":        3,
        "research_evaluation":      5,   # Allow more for iterative evaluation
    }

    # ── Termination ───────────────────────────────────────────────────────────
    ENABLE_FALLBACK: bool          = True
    FORCE_TERMINATE_ON_LIMIT: bool = True


class EvaluationConfig:
    """Per-worker evaluator settings."""

    ENABLE_PER_WORKER_EVAL: bool = True
    QUALITY_THRESHOLD: float     = 0.65   # Minimum score to pass (0–1)
    MAX_RETRIES_PER_WORKER: int  = 3      # Max times to retry same worker


class LLMConfig:
    """LLM provider and model settings."""

    MODEL: str           = "openai.gpt-oss-120b-1:0"
    FALLBACK_MODEL: str  = "amazon.nova-lite-v1:0"
    AWS_REGION:     str   = "us-east-1"
    DEFAULT_TEMPERATURE: float = 0.7

    # Per-role temperatures (override default where precision matters)
    TEMPERATURES: Dict[str, float] = {
        "planner":    0.3,
        "evaluator":  0.3,
        "summarizer": 0.2,
        "replanning": 0.2,
        # Workers default to 0.6–0.7 (set individually in their modules)
    }
