# state/initializer.py
"""
Factory for a clean initial GraphState.
Inlines initialize_worker_metrics to avoid circular import with utils/helpers.
"""

from research_agent.utils.helpers import initialize_worker_metrics, WORKER_LIST


def initialize_safe_state(user_input: str, **kwargs) -> dict:
    """
    Return a fully initialised GraphState dict ready for graph.invoke().

    Parameters
    ----------
    user_input         : the user's research topic
    citation_style     : "APA" (default), "IEEE", "MLA", etc.
    user_requirements  : optional constraints from the user
    """
    return {
        # User Input
        "user_input":        user_input,
        "user_requirements": kwargs.get("user_requirements"),
        "citation_style":    kwargs.get("citation_style", "APA"),

        # Research Artefacts
        "clarified_topic":    None,
        "outline":            None,
        "introduction":       None,
        "background":         None,
        "literature_review":  None,
        "key_sources":        None,
        "research_gaps":      None,
        "methodology":        None,
        "results":            None,
        "discussion":         None,
        "conclusion":         None,
        "references":         None,
        "references_formatted": False,

        # Control Flow
        "next_worker":            None,
        "worker_input":           None,
        "final_paper":            None,
        "execution_history":      [],
        "current_worker":         None,
        "worker_summaries":       {},
        "worker_evaluations":     {},
        "last_worker_evaluation": None,

        # Safety Tracking
        "total_steps":                       0,
        "planner_call_count":                0,
        "worker_metrics":                    initialize_worker_metrics(),
        "consecutive_failures":              0,
        "circuit_breaker_active":            False,
        "circuit_breaker_cooldown_remaining": 0,

        # Evaluation
        "evaluation_result":  None,
        "replanning_context": None,

        # Errors / Warnings
        "errors":   [],
        "warnings": [],

        # Termination
        "force_terminate":    False,
        "termination_reason": None,
    }
