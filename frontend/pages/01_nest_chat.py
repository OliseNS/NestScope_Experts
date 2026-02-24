"""
NestChat Page - Natural Language Interface for Bird Survey Data
"""

import streamlit as st
import pandas as pd
import random

# Import from modular structure
from services import (
    ask_question_streaming,
    ask_question_to_backend,
    get_backend_config
)
from components import render_chart, render_map, render_sidebar_section, render_service_status_link
from styles import get_custom_css

# ============================================================================
# PAGE CONFIGURATION
# ============================================================================

st.set_page_config(
    page_title="NestChat - NestScope",
    page_icon="💬",
    layout="wide"
)

# Apply custom CSS
st.markdown(get_custom_css(), unsafe_allow_html=True)

# Hide Streamlit's default page navigation and add fixed header
st.markdown("""
<style>
    [data-testid="stSidebarNav"] {
        display: none;
    }
    .fixed-header {
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        background: #1E1E1E;
        border-bottom: 1px solid #333;
        padding: 0.75rem 1.5rem;
        display: flex;
        align-items: center;
        gap: 0.75rem;
        z-index: 999999;
    }
    .main-content {
        margin-top: 4rem;
    }
</style>
""", unsafe_allow_html=True)

# Fixed header
st.markdown("""
    <div class="fixed-header">
        <span style="font-size: 1.5rem;">🦅</span>
        <span style="font-size: 1rem; font-weight: 600; color: #E5E5E5;">NestScope</span>
        <span style="color: #666; font-size: 0.875rem;">Avian Monitoring Suite</span>
    </div>
""", unsafe_allow_html=True)

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def build_conversation_history():
    """
    Build conversation history from session messages for API context.
    Converts messages to the format expected by the backend LLM.

    Returns:
        List of message dicts with 'role' and 'content' keys
    """
    history = []
    for msg in st.session_state.messages:
        # Only include user and assistant messages, not data
        if msg["role"] in ["user", "assistant"]:
            history.append({
                "role": msg["role"],
                "content": msg["content"]
            })
    return history

# ============================================================================
# SESSION STATE INITIALIZATION
# ============================================================================

if "messages" not in st.session_state:
    st.session_state.messages = []

if "query_history" not in st.session_state:
    st.session_state.query_history = []

if "chat_placeholder" not in st.session_state:
    placeholder_examples = [
        "Show brown pelican trends from 2015 to 2021",
        "What were the top 5 species in 2020?",
        "List all bird colonies in Louisiana",
        "How many observations were recorded per year?",
        "Compare species diversity across different colonies",
        "Which habitat had the most bird sightings?",
        "Analyze the population growth of Seagulls",
        "Identify colonies with declining populations"
    ]
    st.session_state.chat_placeholder = f'Try "{random.choice(placeholder_examples)}"'


# ============================================================================
# SIDEBAR
# ============================================================================

with st.sidebar:
    # Navigation Section
    render_sidebar_section("Navigation")

    if st.button("🏠 Home", use_container_width=True, help="Return to home page"):
        st.switch_page("app.py")

    if st.button("💬 NestChat", use_container_width=True, help="Natural language data queries", type="primary"):
        st.rerun()

    if st.button("🦅 NestVision", use_container_width=True, help="AI bird detection & counting"):
        st.switch_page("pages/02_nest_vision.py")

    if st.button("🗄️ NestDB", use_container_width=True, help="Database management interface"):
        st.switch_page("pages/04_db_editor.py")

    # Tools section
    render_sidebar_section("Tools")

    st.link_button("🧑‍🔬 Nestperts", "http://localhost:5000", use_container_width=True, help="Expert species training platform")

    # Quick Prompts Section
    render_sidebar_section("Quick Examples")

    examples = [
        ("📈 Trends", "Show brown pelican trends from 2015 to 2021"),
        ("🏆 Top Species", "What were the top 5 species in 2021?"),
        ("📍 Locations", "Show all bird colonies in Louisiana with their locations"),
        ("📊 Annual Counts", "How many observations were recorded per year?"),
        ("🎯 Diversity", "Compare species diversity across different colonies")
    ]

    for label, full_prompt in examples:
        if st.button(label, key=f"quick_prompt_{label}", use_container_width=True):
            st.session_state.current_question = full_prompt
            st.rerun()

    # Session History Section
    if st.session_state.query_history:
        render_sidebar_section("Recent Queries")

        for i, (q_label, q_prompt) in enumerate(reversed(st.session_state.query_history[-5:])):
            display_label = (q_label[:35] + '...') if len(q_label) > 37 else q_label
            if st.button(f"💬 {display_label}", key=f"hist_{i}", use_container_width=True, help=q_prompt):
                st.session_state.current_question = q_prompt
                st.rerun()

        st.markdown("")  # Small spacing
        if st.button("🗑️ Clear History", key="clear_hist", use_container_width=True):
            st.session_state.query_history = []
            st.rerun()

    # System Status section
    render_sidebar_section("System Status")
    render_service_status_link()

# ============================================================================
# MAIN INTERFACE
# ============================================================================

st.title("NestChat")
st.caption("Natural language interface for Gulf Coast avian monitoring data")

# Display current model being used
try:
    backend_config = get_backend_config()
    model_name = backend_config.get("model", {}).get("name", "Unknown")
    st.markdown(
        f'<p style="font-size: 0.8rem; color: #888; margin-top: -0.5rem; margin-bottom: 1rem;">⚡ Powered by <code style="background: #2d2d2d; padding: 2px 6px; border-radius: 3px; color: #D97757;">{model_name}</code></p>',
        unsafe_allow_html=True
    )
except Exception:
    # Silently fail if backend is unreachable
    pass

# ============================================================================
# CHAT INTERFACE
# ============================================================================
# Welcome Card
if not st.session_state.messages:
    st.markdown("""
        <div class="title-card">
            <h3 style="margin-top: 0;">🚀 Your AI-Powered Research & Decision Support Tool</h3>
            <p style="font-size: 1.05rem; margin-bottom: 1.5rem; color: #E5E5E5;">
                Transform <strong>days of data analysis into minutes of insights</strong>. Ask questions in plain English—no SQL expertise required.
            </p>
        </div>
    """, unsafe_allow_html=True)

    # Use native Streamlit columns with gap for feature cards
    col1, col2 = st.columns(2, gap="medium")

    with col1:
        st.markdown("""
            <div style="background: rgba(217, 119, 87, 0.08); padding: 1rem; border-radius: 10px; border-left: 3px solid #D97757; margin-bottom: 0.75rem; height: 100%;">
                <div style="color: #E5E5E5; font-weight: 600; margin-bottom: 0.5rem;">📊 For Researchers</div>
                <div style="font-size: 0.875rem; color: #B0B0B0; line-height: 1.5;">Instant trend analysis, baseline comparisons, grant proposal data</div>
            </div>
        """, unsafe_allow_html=True)

        st.markdown("""
            <div style="background: rgba(217, 119, 87, 0.08); padding: 1rem; border-radius: 10px; border-left: 3px solid #D97757; height: 100%;">
                <div style="color: #E5E5E5; font-weight: 600; margin-bottom: 0.5rem;">📈 For Presentations</div>
                <div style="font-size: 0.875rem; color: #B0B0B0; line-height: 1.5;">Auto-generated charts, maps, and publication-ready visualizations</div>
            </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("""
            <div style="background: rgba(217, 119, 87, 0.08); padding: 1rem; border-radius: 10px; border-left: 3px solid #D97757; margin-bottom: 0.75rem; height: 100%;">
                <div style="color: #E5E5E5; font-weight: 600; margin-bottom: 0.5rem;">🎯 For Managers</div>
                <div style="font-size: 0.875rem; color: #B0B0B0; line-height: 1.5;">Restoration site prioritization, resource allocation insights</div>
            </div>
        """, unsafe_allow_html=True)

        st.markdown("""
            <div style="background: rgba(217, 119, 87, 0.08); padding: 1rem; border-radius: 10px; border-left: 3px solid #D97757; height: 100%;">
                <div style="color: #E5E5E5; font-weight: 600; margin-bottom: 0.5rem;">👥 For Stakeholders</div>
                <div style="font-size: 0.875rem; color: #B0B0B0; line-height: 1.5;">Real-time answers during meetings, community engagement</div>
            </div>
        """, unsafe_allow_html=True)

    # Dataset stats and examples
    st.markdown("""
        <div style="margin-top: 1.5rem; padding: 1rem 1.25rem; background: rgba(255, 255, 255, 0.03); border-radius: 10px; border: 1px solid rgba(255, 255, 255, 0.08);">
            <div style="font-size: 0.95rem; color: #B0B0B0; margin-bottom: 1rem;">
                <strong style="color: #E5E5E5;">11 years</strong> of Gulf Coast colonial waterbird data (2010-2021) •
                <strong style="color: #E5E5E5;">5 states</strong> (TX, LA, MS, AL, FL) •
                <strong style="color: #E5E5E5;">592 colonies</strong> •
                <strong style="color: #E5E5E5;">73 species</strong>
            </div>
            <div style="font-size: 0.875rem; color: #888; border-top: 1px solid rgba(255, 255, 255, 0.08); padding-top: 1rem;">
                💡 <em>Try asking:</em> "Show me post-Deepwater Horizon recovery trends" • "Which colonies need monitoring?" • "Compare species diversity across restoration sites"
            </div>
        </div>
    """, unsafe_allow_html=True)

# ============================================================================
# CHAT HISTORY DISPLAY
# ============================================================================

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

        if "dataframe" in message and message["dataframe"] is not None:
            df = message["dataframe"]
            show_chart = message.get("show_chart", False)
            chart_type = message.get("chart_type")
            show_map = message.get("show_map", False)
            is_single_location = message.get("is_single_location", False)

            # Render single-location map (always show for single location with coords)
            if is_single_location:
                st.markdown("---")
                st.markdown("### 📍 Location Map")
                render_map(df)
                st.markdown("---")

            # Render tabs for multi-result visualizations (respect backend directives)
            if show_chart or (show_map and len(df) > 1):
                tab_labels = []

                if show_chart:
                    tab_labels.append("📊 Data & Charts")
                else:
                    tab_labels.append("📋 Data Table")

                if show_map and len(df) > 1:
                    tab_labels.append("🗺️ Map View")

                tabs = st.tabs(tab_labels)

                # Data/Chart Tab
                with tabs[0]:
                    st.dataframe(df, use_container_width=True)

                    csv = df.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="📥 Download CSV",
                        data=csv,
                        file_name="bird_data_export.csv",
                        mime="text/csv",
                        key=f"download_{message.get('content', '')[:20]}_{id(message)}"
                    )

                    if show_chart and chart_type:
                        render_chart(df, chart_type, key_suffix=f"history_{id(message)}")

                # Map Tab
                if show_map and len(tabs) > 1 and len(df) > 1:
                    with tabs[1]:
                        render_map(df)

            else:
                # Simple data table in expander (no visualization directive from backend)
                with st.expander("View Source Data"):
                    st.dataframe(df, use_container_width=True)

                    csv = df.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="📥 Download CSV",
                        data=csv,
                        file_name="bird_data_export.csv",
                        mime="text/csv",
                        key=f"download_simple_{message.get('content', '')[:20]}_{id(message)}"
                    )

# ============================================================================
# USER INPUT HANDLING
# ============================================================================

# Always render the chat input at the bottom
user_input = st.chat_input(st.session_state.chat_placeholder)

# Determine which prompt to process
prompt = None
if "current_question" in st.session_state:
    # Use the quick prompt or history item from sidebar
    prompt = st.session_state.current_question
    del st.session_state.current_question
elif user_input:
    # Use the user's typed input
    prompt = user_input

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        try:
            # Placeholders for streaming content
            status_placeholder = st.empty()
            sql_expander_placeholder = st.empty()
            answer_placeholder = st.empty()

            # Variables to store response data
            sql_query = ""
            results = None
            results_count = 0
            answer = ""
            error = None
            query_error = None
            use_streaming = True

            # Visualization directives from backend
            show_chart = False
            chart_type = None
            show_map = False

            status_placeholder.markdown("🔄 **Processing your question...**")

            # Build conversation history for context
            conversation_history = build_conversation_history()

            # Try streaming first, fallback to regular API if it fails
            try:
                for event in ask_question_streaming(prompt, conversation_history=conversation_history):
                    event_type = event.get('type')

                    if event_type == 'error':
                        error_content = event.get('content', '')
                        # Check if it's a 404 error (streaming not available)
                        if '404' in str(error_content):
                            use_streaming = False
                            break
                        else:
                            error = error_content
                            status_placeholder.empty()
                            st.error(error)
                            st.session_state.messages.append({"role": "assistant", "content": error})
                            st.stop()

                    elif event_type == 'sql_query':
                        sql_query = event.get('content')
                        status_placeholder.markdown("🔄 **Executing query...**")

                    elif event_type == 'results':
                        results = event.get('content')
                        results_count = event.get('count', 0)
                        status_placeholder.markdown("🔄 **Analyzing results...**")

                        # Display SQL query in expander
                        with sql_expander_placeholder.expander("🔍 View Generated SQL Query"):
                            st.code(sql_query, language="sql")

                    elif event_type == 'query_error':
                        query_error = event.get('content')

                    elif event_type == 'answer_start':
                        status_placeholder.empty()

                    elif event_type == 'answer_chunk':
                        chunk = event.get('content', '')
                        answer += chunk
                        # Update the answer display with streaming text
                        answer_placeholder.markdown(answer + "▌")

                    elif event_type == 'answer_end':
                        # Remove cursor and show final answer
                        answer_placeholder.markdown(answer)

                    elif event_type == 'visualization':
                        # Backend tells us what to visualize
                        show_chart = event.get('show_chart', False)
                        chart_type = event.get('chart_type')
                        show_map = event.get('show_map', False)

                    elif event_type == 'done':
                        break
            except Exception as e:
                # If streaming fails, fall back to regular API
                if '404' in str(e):
                    use_streaming = False
                else:
                    raise

            # Fallback to non-streaming API if streaming is not available
            if not use_streaming:
                status_placeholder.markdown("🔄 **Processing your question...**")
                response = ask_question_to_backend(prompt, conversation_history=conversation_history)

                if response.get('error'):
                    error_msg = response['error']
                    status_placeholder.empty()
                    st.error(error_msg)
                    st.session_state.messages.append({"role": "assistant", "content": error_msg})
                    st.stop()

                # Extract response components
                sql_query = response['sql_query']
                answer = response['answer']
                results = response['results']

                # Get visualization directives from backend
                show_chart = response.get('show_chart', False)
                chart_type = response.get('chart_type')
                show_map = response.get('show_map', False)

                status_placeholder.empty()

                # Display SQL query in expander
                with sql_expander_placeholder.expander("🔍 View Generated SQL Query"):
                    st.code(sql_query, language="sql")

                # Display the answer
                answer_placeholder.markdown(answer)

            # Save to history (on success only)
            if prompt and prompt not in [h[1] for h in st.session_state.query_history]:
                st.session_state.query_history.append((prompt, prompt))

            # Convert results to DataFrame for visualization
            df = pd.DataFrame(results) if results else pd.DataFrame()

            # Stop if no results are found or there was a query error
            if df.empty:
                if query_error:
                    # Query error - Claude's answer will explain the issue
                    pass  # Just display the answer, no additional message needed
                else:
                    # Query succeeded but returned no results
                    st.info("This query returned no matching records.")
                st.session_state.messages.append({"role": "assistant", "content": answer})
                st.stop()

            response_data = {
                "role": "assistant",
                "content": answer,
                "dataframe": df,
                "show_chart": show_chart,
                "chart_type": chart_type,
                "show_map": show_map
            }

            # Detect if this is a single-location query (always show map for single location)
            cols_lower = [str(col).lower() for col in df.columns]
            has_lat = any('latit' in col for col in cols_lower)
            has_lon = any('longi' in col or 'lng' in col for col in cols_lower)
            is_single_location = not df.empty and len(df) == 1 and has_lat and has_lon

            response_data["is_single_location"] = is_single_location

            # Render map for single-location queries (regardless of backend directive)
            if is_single_location:
                st.markdown("---")
                st.markdown("### 📍 Location Map")
                render_map(df)
                st.markdown("---")

            # Render visualizations based on BACKEND directives
            if show_chart or show_map:
                # Tabs for data, charts, and maps
                tab_labels = []

                if show_chart:
                    tab_labels.append("📊 Data & Charts")
                else:
                    tab_labels.append("📋 Data Table")

                if show_map and len(df) > 1:
                    tab_labels.append("🗺️ Map View")

                tabs = st.tabs(tab_labels)

                # Data/Chart Tab
                with tabs[0]:
                    st.dataframe(df, use_container_width=True)

                    csv = df.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="📥 Download CSV",
                        data=csv,
                        file_name="bird_data_export.csv",
                        mime="text/csv",
                    )

                    if show_chart and chart_type:
                        render_chart(df, chart_type, key_suffix=f"current_{id(response_data)}")

                # Map Tab
                if show_map and len(tabs) > 1 and len(df) > 1:
                    with tabs[1]:
                        render_map(df)

            else:
                # Simple data table (no visualization directive from backend)
                with st.expander("View Source Data"):
                    st.dataframe(df, use_container_width=True)

                    csv = df.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="📥 Download CSV",
                        data=csv,
                        file_name="bird_data_export.csv",
                        mime="text/csv",
                    )

            st.session_state.messages.append(response_data)

        except Exception as e:
            st.error(str(e))
            st.error(f"An unexpected error occurred: {str(e)}")
            st.info("Try rephrasing your question or contact support if the issue persists.")
