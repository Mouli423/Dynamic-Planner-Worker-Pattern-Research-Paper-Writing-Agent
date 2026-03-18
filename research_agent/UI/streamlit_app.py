# ui.py
"""
Streamlit UI for the Research Paper Agent.

Run:
    streamlit run ui.py
"""

import sys
import time
import threading
import queue
from pathlib import Path
from datetime import datetime

import streamlit as st

# ── Page config (must be first Streamlit call) ────────────────────────────────
st.set_page_config(
    page_title="Research Paper Agent",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=DM+Mono:wght@300;400;500&family=DM+Sans:wght@300;400;500;600&display=swap');

/* ── Base ── */
html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
    background-color: #0e0f13;
    color: #e8e6e0;
}

/* ── Hide Streamlit chrome ── */
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding: 2rem 3rem 4rem; max-width: 1200px; }

/* ── Header ── */
.agent-header {
    display: flex;
    align-items: baseline;
    gap: 1rem;
    border-bottom: 1px solid #2a2d35;
    padding-bottom: 1.5rem;
    margin-bottom: 2.5rem;
}
.agent-title {
    font-family: 'DM Serif Display', serif;
    font-size: 2.4rem;
    color: #f0ede6;
    letter-spacing: -0.02em;
    margin: 0;
}
.agent-subtitle {
    font-family: 'DM Mono', monospace;
    font-size: 0.75rem;
    color: #5a6070;
    letter-spacing: 0.08em;
    text-transform: uppercase;
}

/* ── Input card ── */
.input-card {
    background: #14161c;
    border: 1px solid #22252e;
    border-radius: 12px;
    padding: 2rem;
    margin-bottom: 1.5rem;
}

/* ── Streamlit widget overrides ── */
.stTextArea textarea {
    background: #0e0f13 !important;
    border: 1px solid #2a2d35 !important;
    border-radius: 8px !important;
    color: #e8e6e0 !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 1rem !important;
    padding: 1rem !important;
    resize: vertical !important;
}
.stTextArea textarea:focus {
    border-color: #c8a96e !important;
    box-shadow: 0 0 0 2px rgba(200, 169, 110, 0.15) !important;
}
.stSelectbox > div > div {
    background: #0e0f13 !important;
    border: 1px solid #2a2d35 !important;
    border-radius: 8px !important;
    color: #e8e6e0 !important;
}

/* ── Run button ── */
.stButton > button {
    background: #c8a96e !important;
    color: #0e0f13 !important;
    border: none !important;
    border-radius: 8px !important;
    font-family: 'DM Sans', sans-serif !important;
    font-weight: 600 !important;
    font-size: 0.95rem !important;
    padding: 0.75rem 2.5rem !important;
    letter-spacing: 0.02em !important;
    transition: all 0.2s !important;
    width: 100% !important;
}
.stButton > button:hover {
    background: #d4b97e !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 20px rgba(200, 169, 110, 0.3) !important;
}
.stButton > button:disabled {
    background: #2a2d35 !important;
    color: #5a6070 !important;
    transform: none !important;
    box-shadow: none !important;
}

/* ── Progress / status ── */
.status-bar {
    background: #14161c;
    border: 1px solid #22252e;
    border-radius: 10px;
    padding: 1.25rem 1.5rem;
    margin: 1rem 0;
    font-family: 'DM Mono', monospace;
    font-size: 0.82rem;
}
.status-line {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    color: #8892a4;
    margin: 0.25rem 0;
}
.status-line.active { color: #c8a96e; }
.status-line.done   { color: #6eb58a; }
.status-line.error  { color: #e07070; }

/* ── Worker badge ── */
.worker-badge {
    display: inline-block;
    background: #1e2029;
    border: 1px solid #2a2d35;
    border-radius: 6px;
    padding: 0.2rem 0.6rem;
    font-family: 'DM Mono', monospace;
    font-size: 0.72rem;
    color: #8892a4;
    margin: 0.15rem;
}
.worker-badge.done  { border-color: #3a5a45; color: #6eb58a; background: #141e19; }
.worker-badge.active { border-color: #6a5228; color: #c8a96e; background: #1c1710; }

/* ── Metric cards ── */
.metrics-row {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 1rem;
    margin: 1.5rem 0;
}
.metric-card {
    background: #14161c;
    border: 1px solid #22252e;
    border-radius: 10px;
    padding: 1.25rem;
    text-align: center;
}
.metric-value {
    font-family: 'DM Serif Display', serif;
    font-size: 2rem;
    color: #c8a96e;
    line-height: 1;
}
.metric-label {
    font-family: 'DM Mono', monospace;
    font-size: 0.68rem;
    color: #5a6070;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-top: 0.4rem;
}

/* ── Paper output ── */
.paper-container {
    background: #14161c;
    border: 1px solid #22252e;
    border-radius: 12px;
    padding: 2.5rem 3rem;
    margin-top: 1.5rem;
    line-height: 1.8;
}
.paper-container h1 {
    font-family: 'DM Serif Display', serif;
    font-size: 1.9rem;
    color: #f0ede6;
    border-bottom: 1px solid #2a2d35;
    padding-bottom: 1rem;
    margin-bottom: 1.5rem;
}
.paper-container h2 {
    font-family: 'DM Serif Display', serif;
    font-size: 1.35rem;
    color: #d4c9b4;
    margin-top: 2rem;
}
.paper-container p {
    color: #b8b4aa;
    font-size: 0.97rem;
}

/* ── Sidebar ── */
.sidebar-section {
    background: #14161c;
    border: 1px solid #22252e;
    border-radius: 10px;
    padding: 1rem 1.25rem;
    margin-bottom: 1rem;
}
.sidebar-label {
    font-family: 'DM Mono', monospace;
    font-size: 0.68rem;
    color: #5a6070;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-bottom: 0.6rem;
}
.history-item {
    padding: 0.5rem 0;
    border-bottom: 1px solid #1e2029;
    cursor: pointer;
    font-size: 0.85rem;
    color: #8892a4;
}
.history-item:last-child { border-bottom: none; }
.history-item:hover { color: #c8a96e; }

/* ── Score indicator ── */
.score-ring {
    width: 70px; height: 70px;
    border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-family: 'DM Serif Display', serif;
    font-size: 1.3rem;
    margin: 0 auto 0.4rem;
}
.score-high  { background: #141e19; border: 2px solid #6eb58a; color: #6eb58a; }
.score-mid   { background: #1c1710; border: 2px solid #c8a96e; color: #c8a96e; }
.score-low   { background: #1e1414; border: 2px solid #e07070; color: #e07070; }

/* ── Download button ── */
.stDownloadButton > button {
    background: transparent !important;
    border: 1px solid #c8a96e !important;
    color: #c8a96e !important;
    border-radius: 8px !important;
    font-family: 'DM Sans', sans-serif !important;
    font-weight: 500 !important;
    padding: 0.6rem 1.5rem !important;
    width: 100% !important;
    transition: all 0.2s !important;
}
.stDownloadButton > button:hover {
    background: rgba(200,169,110,0.1) !important;
}

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {
    gap: 0.5rem;
    background: transparent;
    border-bottom: 1px solid #22252e;
}
.stTabs [data-baseweb="tab"] {
    background: transparent !important;
    border: none !important;
    color: #5a6070 !important;
    font-family: 'DM Mono', monospace !important;
    font-size: 0.78rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.06em !important;
    padding: 0.5rem 1rem !important;
}
.stTabs [aria-selected="true"] {
    color: #c8a96e !important;
    border-bottom: 2px solid #c8a96e !important;
}

/* ── Log console ── */
.log-console {
    background: #0a0b0e;
    border: 1px solid #1e2029;
    border-radius: 8px;
    padding: 1rem 1.25rem;
    font-family: 'DM Mono', monospace;
    font-size: 0.75rem;
    max-height: 320px;
    overflow-y: auto;
    line-height: 1.7;
}
.log-line { margin: 0; }
.log-worker  { color: #6eb58a; }
.log-planner { color: #7aaed4; }
.log-eval    { color: #c8a96e; }
.log-error   { color: #e07070; }
.log-info    { color: #5a6070; }
.log-success { color: #9eb88a; }
</style>
""", unsafe_allow_html=True)

# ── Session state init ────────────────────────────────────────────────────────
if "result"       not in st.session_state: st.session_state.result       = None
if "running"      not in st.session_state: st.session_state.running      = False
if "log_lines"    not in st.session_state: st.session_state.log_lines    = []
if "history"      not in st.session_state: st.session_state.history      = []
if "workers_done" not in st.session_state: st.session_state.workers_done = []
if "current_worker" not in st.session_state: st.session_state.current_worker = None

WORKERS = [
    "topic_clarifier", "outline_designer", "introduction_writer",
    "background_writer", "literature_review_writer", "research_gap_identifier",
    "methodology_designer", "results_writer", "discussion_writer",
    "conclusion_writer", "references_writer", "research_evaluation",
]

WORKER_LABELS = {
    "topic_clarifier":          "Topic Clarifier",
    "outline_designer":         "Outline Designer",
    "introduction_writer":      "Introduction",
    "background_writer":        "Background",
    "literature_review_writer": "Literature Review",
    "research_gap_identifier":  "Research Gaps",
    "methodology_designer":     "Methodology",
    "results_writer":           "Results",
    "discussion_writer":        "Discussion",
    "conclusion_writer":        "Conclusion",
    "references_writer":        "References",
    "research_evaluation":      "Final Evaluation",
}

# ── Log interceptor ───────────────────────────────────────────────────────────

class UILogHandler:
    """Intercepts pipeline log lines and routes them to session state."""
    def __init__(self, log_queue):
        self.q = log_queue

    def write(self, msg):
        if msg.strip():
            self.q.put(msg.strip())

    def flush(self): pass


def classify_log(line: str) -> str:
    if "WORKER" in line and "✅" in line:  return "log-worker"
    if "WORKER" in line:                   return "log-worker"
    if "PLANNER" in line:                  return "log-planner"
    if "EVAL" in line:                     return "log-eval"
    if "ERROR" in line:                    return "log-error"
    if "SUCCESS" in line:                  return "log-success"
    return "log-info"


# ── Pipeline runner (thread) ──────────────────────────────────────────────────

def run_pipeline_thread(topic, citation_style, result_queue, log_queue):
    """Runs the pipeline in a background thread, streams logs to queue."""
    import io

    # Patch stdout to capture log output
    old_stdout = sys.stdout
    sys.stdout  = UILogHandler(log_queue)

    try:
        from dotenv import load_dotenv
        load_dotenv()

        from main import run_pipeline
        final_state = run_pipeline(topic=topic, citation_style=citation_style)
        result_queue.put({"ok": True, "state": final_state})
    except Exception as exc:
        result_queue.put({"ok": False, "error": str(exc)})
    finally:
        sys.stdout = old_stdout


# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="agent-header">
    <h1 class="agent-title">Research Paper Agent</h1>
    <span class="agent-subtitle">Powered by AWS Bedrock · LangGraph</span>
</div>
""", unsafe_allow_html=True)

# ── Layout: main col + sidebar ────────────────────────────────────────────────
sidebar = st.sidebar
main_col, right_col = st.columns([3, 1])

# ── Sidebar — history ─────────────────────────────────────────────────────────
with sidebar:
    st.markdown('<div class="sidebar-label">Run History</div>', unsafe_allow_html=True)
    if not st.session_state.history:
        st.markdown('<div style="color:#3a3f4a; font-size:0.82rem; padding: 0.5rem 0;">No runs yet</div>', unsafe_allow_html=True)
    else:
        for i, h in enumerate(reversed(st.session_state.history[-8:])):
            score_color = "#6eb58a" if h["score"] >= 0.8 else "#c8a96e" if h["score"] >= 0.65 else "#e07070"
            if st.button(
                f"{'✓' if h['score'] >= 0.65 else '!'} {h['topic'][:32]}...\n{h['words']:,}w · {h['time']}",
                key=f"hist_{i}",
                use_container_width=True
            ):
                st.session_state.result = h["result"]

    st.divider()
    st.markdown('<div class="sidebar-label">Settings</div>', unsafe_allow_html=True)
    recursion_limit = st.slider("Max steps", 80, 200, 150, 10)
    show_raw = st.toggle("Show raw markdown", value=False)


# ── Main column ───────────────────────────────────────────────────────────────
with main_col:

    # ── Input card ────────────────────────────────────────────────────────────
    with st.container():
        topic = st.text_area(
            "Research topic",
            placeholder="e.g. Design a research paper on the future of the IT industry with AI",
            height=100,
            label_visibility="collapsed",
        )

        c1, c2, c3 = st.columns([2, 2, 3])
        with c1:
            citation_style = st.selectbox(
                "Citation style",
                ["APA", "IEEE", "MLA"],
                label_visibility="collapsed",
            )
        with c2:
            st.markdown('<div style="padding-top:0.2rem"></div>', unsafe_allow_html=True)

        run_btn = st.button(
            "⟶  Generate Paper",
            disabled=st.session_state.running or not topic.strip(),
            use_container_width=True,
        )

    # ── Pipeline execution ────────────────────────────────────────────────────
    if run_btn and topic.strip() and not st.session_state.running:
        st.session_state.running       = True
        st.session_state.result        = None
        st.session_state.log_lines     = []
        st.session_state.workers_done  = []
        st.session_state.current_worker = None
        st.rerun()

    if st.session_state.running:
        result_queue = queue.Queue()
        log_queue    = queue.Queue()

        # Start pipeline thread
        t = threading.Thread(
            target=run_pipeline_thread,
            args=(topic, citation_style, result_queue, log_queue),
            daemon=True,
        )
        t.start()

        # ── Progress UI ───────────────────────────────────────────────────────
        st.markdown("### Running pipeline")

        # Worker progress badges
        badge_placeholder = st.empty()
        status_placeholder = st.empty()
        log_placeholder    = st.empty()

        workers_done   = []
        current_worker = None
        log_lines      = []

        while t.is_alive() or not result_queue.empty():
            # Drain log queue
            while not log_queue.empty():
                try:
                    line = log_queue.get_nowait()
                    log_lines.append(line)

                    # Detect worker progress from log lines
                    for w in WORKERS:
                        if w in line and "Starting" in line:
                            current_worker = w
                        if w in line and "Completed" in line and w not in workers_done:
                            workers_done.append(w)
                            current_worker = None
                except:
                    pass

            # Render badges
            badges_html = ""
            for w in WORKERS:
                if w in workers_done:
                    cls = "done"
                elif w == current_worker:
                    cls = "active"
                else:
                    cls = ""
                badges_html += f'<span class="worker-badge {cls}">{WORKER_LABELS[w]}</span>'
            badge_placeholder.markdown(
                f'<div style="margin: 1rem 0;">{badges_html}</div>',
                unsafe_allow_html=True
            )

            # Status line
            if current_worker:
                status_placeholder.markdown(
                    f'<div class="status-bar"><div class="status-line active">⟳ &nbsp;{WORKER_LABELS.get(current_worker, current_worker)}...</div></div>',
                    unsafe_allow_html=True
                )
            else:
                status_placeholder.markdown(
                    f'<div class="status-bar"><div class="status-line">◦ &nbsp;Processing — {len(workers_done)}/{len(WORKERS)} workers complete</div></div>',
                    unsafe_allow_html=True
                )

            # Log console (last 20 lines)
            recent = log_lines[-20:]
            log_html = "".join(
                f'<p class="log-line {classify_log(l)}">{l}</p>'
                for l in recent
            )
            log_placeholder.markdown(
                f'<div class="log-console">{log_html}</div>',
                unsafe_allow_html=True
            )

            time.sleep(0.4)

        # ── Collect result ────────────────────────────────────────────────────
        try:
            res = result_queue.get_nowait()
            if res["ok"]:
                final_state = res["state"]
                fp = final_state.get("final_paper")
                if fp:
                    result = {
                        "ok":            True,
                        "topic":         topic,
                        "paper":         fp,
                        "metadata":      fp.get("metadata", {}),
                        "score":         final_state.get("research_score", 0),
                        "total_steps":   final_state.get("total_steps", 0),
                        "planner_calls": final_state.get("planner_call_count", 0),
                        "worker_metrics": final_state.get("worker_metrics", {}),
                        "errors":        final_state.get("errors", []),
                    }
                    # Add to history
                    st.session_state.history.append({
                        "topic":  topic,
                        "score":  result["score"],
                        "words":  result["metadata"].get("word_count", 0),
                        "time":   datetime.now().strftime("%H:%M"),
                        "result": result,
                    })
                    st.session_state.result = result
                else:
                    st.session_state.result = {"ok": False, "error": "Pipeline completed but no paper was generated."}
            else:
                st.session_state.result = {"ok": False, "error": res.get("error", "Unknown error")}
        except queue.Empty:
            st.session_state.result = {"ok": False, "error": "Pipeline thread did not return a result."}

        st.session_state.running = False
        st.rerun()

    # ── Result display ────────────────────────────────────────────────────────
    if st.session_state.result and not st.session_state.running:
        r = st.session_state.result

        if not r.get("ok"):
            st.error(f"Pipeline error: {r.get('error')}")
        else:
            meta     = r["metadata"]
            paper    = r["paper"]
            score    = r.get("score", 0)
            sections = list(paper.get("sections", {}).keys())

            # ── Metrics row ───────────────────────────────────────────────────
            score_cls = "score-high" if score >= 0.8 else "score-mid" if score >= 0.65 else "score-low"
            m1, m2, m3, m4 = st.columns(4)
            with m1:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-value">{meta.get('word_count', 0):,}</div>
                    <div class="metric-label">Words</div>
                </div>""", unsafe_allow_html=True)
            with m2:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-value">{len(sections)}</div>
                    <div class="metric-label">Sections</div>
                </div>""", unsafe_allow_html=True)
            with m3:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-value">{r.get('total_steps', 0)}</div>
                    <div class="metric-label">Steps</div>
                </div>""", unsafe_allow_html=True)
            with m4:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="{score_cls} score-ring">{score:.2f}</div>
                    <div class="metric-label">Quality Score</div>
                </div>""", unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)

            # ── Tabs: Paper | Workers | Errors ────────────────────────────────
            tab_paper, tab_workers, tab_errors = st.tabs(["📄  Paper", "⚙  Workers", "⚠  Errors"])

            with tab_paper:
                paper_md = paper.get("markdown", "")
                if show_raw:
                    st.code(paper_md, language="markdown")
                else:
                    st.markdown(paper_md)

                st.download_button(
                    "↓  Download Markdown",
                    data=paper_md,
                    file_name=f"research_paper_{datetime.now().strftime('%Y%m%d_%H%M')}.md",
                    mime="text/markdown",
                    use_container_width=True,
                )

            with tab_workers:
                wm = r.get("worker_metrics", {})
                if wm:
                    for worker, metrics in wm.items():
                        if metrics.get("execution_count", 0) > 0:
                            ec = metrics["execution_count"]
                            sc = metrics["success_count"]
                            fc = metrics["failure_count"]
                            icon = "✅" if fc == 0 else "⚠️"
                            retries = ec - 1
                            retry_str = f" · {retries} retr{'y' if retries==1 else 'ies'}" if retries > 0 else ""
                            st.markdown(
                                f"`{icon}  {WORKER_LABELS.get(worker, worker)}`  "
                                f"— {sc} success / {fc} fail{retry_str}"
                            )
                else:
                    st.markdown("*No worker metrics available.*")

            with tab_errors:
                errors = r.get("errors", [])
                if errors:
                    for e in errors:
                        st.error(e)
                else:
                    st.success("No errors during this run.")


# ── Right column — quick reference ────────────────────────────────────────────
with right_col:
    st.markdown("""
    <div class="sidebar-section">
        <div class="sidebar-label">Pipeline</div>
        <div style="font-size:0.78rem; color:#5a6070; line-height:2;">
            ◦ Topic Clarifier<br>
            ◦ Outline Designer<br>
            ◦ Introduction<br>
            ◦ Background<br>
            ◦ Literature Review<br>
            ◦ Research Gaps<br>
            ◦ Methodology<br>
            ◦ Results<br>
            ◦ Discussion<br>
            ◦ Conclusion<br>
            ◦ References<br>
            ◦ Evaluation
        </div>
    </div>
    <div class="sidebar-section">
        <div class="sidebar-label">Tips</div>
        <div style="font-size:0.78rem; color:#5a6070; line-height:1.8;">
            Be specific in your topic.<br>
            Include domain, angle,<br>
            and time horizon for<br>
            best results.<br><br>
            Use the same session<br>
            to refine results.
        </div>
    </div>
    """, unsafe_allow_html=True)
