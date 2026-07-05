import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
from agent.core import run_pipeline
from agent.memory import SlidingWindowMemory
from agent.tools import is_safe_sql

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    layout="wide",
    page_title="BI Agent",
    page_icon="📊"
)

# ── Session state init ─────────────────────────────────────────────────────────
if "memory" not in st.session_state:
    st.session_state.memory = SlidingWindowMemory(max_turns=6)

if "messages" not in st.session_state:
    st.session_state.messages = []

if "turn_count" not in st.session_state:
    st.session_state.turn_count = 0

if "total_tokens" not in st.session_state:
    st.session_state.total_tokens = 0

if "last_chart" not in st.session_state:
    st.session_state.last_chart = None

if "last_table" not in st.session_state:
    st.session_state.last_table = None

if "last_insight" not in st.session_state:
    st.session_state.last_insight = None

if "last_sql" not in st.session_state:
    st.session_state.last_sql = None

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("Session Info")
    st.metric("Turns", st.session_state.turn_count)
    st.metric("Tokens used", st.session_state.total_tokens)
    st.metric("Memory (messages)", len(st.session_state.memory))

    if st.button("New Conversation", use_container_width=True):
        st.session_state.memory.clear()
        st.session_state.messages = []
        st.session_state.turn_count = 0
        st.session_state.last_chart = None
        st.session_state.last_table = None
        st.session_state.last_insight = None
        st.session_state.last_sql = None
        st.rerun()

# ── Sample questions (shown only when chat is empty) ───────────────────────────
SAMPLE_QUESTIONS = [
    "What is our revenue vs target by region?",
    "Who are the top 5 reps by closed deal value?",
    "Where are we over budget this quarter?",
    "Show the monthly revenue trend",
    "What is the win rate by sales team?",
    "Which product has the highest margin?",
]

if not st.session_state.messages:
    st.subheader("Try asking:")
    cols = st.columns(2)
    for i, q in enumerate(SAMPLE_QUESTIONS):
        if cols[i % 2].button(q, key=f"sample_{i}", use_container_width=True):
            st.session_state.prefill = q
            st.rerun()
else:
    if "prefill" in st.session_state:
        del st.session_state.prefill

# ── Split panel ────────────────────────────────────────────────────────────────
chat_col, viz_col = st.columns([1, 1.2])

# ── LEFT: Chat ─────────────────────────────────────────────────────────────────
with chat_col:
    st.header("Ask a Business Question")

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    user_input = st.chat_input("e.g. What is our revenue vs target by region?")
    if user_input is None and "prefill" in st.session_state:
        user_input = st.session_state.prefill
        del st.session_state.prefill

    if user_input:
        user_input = user_input.strip("`")
        st.session_state.messages.append({"role": "user", "content": user_input})

        with chat_col:
            with st.chat_message("user"):
                st.write(user_input)

        # ── Input-level safety check ───────────────────────────────────────────
        if not is_safe_sql(user_input):
            reply = "Destructive SQL commands are not permitted."
            st.session_state.messages.append({"role": "assistant", "content": reply})
            with chat_col:
                with st.chat_message("assistant"):
                    st.write(reply)
            # Clear viz state
            st.session_state.last_chart = None
            st.session_state.last_table = None
            st.session_state.last_insight = None
            st.session_state.last_sql = None
            st.session_state.total_tokens = 0
            st.rerun()

        else:
            # Run pipeline with spinner
            with st.spinner("Running..."):
                result = run_pipeline(user_input, memory=st.session_state.memory)

            error = result.get("error", False)
            sql = result.get("sql")
            data = result.get("data")
            chart = result.get("chart")
            insight = result.get("insight", "")

            reply = insight

            st.session_state.messages.append({"role": "assistant", "content": reply})
            with chat_col:
                with st.chat_message("assistant"):
                    st.write(reply)

            st.session_state.last_chart = chart if not error else None
            st.session_state.last_table = data if (data is not None and not data.empty) else None
            st.session_state.last_insight = insight if not error else None
            st.session_state.last_sql = sql if not error else None

            if not error:
                st.session_state.turn_count += 1
                st.session_state.total_tokens += result.get("tokens", 0)

            st.rerun()

# ── RIGHT: Viz ─────────────────────────────────────────────────────────────────
with viz_col:
    st.header("Results")

    if st.session_state.last_chart is not None:
        st.plotly_chart(st.session_state.last_chart, use_container_width=True)

    if st.session_state.last_table is not None:
        st.dataframe(st.session_state.last_table, use_container_width=True)

        csv = st.session_state.last_table.to_csv(index=False)
        st.download_button(
            label="Download as CSV",
            data=csv,
            file_name="results.csv",
            mime="text/csv"
        )

    if st.session_state.last_sql:
        with st.expander("Generated SQL", expanded=False):
            st.code(st.session_state.last_sql, language="sql")

    if st.session_state.last_insight:
        with st.expander("Business Insight", expanded=True):
            st.write(st.session_state.last_insight)

    if (st.session_state.last_chart is None and
            st.session_state.last_table is None and
            st.session_state.last_sql is None):
        st.info("Results will appear here after you ask a question.")