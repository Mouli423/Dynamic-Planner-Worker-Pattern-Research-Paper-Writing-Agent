"""
main.py
=======
Entry point for the Research Paper Agent.

Run:
    python main.py

Or import and call run_pipeline() from another script / notebook.
"""

import os
from pathlib import Path
import json
from dotenv import load_dotenv
load_dotenv()

from research_agent.api_key_store.ssm_parameters import get_api_key
# ── Environment ───────────────────────────────────────────────────────────────


os.environ["LANGSMITH_API_KEY"]=get_api_key()
os.environ["LANGCHAIN_TRACING_V2"]="true"
os.environ["LANGCHAIN_PROJECT"]="Dynamic Planner Worker Research Paper Writing Agent"
os.environ["LANGSMITH_MAX_CONTENT_LENGTH"] = "5000"
# ── Logging (must be configured before any agent imports) ─────────────────────
from research_agent.utils.logger import log, setup_logging
setup_logging(log_dir="logs", log_file="agent.log")

# ── Agent imports ─────────────────────────────────────────────────────────────
from research_agent.config import SafetyConfig
from research_agent.graph import build_graph
from research_agent.state import initialize_safe_state

def save_paper(final_paper: dict, partial: bool = False):
    """Write the assembled paper to output/."""
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)

    suffix = "_partial" if partial else ""
    md_path   = output_dir / f"final_paper{suffix}.md"
    json_path = output_dir / f"final_paper{suffix}.json"

    md_path.write_text(final_paper["markdown"], encoding="utf-8")
    json_path.write_text(json.dumps(final_paper, indent=2, default=str), encoding="utf-8")

    wc = final_paper["metadata"]["word_count"]
    log.success(f"📄  {'Partial p' if partial else 'P'}aper saved → {md_path}  ({wc:,} words)")
    log.success(f"📦  Structured data  → {json_path}")


def run_pipeline(
    topic: str,
    citation_style: str = "APA",
    user_requirements: str = None,
    recursion_limit: int = 100,
) -> dict:
    """
    Run the full research-paper pipeline for a given topic.

    Parameters
    ----------
    topic              : research topic / user request
    citation_style     : "APA" | "IEEE" | "MLA" (default "APA")
    user_requirements  : optional free-text constraints
    recursion_limit    : LangGraph recursion cap

    Returns
    -------
    final_state : dict — the completed GraphState
    """
    log.pipeline_start(topic)
    log.info(
        f"Safety config — max_steps={SafetyConfig.MAX_TOTAL_STEPS}  "
        f"max_retries={SafetyConfig.MAX_WORKER_RETRIES}  "
        f"circuit_breaker={SafetyConfig.MAX_CONSECUTIVE_FAILURES}"
    )

    state = initialize_safe_state(
        topic,
        citation_style=citation_style,
        user_requirements=user_requirements,
    )
    graph = build_graph()

    try:
        final_state = graph.invoke(state, config={"recursion_limit": recursion_limit})
    except Exception as exc:
        log.critical(f"Pipeline crashed: {exc}", exc_info=True)
        raise

    # ── Summary ───────────────────────────────────────────────────────────────
    log.pipeline_end(
        total_steps   = final_state.get("total_steps", 0),
        planner_calls = final_state.get("planner_call_count", 0),
        outcome       = final_state.get("termination_reason", "Completed successfully"),
        workers_done  = len(final_state.get("worker_summaries", {})),
    )

    for worker, wm in final_state.get("worker_metrics", {}).items():
        if wm["execution_count"] > 0:
            log.info(
                f"  {worker}: {wm['execution_count']}x  "
                f"(✓{wm['success_count']} ✗{wm['failure_count']})"
            )

        # ── Save output ───────────────────────────────────────────────────────────
    final_paper = final_state.get("final_paper")

    if final_paper:
        save_paper(final_paper)
    else:
        # Pipeline hit fallback — assemble whatever sections we have
        log.warning("output_generator did not run (pipeline hit fallback). "
                    "Assembling partial paper from available sections...")
        from research_agent.output_generator import generate_output
        try:
            patched = generate_output(final_state)
            save_paper(patched["final_paper"], partial=True)
        except Exception as exc:
            log.error(f"Could not assemble partial paper: {exc}")


    return final_state


# ── CLI entry point ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    final_state = run_pipeline(
        topic="Design a research paper on how the software development lifecycle is going to change with respect to the effect of AI Agents and Agentic AI systems",
        citation_style="APA",
    )
