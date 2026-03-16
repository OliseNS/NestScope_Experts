"""
NestEval Dashboard — LLM Evaluation Results for NestChat.

WHAT THIS PAGE DOES:
  1. Lets you trigger a DeepEval evaluation run with a single button click
  2. Shows live progress while the run is happening
  3. Displays a "report card" of the results when done

WHAT IS DEEPEVAL? (Quick Primer)
  DeepEval is a framework that uses a "judge LLM" to score another LLM's answers.
  It answers questions like:
    - "Did NestChat actually answer what was asked?" (Answer Relevancy)
    - "Did NestChat make up data, or is it grounded in real query results?" (Faithfulness)

  Each metric scores from 0.0 (terrible) to 1.0 (perfect).
  We require >= 0.7 to pass.

HOW THE RUN WORKS:
  Browser clicks "Run" → POST /eval/run (starts background job)
  Page polls GET /eval/status every 3s → shows progress bar
  When complete → GET /eval/results → renders report card
"""

import streamlit as st
import time
import json
from datetime import datetime

from components import init_page, render_header, render_sidebar
from services.api_client import run_evaluation, get_eval_status, get_eval_results

# ── Page Setup ────────────────────────────────────────────────────────────────
init_page(page_title="NestEval - NestScope", page_icon="📊", layout="wide")
render_header(page_name="NestEval")

with st.sidebar:
    render_sidebar(active_page="nesteval")

# ── Session State ─────────────────────────────────────────────────────────────
# We use session_state to remember whether we triggered a run this session.
if "eval_triggered" not in st.session_state:
    st.session_state.eval_triggered = False

if "eval_results" not in st.session_state:
    st.session_state.eval_results = None


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def score_color(score: float | None, passed: bool) -> str:
    """Return a color hex string based on pass/fail status."""
    if score is None:
        return "#888888"  # Grey for unknown
    return "#4CAF50" if passed else "#FF6464"  # Green / Red


def render_metric_badge(metric_name: str, metric_data: dict):
    """Render a small metric score badge inline."""
    score = metric_data.get("score")
    passed = metric_data.get("passed", False)
    threshold = metric_data.get("threshold", 0.7)
    reason = metric_data.get("reason", "")
    error = metric_data.get("error")

    color = score_color(score, passed)
    icon = "✅" if passed else "❌"
    score_display = f"{score:.2f}" if score is not None else "N/A"

    # Render as a styled metric
    st.markdown(
        f"""
        <div style="
            border: 1px solid {color};
            border-radius: 8px;
            padding: 10px 14px;
            margin: 4px 0;
            background: rgba(255,255,255,0.03);
        ">
            <div style="font-size:0.8rem; color:#aaa; margin-bottom:4px;">
                {icon} <b>{metric_name}</b>
                &nbsp;·&nbsp;
                <span style="color:{color}; font-size:1.1rem; font-weight:bold;">{score_display}</span>
                &nbsp;/&nbsp;
                <span style="color:#888; font-size:0.8rem;">threshold {threshold}</span>
            </div>
            {'<div style="font-size:0.75rem; color:#bbb; font-style:italic;">' + reason + '</div>' if reason else ''}
            {'<div style="font-size:0.75rem; color:#FF6464;">Error: ' + error + '</div>' if error else ''}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_results(results: dict):
    """Render the full results report card."""
    total = results.get("total_tests", 0)
    passed = results.get("passed", 0)
    failed = results.get("failed", 0)
    pass_rate = results.get("pass_rate", 0)
    model = results.get("model", "unknown")
    duration = results.get("duration_seconds", 0)
    timestamp = results.get("timestamp", "")
    run_id = results.get("run_id", "")
    test_results = results.get("test_results", [])

    # ── Summary Header ────────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("📋 Evaluation Report")

    # Metadata line
    try:
        ts = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        ts_display = ts.strftime("%b %d, %Y at %H:%M UTC")
    except Exception:
        ts_display = timestamp

    st.caption(f"Run ID: `{run_id}` · Model: `{model}` · Completed: {ts_display} · Duration: {duration}s")

    # ── Big Metric Cards ──────────────────────────────────────────────────────
    # These are the "at-a-glance" numbers — the most important thing to see first.
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Tests", total)
    with col2:
        st.metric("✅ Passed", passed, delta=None)
    with col3:
        st.metric("❌ Failed", failed, delta=None)
    with col4:
        pct = f"{pass_rate * 100:.0f}%"
        # Pass rate delta shown as a color hint
        delta_color = "normal" if pass_rate >= 0.7 else "inverse"
        st.metric("Pass Rate", pct)

    # Visual pass rate bar
    bar_color = "#4CAF50" if pass_rate >= 0.8 else "#FFA500" if pass_rate >= 0.5 else "#FF6464"
    st.markdown(
        f"""
        <div style="background:#333; border-radius:8px; height:12px; margin:8px 0 20px 0;">
            <div style="background:{bar_color}; width:{pass_rate*100:.1f}%; height:100%; border-radius:8px;"></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Per-Test Results ──────────────────────────────────────────────────────
    st.subheader("🔍 Per-Test Results")
    st.caption("Click a test to expand its details, including the SQL query, answer, and metric scores.")

    for entry in test_results:
        overall_passed = entry.get("overall_passed", False)
        icon = "✅" if overall_passed else "❌"
        desc = entry.get("description", f"Test {entry.get('id')}")
        category = entry.get("category", "")
        question = entry.get("question", "")

        # Build a compact label showing pass/fail at a glance
        label = f"{icon} **{desc}** — *{category}*"

        with st.expander(label, expanded=False):
            # Question
            st.markdown(f"**Question:** {question}")

            # Success/Error status from NestChat
            if not entry.get("success"):
                err = entry.get("error", "Unknown error")
                st.error(f"NestChat failed: {err}")
                continue

            # SQL query
            sql = entry.get("sql_query", "")
            if sql:
                st.markdown("**Generated SQL:**")
                st.code(sql, language="sql")

            # NestChat's answer
            answer = entry.get("answer", "")
            if answer:
                st.markdown("**NestChat's Answer:**")
                st.info(answer)

            # Metric scores
            metrics = entry.get("metrics", {})
            if metrics:
                st.markdown("**Metric Scores:**")
                cols = st.columns(len(metrics))
                for col, (metric_name, metric_data) in zip(cols, metrics.items()):
                    with col:
                        render_metric_badge(
                            metric_name.replace("_", " ").title(),
                            metric_data
                        )
            else:
                st.warning("No metrics scored (NestChat query may have failed).")

    # ── Download JSON ─────────────────────────────────────────────────────────
    st.markdown("---")
    st.download_button(
        label="⬇️ Download full results JSON",
        data=json.dumps(results, indent=2, default=str),
        file_name=f"nesteval_{run_id}.json",
        mime="application/json",
        help="Save the full results for offline analysis or sharing",
    )


# ============================================================================
# MAIN PAGE LAYOUT
# ============================================================================

st.markdown("""
## 📊 NestEval — LLM Quality Dashboard

NestEval runs automated evaluations of **NestChat** using [DeepEval](https://docs.confident-ai.com/),
an open-source LLM evaluation framework.

### What gets tested?
We run **18 bird colony questions** across different complexity levels and score each answer on:

| Metric | What it measures | Pass threshold |
|--------|-----------------|----------------|
| **Answer Relevancy** | Did the answer actually address the question? | ≥ 0.5 |
| **Faithfulness** | Is the answer grounded in retrieved data (no hallucinations)? | ≥ 0.7 |
| **Contextual Relevancy** | Was the data retrieved by the SQL query relevant to the question? | ≥ 0.7 |
| **Conciseness** | Did the answer stay focused without excessive elaboration? | ≥ 0.3 |

> **Note:** Running evaluations uses API credits (each run makes ~90-100 LLM calls for scoring).
> A typical run takes 5-10 minutes.
""")

st.divider()

# ── Check if currently running (from a previous session trigger) ──────────────
status = get_eval_status()
is_running = status.get("running", False)

# ── Run Button ────────────────────────────────────────────────────────────────
col_btn, col_info = st.columns([1, 3])

with col_btn:
    run_disabled = is_running
    if st.button(
        "▶ Run Evaluation" if not is_running else "⏳ Running...",
        use_container_width=True,
        type="primary",
        disabled=run_disabled,
        help="Runs all 18 test cases and scores them with DeepEval"
    ):
        result = run_evaluation()
        if result.get("error") == "already_running":
            st.warning("An evaluation is already running. Please wait.")
        elif result.get("error"):
            st.error(f"Failed to start: {result['error']}")
        else:
            st.session_state.eval_triggered = True
            st.rerun()

with col_info:
    if is_running:
        progress = status.get("progress", 0)
        total = status.get("total", 8)
        current_test = status.get("current_test", "")
        pct = progress / total if total > 0 else 0

        st.progress(pct, text=f"Running test {progress}/{total}: *{current_test}*")

        # Auto-refresh: wait 3 seconds and rerun to check status again.
        # This creates a "polling" loop — the page refreshes until the run completes.
        # WHY 3 SECONDS? Each test takes ~10-20s, so 3s gives good granularity
        # without hammering the server.
        time.sleep(3)
        st.rerun()
    elif st.session_state.eval_triggered:
        # Transitioning from "triggered" to "done" state — fetch results
        results = get_eval_results()
        if results.get("error") == "no_results":
            st.info("Evaluation complete. Results loading...")
            time.sleep(2)
            st.rerun()
        elif results.get("error"):
            st.error(f"Could not load results: {results['error']}")
        else:
            st.session_state.eval_results = results
            st.session_state.eval_triggered = False

# ── Show Results ──────────────────────────────────────────────────────────────
# Try to load results if we have them in session, otherwise fetch from backend
if st.session_state.eval_results:
    render_results(st.session_state.eval_results)
elif not is_running:
    # Try fetching previous results (from a past run)
    results = get_eval_results()
    if results and not results.get("error"):
        st.session_state.eval_results = results
        render_results(results)
    else:
        st.markdown("""
        ---
        ### No results yet

        Click **Run Evaluation** above to run your first evaluation.

        The dashboard will show results here once the run is complete.
        """)
