# output_generator/output_generator.py
"""
Output Generator node.

Runs after research_evaluation accepts the paper.
Assembles all worker outputs into a clean, structured final paper
stored in state["final_paper"] as:
  - "markdown"  → full paper as a single .md string  (saved to output/final_paper.md)
  - "sections"  → dict of section_name → plain text
  - "metadata"  → title, word_count, citation_style, generated_at, etc.
"""

import json
from datetime import datetime

from research_agent.utils.logger import log


# ── Converters ────────────────────────────────────────────────────────────────

def _to_str(value) -> str:
    """Convert any worker output type to a plain string."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):
        # Try common text-content keys first
        for key in ("introduction", "background", "literature_review",
                    "results_section", "discussion", "conclusion",
                    "clarified_topic", "formatted_citations"):
            if key in value:
                v = value[key]
                return (_to_str(v))
        # Fall back to pretty JSON
        return json.dumps(value, indent=2)
    if isinstance(value, list):
        return "\n".join(f"- {item}" for item in value)
    return str(value).strip()


def _format_gaps(gaps_data) -> str:
    if gaps_data is None:
        return ""
    if isinstance(gaps_data, str):
        return gaps_data
    gaps = gaps_data.get("research_gaps", []) if isinstance(gaps_data, dict) else gaps_data
    lines = []
    for i, g in enumerate(gaps, 1):
        if isinstance(g, dict):
            lines.append(f"{i}. **{g.get('gap', '')}**")
            if g.get("justification"):
                lines.append(f"   _{g['justification']}_")
        else:
            lines.append(f"{i}. {g}")
    return "\n".join(lines)


def _format_methodology(meth_data) -> str:
    if meth_data is None:
        return ""
    if isinstance(meth_data, str):
        return meth_data
    inner = meth_data.get("methodology") if isinstance(meth_data, dict) else meth_data
    if isinstance(inner, dict):
        lines = []
        for k, v in inner.items():
            label = k.replace("_", " ").title()
            if isinstance(v, list):
                lines.append(f"**{label}:**")
                lines.extend(f"- {item}" for item in v)
            else:
                lines.append(f"**{label}:** {v}")
        return "\n".join(lines)
    return _to_str(inner)


def _format_references(refs_data) -> str:
    if refs_data is None:
        return "_No references generated._"
    if isinstance(refs_data, str):
        return refs_data
    refs = refs_data.get("references", []) if isinstance(refs_data, dict) else refs_data
    if not refs:
        return "_No references generated._"
    # Coerce every item to str — tuples slip through from citation regex matches
    clean = []
    for r in refs:
        if isinstance(r, tuple):
            clean.append(", ".join(str(x).strip() for x in r if x))
        else:
            clean.append(str(r))
    return "\n".join(clean)


def _format_discussion(disc_data) -> str:
    if disc_data is None:
        return ""
    if isinstance(disc_data, str):
        return disc_data
    if isinstance(disc_data, dict):
        parts = []
        if disc_data.get("discussion"):
            parts.append(_to_str(disc_data["discussion"]))
        if disc_data.get("limitations"):
            parts.append(f"\n**Limitations**\n\n{_to_str(disc_data['limitations'])}")
        if disc_data.get("future_work"):
            fw = disc_data["future_work"]
            if isinstance(fw, list):
                parts.append("\n**Future Work**\n\n" + "\n".join(f"- {item}" for item in fw))
            else:
                parts.append(f"\n**Future Work**\n\n{fw}")
        return "\n\n".join(parts)
    return _to_str(disc_data)


def _format_conclusion(conc_data) -> str:
    if conc_data is None:
        return ""
    if isinstance(conc_data, str):
        return conc_data
    if isinstance(conc_data, dict):
        parts = []
        if conc_data.get("conclusion"):
            parts.append(_to_str(conc_data["conclusion"]))
        if conc_data.get("key_takeaways"):
            kt = conc_data["key_takeaways"]
            if isinstance(kt, list):
                parts.append("\n**Key Takeaways**\n\n" + "\n".join(f"- {item}" for item in kt))
        return "\n\n".join(parts)
    return _to_str(conc_data)


def _section_md(number: str, heading: str, content: str) -> str:
    """Return a formatted markdown section, or empty string if content is blank."""
    if not content or not content.strip():
        return ""
    return f"\n---\n\n## {number}. {heading}\n\n{content.strip()}\n"


# ── Main node ─────────────────────────────────────────────────────────────────

def generate_output(state: dict) -> dict:
    """
    Assemble all worker outputs into a complete, formatted research paper.
    Populates state['final_paper'] with 'markdown', 'sections', and 'metadata'.
    """
    log.info("=" * 60)
    log.info("📄  OUTPUT GENERATOR — Assembling final paper")
    log.info("=" * 60)

    topic = state.get("user_input", "Research Paper")
    style = state.get("citation_style", "APA")

    # ── Derive paper title ────────────────────────────────────────────────────
    ct = state.get("clarified_topic")
    if isinstance(ct, dict):
        paper_title = ct.get("clarified_topic", topic)
    elif ct:
        paper_title = str(ct)
    else:
        paper_title = topic

    # ── Extract each section ──────────────────────────────────────────────────
    sections = {
        "title":            paper_title,
        "introduction":     _to_str(state.get("introduction")),
        "background":       _to_str(state.get("background")),
        "literature_review":_to_str(state.get("literature_review")),
        "research_gaps":    _format_gaps(state.get("research_gaps")),
        "methodology":      _format_methodology(state.get("methodology")),
        "results":          _to_str(state.get("results")),
        "discussion":       _format_discussion(state.get("discussion")),
        "conclusion":       _format_conclusion(state.get("conclusion")),
        "references":       _format_references(state.get("references")),
    }

    # ── Build markdown ────────────────────────────────────────────────────────
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    md = (
        f"# {paper_title}\n\n"
        f"> **Citation Style:** {style} &nbsp;|&nbsp; "
        f"**Generated:** {ts}\n"
    )

    md += _section_md("1", "Introduction",          sections["introduction"])
    md += _section_md("2", "Background",             sections["background"])
    md += _section_md("3", "Literature Review",      sections["literature_review"])
    md += _section_md("4", "Research Gaps",          sections["research_gaps"])
    md += _section_md("5", "Methodology",            sections["methodology"])
    md += _section_md("6", "Results",                sections["results"])
    md += _section_md("7", "Discussion",             sections["discussion"])
    md += _section_md("8", "Conclusion",             sections["conclusion"])
    md += _section_md("9", "References",             sections["references"])

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

    final_paper = {
        "markdown": md,
        "sections": sections,
        "metadata": metadata,
    }

    log.success(f"Paper assembled: '{paper_title}'")
    log.success(f"  Word count     : {word_count:,}")
    log.success(f"  Sections ready : {', '.join(metadata['sections_present'])}")
    log.success(f"  Citation style : {style}")

    return {
        **state,
        "final_paper": final_paper,
        "execution_history": [{
            "node":       "output_generator",
            "action":     "paper_assembled",
            "word_count": word_count,
            "timestamp":  datetime.now().isoformat(),
        }],
        "termination_reason": "Completed successfully"
    }
