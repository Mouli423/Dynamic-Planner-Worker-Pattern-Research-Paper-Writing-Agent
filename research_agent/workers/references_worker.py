# workers/references_worker.py
"""
References writer — extracts citations from all paper sections,
then asks the LLM to generate a formatted references list.
"""

import json
import re
from datetime import datetime

from langchain_core.messages import HumanMessage, SystemMessage

from research_agent.config import SafetyConfig
from research_agent.llm import get_llm_with_structure
from research_agent.prompts import GENERIC_REFERENCES_WRITER_PROMPT
from research_agent.state.schema import GraphState, ReferencesWriterOutput
from research_agent.utils.helpers import (
    blocked_worker_state,
    check_worker_can_execute,
    update_worker_metrics,
)
from research_agent.utils.logger import log

_WORKER = "references_writer"

_PATTERNS = [
    # [Author et al., 2020] or [Author & Co, 2020]
    r'\[([A-Z][a-zA-Z\-\.\s]+(?:et\s+al\.?|&[^\]]+)?\s*,\s*\d{4})\]',
    # (Author et al., 2020) or (Author & Co, 2020) or (OpenAI, 2023)
    r'\(([A-Z][a-zA-Z\-\.\s]+(?:et\s+al\.?|&[^\)]+)?\s*,\s*\d{4})\)',
    # Author et al. (2020) — author-year style outside brackets
    r'([A-Z][a-zA-Z\-]+(?:\s+(?:et\s+al\.|&\s+[A-Z][a-zA-Z\-]+))?)\.?\s*\((\d{4})\)',
    # IEEE numeric [1], [12]
    r'\[(\d{1,3})\]',
]

# def _extract_citations(state: GraphState) -> list[str]:
#     sections = {
#         "clarified_topic":  state.get("clarified_topic"),
#         "introduction":     state.get("introduction"),
#         "background":       state.get("background"),
#         "literature_review":state.get("literature_review"),
#         "methodology":      state.get("methodology"),
#         "results":          state.get("results"),
#         "discussion":       state.get("discussion"),
#         "conclusion":       state.get("conclusion"),
#     }
#     all_text = " ".join(
#         json.dumps(v) if isinstance(v, dict) else str(v)
#         for v in sections.values() if v
#     )
#     found: list[str] = []
#     for pat in _PATTERNS:
#         found.extend(re.findall(pat, all_text))
#     return list(dict.fromkeys(found))   # deduplicate, preserve order

def _extract_citations(text: str) -> list:
    found = []
    for pat in _PATTERNS:
        matches = re.findall(pat, text)
        for m in matches:
            # re.findall returns tuples for multi-group patterns
            if isinstance(m, tuple):
                # Author-year style: groups are (author, year)
                author, year = m[0].strip(), m[1].strip()
                if author and year:
                    found.append(f"{author}, {year}")
            else:
                found.append(m)

    # Deduplicate, skip pure numbers (IEEE refs are reconstructed from context)
    # Final safety net: coerce everything to str so join() never crashes on tuples
    seen, unique = set(), []
    for c in found:
        # Extra guard: if a tuple somehow survived, join it into "Author, Year"
        if isinstance(c, tuple):
            c = ", ".join(str(x).strip() for x in c if x)
        key = str(c).strip()
        if key and key not in seen and not key.isdigit():
            seen.add(key)
            unique.append(key)
    return unique

def _collect_all_text(state: dict) -> str:
    keys = ["introduction", "background", "literature_review", "research_gaps",
            "methodology", "results", "discussion", "conclusion"]
    parts = []
    for k in keys:
        v = state.get(k)
        if v:
            parts.append(json.dumps(v) if isinstance(v, dict) else str(v))
    return " ".join(parts)

def references_writer(state: GraphState) -> GraphState:
    can_run, reason = check_worker_can_execute(state, _WORKER)
    if not can_run:
        return blocked_worker_state(state, reason)

    log.worker(_WORKER, "Starting citation extraction", status="running")

    citations = _extract_citations(_collect_all_text(state))
    log.info(f"Extracted {len(citations)} unique citations")
    if citations:
        log.debug(f"Citation sample: {', '.join(citations[:10])}")
    topic=state.get("clarified_topic")
    citation_style  = state.get("citation_style", "APA")
    sections_present= [k for k in [
        "clarified_topic", "introduction", "background", "literature_review",
        "methodology", "results", "discussion", "conclusion",
    ] if state.get(k)]

    human_msg = (
        f"Paper topic: {topic}\n\n"
        f"Citation Style: {citation_style}\n\n"
        f"Extracted citations: {', '.join(citations)}\n"
        f"Total unique citations: {len(citations)}\n\n"
        f"Paper sections present: {sections_present}\n\n"
        f"Task: Generate formatted references for these citations.\n"
        f"- Use accurate details for well-known work\n"
        f"- Use [Generic Prior Work] for unrecognised work\n"
        f"- Format in {citation_style} style\n"
        f"- Aim for {max(15, len(citations))} total references\n\n"
        f"Every title must relate to this topic — not unrelated fields.\n\n"
        "CRITICAL: DO NOT assume research domain! Only use citations actually found."
    )

    llm = get_llm_with_structure(ReferencesWriterOutput, temperature=0.2)
    messages = [
        SystemMessage(content=GENERIC_REFERENCES_WRITER_PROMPT),
        HumanMessage(content=human_msg),
    ]

    try:
        result  = llm.invoke(messages)
        metrics = update_worker_metrics(state, _WORKER, success=True, output=result)
        log.worker(_WORKER, "References generated", status="success",worker_output=result)

        return {
            **state,
            "references":          result,
            "references_formatted": True,
            "current_worker":      _WORKER,
            "worker_metrics":      metrics,
            "total_steps":         state.get("total_steps", 0) + 1,
            "consecutive_failures": 0,
        }

    except Exception as exc:
        log.error(f"{_WORKER} failed", exc=exc)
        consecutive = state.get("consecutive_failures", 0) + 1
        metrics     = update_worker_metrics(state, _WORKER, success=False, error=str(exc))

        if consecutive >= SafetyConfig.MAX_CONSECUTIVE_FAILURES:
            log.circuit_breaker("Activated", worker_name=_WORKER, consecutive=consecutive)

        return {
            **state,
            "worker_metrics":      metrics,
            "total_steps":         state.get("total_steps", 0) + 1,
            "consecutive_failures": consecutive,
            "errors":              [f"{_WORKER} failed: {exc}"],
            "execution_history":   [{
                "worker":    _WORKER,
                "status":    "failure",
                "error":     str(exc),
                "timestamp": datetime.now().isoformat(),
            }],
        }


# workers/references_worker.py
# """
# References writer.

# Root cause of original failures:
# - Regex only captured citation KEYS like "Chen et al., 2018"
# - LLM received a bare comma-separated list with no surrounding context
# - Evaluator applied strict format checks to inherently placeholder citations

# Fixes applied:
# - Better citation extraction with numbered list input
# - Explicit per-style formatting instructions with concrete examples
# - Lower temperature (0.1) for consistent formatting
# - Execution limit raised to 4 in config/settings.py
# """

# import json
# import re
# from datetime import datetime

# from langchain_core.messages import HumanMessage, SystemMessage

# from research_agent.config import SafetyConfig
# from research_agent.llm import get_llm_with_structure
# from research_agent.state.schema import GraphState, ReferencesWriterOutput
# from research_agent.utils.helpers import (
#     blocked_worker_state,
#     check_worker_can_execute,
#     update_worker_metrics,
# )
# from research_agent.utils.logger import log

# _WORKER = "references_writer"

# _PATTERNS = [
#     # [Author et al., 2020] or [Author & Co, 2020]
#     r'\[([A-Z][a-zA-Z\-\.\s]+(?:et\s+al\.?|&[^\]]+)?\s*,\s*\d{4})\]',
#     # (Author et al., 2020) or (Author & Co, 2020) or (OpenAI, 2023)
#     r'\(([A-Z][a-zA-Z\-\.\s]+(?:et\s+al\.?|&[^\)]+)?\s*,\s*\d{4})\)',
#     # Author et al. (2020) — author-year style outside brackets
#     r'([A-Z][a-zA-Z\-]+(?:\s+(?:et\s+al\.|&\s+[A-Z][a-zA-Z\-]+))?)\.?\s*\((\d{4})\)',
#     # IEEE numeric [1], [12]
#     r'\[(\d{1,3})\]',
# ]

# # _SYSTEM_PROMPT = """You are writing the References section of an academic research paper.

# # ## YOUR TASK
# # Generate ONE properly formatted reference entry for EACH citation key provided.

# # ## FORMATTING — {style} STYLE

# # APA example:
# #   Chen, J., & Wang, L. (2018). Deep learning for enterprise IT systems. IEEE Transactions on Software Engineering, 44(3), 245-261. https://doi.org/10.1109/TSE.2018.001

# # IEEE example:
# #   [1] J. Chen and L. Wang, "Deep learning for enterprise IT systems," IEEE Trans. Softw. Eng., vol. 44, no. 3, pp. 245-261, 2018.

# # ## STRICT RULES
# # 1. Use the SAME format for EVERY reference — no mixing styles
# # 2. Use your training knowledge for well-known works (accurate details)
# # 3. For unknown works, construct a plausible entry and append [Simulated] at the end
# # 4. Every entry MUST have: author(s), year, title, and venue
# # 5. Sort alphabetically by first author surname (APA) or by citation number (IEEE)


# # Requested style: {style}
# # Number of references to generate: {count}


# # CRITICAL: Return ONLY structured output. No explanations. No tags.
# # """


# def _collect_all_text(state: dict) -> str:
#     keys = ["introduction", "background", "literature_review", "research_gaps",
#             "methodology", "results", "discussion", "conclusion"]
#     parts = []
#     for k in keys:
#         v = state.get(k)
#         if v:
#             parts.append(json.dumps(v) if isinstance(v, dict) else str(v))
#     return " ".join(parts)


# def _extract_citations(text: str) -> list:
#     found = []
#     for pat in _PATTERNS:
#         matches = re.findall(pat, text)
#         for m in matches:
#             # re.findall returns tuples for multi-group patterns
#             if isinstance(m, tuple):
#                 # Author-year style: groups are (author, year)
#                 author, year = m[0].strip(), m[1].strip()
#                 if author and year:
#                     found.append(f"{author}, {year}")
#             else:
#                 found.append(m)

#     # Deduplicate, skip pure numbers (IEEE refs are reconstructed from context)
#     # Final safety net: coerce everything to str so join() never crashes on tuples
#     seen, unique = set(), []
#     for c in found:
#         # Extra guard: if a tuple somehow survived, join it into "Author, Year"
#         if isinstance(c, tuple):
#             c = ", ".join(str(x).strip() for x in c if x)
#         key = str(c).strip()
#         if key and key not in seen and not key.isdigit():
#             seen.add(key)
#             unique.append(key)
#     return unique


# def references_writer(state: GraphState) -> GraphState:
#     can_run, reason = check_worker_can_execute(state, _WORKER)
#     if not can_run:
#         return blocked_worker_state(state, reason)

#     log.worker(_WORKER, "Scanning paper for citations", status="running")

#     citations = _extract_citations(_collect_all_text(state))
#     log.info(f"[{_WORKER}] Found {len(citations)} unique citation keys")
#     if citations:
#         log.debug(f"[{_WORKER}] Keys: {citations[:10]}")

#     if not citations:
#         log.warning(f"[{_WORKER}] No citations found — using generic placeholders")
#         citations = [f"Generic Author et al., 202{i}" for i in range(5)]

#     citation_style = state.get("citation_style", "APA")
#     numbered       = "\n".join(f"{i+1}. {c}" for i, c in enumerate(citations))

#     # system_prompt = _SYSTEM_PROMPT.format(
#     #     style=citation_style, count=len(citations)
#     # )
#     human_msg = (
#         f"Generate a formatted {citation_style} reference for each of the "
#         f"{len(citations)} citation keys below.\n\n"
#         f"CITATION KEYS:\n{numbered}\n\n"
#         f"Use {citation_style} format consistently for every entry."
#     )

#     llm = get_llm_with_structure(ReferencesWriterOutput, temperature=0.1)
#     try:
#         result  = llm.invoke([SystemMessage(content=GENERIC_REFERENCES_WRITER_PROMPT),
#                               HumanMessage(content=human_msg)])
#         print(result)
#         output  = result.model_dump()
#         metrics = update_worker_metrics(state, _WORKER, success=True, output=output)
#         log.worker(_WORKER, "Generated references", status="success")

#         return {
#             **state,
#             "references":           output,
#             "references_formatted": True,
#             "current_worker":       _WORKER,
#             "worker_metrics":       metrics,
#             "total_steps":          state.get("total_steps", 0) + 1,
#             "consecutive_failures": 0,
#             "execution_history": [{"worker": _WORKER, "status": "success",
#                                    "timestamp": datetime.now().isoformat()}],
#         }

#     except Exception as exc:
#         log.error(f"{_WORKER} failed", exc=exc)
#         consecutive = state.get("consecutive_failures", 0) + 1
#         metrics     = update_worker_metrics(state, _WORKER, success=False, error=str(exc))
#         if consecutive >= SafetyConfig.MAX_CONSECUTIVE_FAILURES:
#             log.circuit_breaker("Activated", worker_name=_WORKER, consecutive=consecutive)
#         return {
#             **state,
#             "worker_metrics":       metrics,
#             "total_steps":          state.get("total_steps", 0) + 1,
#             "consecutive_failures": consecutive,
#             "errors":               [f"{_WORKER} failed: {exc}"],
#             "execution_history": [{"worker": _WORKER, "status": "failure",
#                                    "error": str(exc), "timestamp": datetime.now().isoformat()}],
#         }
