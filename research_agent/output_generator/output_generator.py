# output_generator/output_generator.py
"""
Output Generator node — assembles all worker outputs into a clean research paper.
Stored in state["final_paper"] as markdown, sections dict, and metadata.
"""

import json
import re
from datetime import datetime

from research_agent.utils.logger import log


# ── Core helpers ──────────────────────────────────────────────────────────────

def _unwrap(value):
    """Convert Pydantic model to plain dict."""
    if value is None:
        return None
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if hasattr(value, "dict") and callable(value.dict):
        return value.dict()
    return value


def _strip_repr(s: str) -> str:
    """
    Strip Pydantic repr leakage from strings.
    e.g. background='actual text...' -> actual text...
    Happens when result_transform=lambda r: r bypasses model_dump().
    """
    m = re.match(r"^[a-z_]+='(.+)'$", s, re.DOTALL)
    if m:
        return m.group(1).strip()
    m = re.match(r'^[a-z_]+="(.+)"$', s, re.DOTALL)
    if m:
        return m.group(1).strip()
    return s


def _to_str(value) -> str:
    """Convert any worker output to clean prose string."""
    value = _unwrap(value)

    if value is None:
        return ""
    if isinstance(value, str):
        return _strip_repr(value.strip())
    if isinstance(value, dict):
        for key in (
            "introduction", "background", "literature_review",
            "results_section", "results", "discussion", "conclusion",
            "clarified_topic", "text", "content", "body", "summary",
        ):
            if key in value and isinstance(value[key], str) and len(value[key]) > 30:
                return value[key].strip()
        parts = [v for v in value.values() if isinstance(v, str) and len(v) > 30]
        return "\n\n".join(parts).strip() if parts else ""
    if isinstance(value, list):
        return "\n".join(f"- {item}" for item in value if item)
    return str(value).strip()


# ── Section formatters ────────────────────────────────────────────────────────

def _format_title(ct_value, fallback: str) -> str:
    ct = _unwrap(ct_value)
    if ct is None:
        return fallback
    if isinstance(ct, str):
        ct = _strip_repr(ct.strip())
        # Handle any remaining pydantic key prefix
        if "clarified_topic='" in ct:
            try:
                start = ct.index("clarified_topic='") + len("clarified_topic='")
                end   = ct.index("'", start)
                return ct[start:end].strip()
            except ValueError:
                pass
        return ct.strip()
    if isinstance(ct, dict):
        return ct.get("clarified_topic", fallback).strip()
    return fallback


def _format_gaps(gaps_data) -> str:
    gaps_data = _unwrap(gaps_data)
    if not gaps_data:
        return ""
    if isinstance(gaps_data, str):
        return _strip_repr(gaps_data)
    if isinstance(gaps_data, dict):
        gaps = gaps_data.get("research_gaps", [])
    elif isinstance(gaps_data, list):
        gaps = gaps_data
    else:
        return _to_str(gaps_data)

    lines = []
    for i, g in enumerate(gaps, 1):
        g = _unwrap(g)
        if isinstance(g, dict):
            gap_text  = g.get("gap", "")
            just_text = g.get("justification", "")
            lines.append(f"{i}. **{gap_text}**")
            if just_text:
                lines.append(f"   _{just_text}_")
        else:
            lines.append(f"{i}. {g}")
    return "\n".join(lines)


def _format_methodology(meth_data) -> str:
    meth_data = _unwrap(meth_data)
    if not meth_data:
        return ""
    if isinstance(meth_data, str):
        return _strip_repr(meth_data)

    inner = meth_data.get("methodology", meth_data) if isinstance(meth_data, dict) else meth_data
    inner = _unwrap(inner)

    if not isinstance(inner, dict):
        return _to_str(inner)

    parts = []

    if inner.get("research_approach"):
        parts.append(inner["research_approach"])

    if inner.get("justification"):
        parts.append(f"**Justification:** {inner['justification']}")

    ds = inner.get("data_sources")
    if ds and isinstance(ds, dict):
        parts.append("**Data Sources:**")
        for k, v in ds.items():
            label = k.replace("_", " ").title()
            if isinstance(v, list):
                parts.append(f"- *{label}:* " + "; ".join(str(i) for i in v))
            elif isinstance(v, str):
                parts.append(f"- *{label}:* {v}")

    at = inner.get("analysis_techniques")
    if at and isinstance(at, dict):
        parts.append("**Analysis Techniques:**")
        for k, v in at.items():
            label = k.replace("_", " ").title()
            if isinstance(v, list):
                parts.append(f"- *{label}:* " + "; ".join(str(i) for i in v))
            elif isinstance(v, str):
                parts.append(f"- *{label}:* {v}")

    lim = inner.get("limitations")
    if lim:
        if isinstance(lim, list):
            parts.append("**Limitations:** " + "; ".join(str(i) for i in lim))
        else:
            parts.append(f"**Limitations:** {lim}")

    return "\n\n".join(parts) if parts else _to_str(inner)


def _format_references(refs_data) -> str:
    refs_data = _unwrap(refs_data)
    if not refs_data:
        return "_No references generated._"

    # Handle the "references, [...]" string format from references_worker
    if isinstance(refs_data, str):
        s = refs_data.strip()
        # Strip "references, " prefix if present
        if s.startswith("references,"):
            s = s[len("references,"):].strip()
        # If it looks like a Python list string, parse it
        if s.startswith("[") and s.endswith("]"):
            try:
                import ast
                refs = ast.literal_eval(s)
                if isinstance(refs, list):
                    refs_data = refs
            except Exception:
                return s
        else:
            return s

    refs = refs_data.get("references", []) if isinstance(refs_data, dict) else refs_data
    if not refs:
        return "_No references generated._"

    clean = []
    for i, r in enumerate(refs, 1):
        r = _unwrap(r)
        if isinstance(r, tuple):
            text = ", ".join(str(x).strip() for x in r if x)
        else:
            text = str(r).strip()
        if text:
            clean.append(f"{i}. {text}")

    return "\n".join(clean) if clean else "_No references generated._"


def _format_discussion(disc_data) -> str:
    disc_data = _unwrap(disc_data)
    if not disc_data:
        return ""
    if isinstance(disc_data, str):
        return _strip_repr(disc_data)
    if not isinstance(disc_data, dict):
        return _to_str(disc_data)

    parts = []
    if disc_data.get("discussion"):
        parts.append(_strip_repr(_to_str(disc_data["discussion"])))
    if disc_data.get("limitations"):
        parts.append(f"**Limitations**\n\n{_to_str(disc_data['limitations'])}")
    if disc_data.get("future_work"):
        fw = disc_data["future_work"]
        if isinstance(fw, list):
            parts.append("**Future Work**\n\n" + "\n".join(f"- {item}" for item in fw))
        else:
            parts.append(f"**Future Work**\n\n{fw}")
    return "\n\n".join(parts)


def _format_conclusion(conc_data) -> str:
    conc_data = _unwrap(conc_data)
    if not conc_data:
        return ""
    if isinstance(conc_data, str):
        return _strip_repr(conc_data)
    if not isinstance(conc_data, dict):
        return _to_str(conc_data)

    parts = []
    if conc_data.get("conclusion"):
        parts.append(_strip_repr(_to_str(conc_data["conclusion"])))
    if conc_data.get("key_takeaways"):
        kt = conc_data["key_takeaways"]
        if isinstance(kt, list):
            parts.append("**Key Takeaways**\n\n" + "\n".join(f"- {item}" for item in kt))
        else:
            parts.append(f"**Key Takeaways**\n\n{kt}")
    return "\n\n".join(parts)


def _section_md(number: str, heading: str, content: str) -> str:
    if not content or not content.strip():
        return ""
    return f"\n---\n\n## {number}. {heading}\n\n{content.strip()}\n"


# ── Main node ─────────────────────────────────────────────────────────────────

def generate_output(state: dict) -> dict:
    log.info("=" * 60)
    log.info("📄  OUTPUT GENERATOR — Assembling final paper")
    log.info("=" * 60)

    topic = state.get("user_input", "Research Paper")
    style = state.get("citation_style", "APA")

    paper_title = _format_title(state.get("clarified_topic"), fallback=topic)

    sections = {
        "title":             paper_title,
        "introduction":      _to_str(state.get("introduction")),
        "background":        _to_str(state.get("background")),
        "literature_review": _to_str(state.get("literature_review")),
        "research_gaps":     _format_gaps(state.get("research_gaps")),
        "methodology":       _format_methodology(state.get("methodology")),
        "results":           _to_str(state.get("results")),
        "discussion":        _format_discussion(state.get("discussion")),
        "conclusion":        _format_conclusion(state.get("conclusion")),
        "references":        _format_references(state.get("references")),
    }

    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    md = (
        f"# {paper_title}\n\n"
        f"> **Citation Style:** {style} &nbsp;|&nbsp; "
        f"**Generated:** {ts}\n"
    )

    md += _section_md("1", "Introduction",     sections["introduction"])
    md += _section_md("2", "Background",        sections["background"])
    md += _section_md("3", "Literature Review", sections["literature_review"])
    md += _section_md("4", "Research Gaps",     sections["research_gaps"])
    md += _section_md("5", "Methodology",       sections["methodology"])
    md += _section_md("6", "Results",           sections["results"])
    md += _section_md("7", "Discussion",        sections["discussion"])
    md += _section_md("8", "Conclusion",        sections["conclusion"])
    md += _section_md("9", "References",        sections["references"])

    word_count = len(md.split())

    metadata = {
        "title":            paper_title,
        "user_input":       state.get("user_input", ""),
        "citation_style":   style,
        "word_count":       word_count,
        "sections_present": [k for k, v in sections.items() if v and v.strip()],
        "generated_at":     datetime.now().isoformat(),
        "total_steps":      state.get("total_steps", 0),
        "planner_calls":    state.get("planner_call_count", 0),
    }

    final_paper = {"markdown": md, "sections": sections, "metadata": metadata}

    log.success(f"Paper assembled: '{paper_title}'")
    log.success(f"  Word count     : {word_count:,}")
    log.success(f"  Sections ready : {', '.join(metadata['sections_present'])}")
    log.success(f"  Citation style : {style}")

    return {
        "final_paper":        final_paper,
        "termination_reason": "Completed successfully",
        "execution_history":  [{
            "node":       "output_generator",
            "action":     "paper_assembled",
            "word_count": word_count,
            "timestamp":  datetime.now().isoformat(),
        }],
    }