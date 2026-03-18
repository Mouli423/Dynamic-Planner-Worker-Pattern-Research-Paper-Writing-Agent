# ui.py
"""
Streamlit UI for the Research Paper Agent.
Run: streamlit run ui.py
"""

import queue
import sys
import threading
import time
from datetime import datetime

import streamlit as st

st.set_page_config(page_title="Research Paper Agent", layout="centered")
st.title("Research Paper Agent")

for key, default in [
    ("running", False),
    ("result",  None),
    ("thread",  None),
    ("msg_q",   None),
    ("worker",  "Starting..."),
]:
    if key not in st.session_state:
        st.session_state[key] = default

WORKER_LABELS = {
    "topic_clarifier":          "Clarifying topic",
    "outline_designer":         "Designing outline",
    "introduction_writer":      "Writing introduction",
    "background_writer":        "Writing background",
    "literature_review_writer": "Writing literature review",
    "research_gap_identifier":  "Identifying research gaps",
    "methodology_designer":     "Designing methodology",
    "results_writer":           "Writing results",
    "discussion_writer":        "Writing discussion",
    "conclusion_writer":        "Writing conclusion",
    "references_writer":        "Compiling references",
    "research_evaluation":      "Evaluating paper",
    "summarizer":               "Summarising section",
    "evaluator":                "Evaluating section",
    "output_generator":         "Assembling paper",
    "planner":                  "Planning next step",
}


class LogCapture:
    """Captures pipeline logs and pushes worker name updates to the queue."""
    def __init__(self, q):
        self.q = q

    def write(self, msg):
        if not msg.strip():
            return
        # Detect which worker just started from the log line
        for worker in WORKER_LABELS:
            if worker in msg and "Starting" in msg:
                self.q.put({"type": "worker", "name": worker})
                return

    def flush(self):
        pass


def run_pipeline_thread(topic, citation_style, msg_q):
    old_stdout = sys.stdout
    sys.stdout  = LogCapture(msg_q)
    try:
        from dotenv import load_dotenv
        load_dotenv()
        from main import run_pipeline

        final_state = run_pipeline(topic=topic, citation_style=citation_style)

        fp    = final_state.get("final_paper")
        er    = final_state.get("evaluation_result") or {}
        score = er.get("overall_score", 0)

        if fp:
            msg_q.put({
                "type":  "done",
                "md":    fp.get("markdown", ""),
                "words": fp.get("metadata", {}).get("word_count", 0),
                "score": score,
            })
        else:
            # Pipeline failed — assemble partial output from completed sections
            msg_q.put({
                "type":    "partial",
                "state":   final_state,
                "score":   score,
                "errors":  list(dict.fromkeys(final_state.get("errors", []))),
            })

    except Exception as exc:
        msg_q.put({"type": "error", "error": str(exc)})
    finally:
        sys.stdout = old_stdout


def extract_section_text(key: str, value) -> str:
    """Extract clean prose from any worker output structure."""
    if not value:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        # Try the exact section key first (most workers store text under their own key)
        if key in value and isinstance(value[key], str) and len(value[key]) > 30:
            return value[key]
        # Try all known prose fields
        for field in ("introduction", "background", "literature_review",
                      "discussion", "conclusion", "results_section", "results",
                      "methodology", "text", "content", "body", "summary"):
            if field in value and isinstance(value[field], str) and len(value[field]) > 30:
                return value[field]
        # Research gaps — list of dicts
        if key == "research_gaps":
            gaps = value.get("research_gaps", [])
            if isinstance(gaps, list) and gaps:
                lines = []
                for i, g in enumerate(gaps, 1):
                    if isinstance(g, dict):
                        lines.append(f"**{i}. {g.get('gap', '')}**\n\n{g.get('justification', '')}")
                    else:
                        lines.append(str(g))
                return "\n\n".join(lines)
        # Methodology — nested dict, extract research_approach
        if key == "methodology":
            m = value.get("methodology", value)
            if isinstance(m, dict):
                parts = []
                for f in ("research_approach", "justification"):
                    if f in m and isinstance(m[f], str):
                        parts.append(m[f])
                if parts:
                    return "\n\n".join(parts)
        # References — list of strings
        if key == "references":
            refs = value.get("references", [])
            if isinstance(refs, list) and refs:
                lines = []
                for r in refs:
                    if isinstance(r, tuple):
                        lines.append(", ".join(str(x).strip() for x in r if x))
                    else:
                        lines.append(str(r))
                return "\n\n".join(lines)
        # Last resort — join any long string values
        long_vals = [v for v in value.values() if isinstance(v, str) and len(v) > 30]
        if long_vals:
            return "\n\n".join(long_vals)
    if isinstance(value, list):
        return "\n\n".join(str(i) for i in value if i)
    return ""


def assemble_partial(state: dict) -> str:
    """Build a markdown string from whatever sections completed before failure."""
    SECTION_MAP = [
        ("introduction",      "Introduction"),
        ("background",        "Background"),
        ("literature_review", "Literature Review"),
        ("research_gaps",     "Research Gaps"),
        ("methodology",       "Methodology"),
        ("results",           "Results"),
        ("discussion",        "Discussion"),
        ("conclusion",        "Conclusion"),
        ("references",        "References"),
    ]

    parts = []
    found = 0
    for key, label in SECTION_MAP:
        text = extract_section_text(key, state.get(key))
        if text:
            parts.append(f"## {label}\n\n{text}")
            found += 1

    if not found:
        return "_No sections were completed before the pipeline stopped._"

    return "\n\n---\n\n".join(parts)


def drain():
    """Drain all pending messages from the queue into session state."""
    result = None
    while True:
        try:
            msg = st.session_state.msg_q.get_nowait()
        except Exception:
            break
        if msg["type"] == "worker":
            st.session_state.worker = WORKER_LABELS.get(msg["name"], msg["name"])
        elif msg["type"] in ("done", "partial", "error"):
            result = msg
            st.session_state.running = False
    return result


# ── UI ────────────────────────────────────────────────────────────────────────

if not st.session_state.running and st.session_state.result is None:

    topic = st.text_area(
        "Research topic", height=100,
        placeholder="e.g. Design a research paper on the future of the IT industry with AI",
        key="topic_input",
    )
    citation_style = st.selectbox("Citation style", ["APA", "IEEE", "MLA"],
                                  key="citation_input")

    if st.button("Generate Paper", disabled=not topic.strip(), key="run_btn"):
        q = queue.Queue()
        t = threading.Thread(
            target=run_pipeline_thread,
            args=(topic, citation_style, q),
            daemon=True,
        )
        t.start()
        st.session_state.update({
            "running": True,
            "result":  None,
            "msg_q":   q,
            "thread":  t,
            "worker":  "Starting...",
        })
        st.rerun()

elif st.session_state.running:

    result = drain()

    if result:
        st.session_state.result = result
        st.rerun()
    else:
        st.spinner(st.session_state.worker)
        st.write(f"⟳  {st.session_state.worker}")

        thread_done = (
            st.session_state.thread is not None
            and not st.session_state.thread.is_alive()
        )
        if thread_done:
            drain()
            if st.session_state.result is None:
                st.session_state.result = {
                    "type": "error", "error": "Thread ended with no result."
                }
            st.session_state.running = False
            st.rerun()
        else:
            time.sleep(0.5)
            st.rerun()

elif st.session_state.result is not None:

    r = st.session_state.result

    if r["type"] == "done":
        st.success(
            f"Done — {r.get('words', 0):,} words · "
            f"quality score {r.get('score', 0):.2f}"
        )
        st.download_button(
            "Download Paper",
            data=r.get("md", ""),
            file_name=f"paper_{datetime.now().strftime('%Y%m%d_%H%M')}.md",
            mime="text/markdown",
            key="download_btn",
        )

    elif r["type"] == "partial":
        st.warning("Pipeline did not complete — partial paper assembled from finished sections.")
        md = assemble_partial(r.get("state", {}))
        st.download_button(
            "Download Partial Paper",
            data=md,
            file_name=f"partial_paper_{datetime.now().strftime('%Y%m%d_%H%M')}.md",
            mime="text/markdown",
            key="download_partial_btn",
        )
        st.divider()
        # Render each completed section individually
        SECTION_MAP = [
            ("introduction",      "Introduction"),
            ("background",        "Background"),
            ("literature_review", "Literature Review"),
            ("research_gaps",     "Research Gaps"),
            ("methodology",       "Methodology"),
            ("results",           "Results"),
            ("discussion",        "Discussion"),
            ("conclusion",        "Conclusion"),
            ("references",        "References"),
        ]
        state = r.get("state", {})
        for key, label in SECTION_MAP:
            text = extract_section_text(key, state.get(key))
            if text:
                with st.expander(f"✅  {label}", expanded=True):
                    st.markdown(text)

    elif r["type"] == "error":
        st.error(r.get("error", "Unknown error"))

    if st.button("New Paper", key="new_btn"):
        for k, v in [("running", False), ("result", None),
                     ("thread", None), ("msg_q", None),
                     ("worker", "Starting...")]:
            st.session_state[k] = v
        st.rerun()