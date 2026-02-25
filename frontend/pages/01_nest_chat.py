"""
NestChat Page - Natural Language Interface for Bird Survey Data
"""

import streamlit as st
import pandas as pd
import random
import requests

# Import from modular structure
from services import (
    ask_question_streaming,
    ask_question_agentic_streaming,
    ask_question_to_backend,
    get_backend_config
)
from components import render_chart, render_map, init_page, render_header, render_sidebar

# API configuration
API_BASE_URL = "http://localhost:8000"

# ============================================================================
# PAGE CONFIGURATION
# ============================================================================

# Initialize page with shared layout
init_page(page_title="NestChat - NestScope", page_icon="💬", layout="wide")

# Render shared header
render_header(page_name="NestChat")

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
        "Show the total bird count for Brown Pelican from 2015 to 2021",
        "What were the top 5 species by bird count in 2021?",
        "List all bird colonies in Louisiana with their coordinates",
        "What is the total bird count for each year?",
        "Show the number of different species at each colony",
        "Which colony location had the highest total bird count?",
        "Show the total bird count for Laughing Gull by year",
        "Which colonies had decreasing bird counts over time?"
    ]
    st.session_state.chat_placeholder = f'Try "{random.choice(placeholder_examples)}"'

# ============================================================================
# SIDEBAR
# ============================================================================

with st.sidebar:
    # Render shared navigation and tools
    render_sidebar(active_page="nestchat")

    # Quick Prompts Section (NestChat-specific)
    from components import render_sidebar_section
    render_sidebar_section("Quick Examples")

    examples = [
        ("📈 Trends", "Show the total bird count for Brown Pelican from 2015 to 2021"),
        ("🏆 Top Species", "What were the top 5 species by bird count in 2021?"),
        ("📍 Locations", "Show all bird colonies in Louisiana with their coordinates"),
        ("📊 Annual Counts", "What is the total bird count for each year?"),
        ("🎯 Diversity", "Show the number of different species observed at each colony")
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
# Welcome Card - Clean and concise
if not st.session_state.messages:
    st.markdown("""
        <div style="background: linear-gradient(135deg, rgba(217, 119, 87, 0.1) 0%, rgba(217, 119, 87, 0.05) 100%);
                    padding: 2rem; border-radius: 12px; border: 1px solid rgba(217, 119, 87, 0.2); margin-bottom: 1.5rem;">
            <h3 style="margin: 0 0 0.5rem 0; color: #E5E5E5;">Ask questions in plain English, get instant insights</h3>
            <p style="font-size: 0.95rem; margin: 0; color: #B0B0B0;">
                11 years of Gulf Coast data • 592 colonies • 73 species • Auto-generated charts & maps
            </p>
        </div>
    """, unsafe_allow_html=True)

    # Example questions card
    st.markdown("""
        <div style="background: rgba(255, 255, 255, 0.02); padding: 1.25rem; border-radius: 10px; border: 1px solid rgba(255, 255, 255, 0.08);">
            <div style="font-size: 0.875rem; color: #888; margin-bottom: 0.75rem;">💡 Example questions:</div>
            <div style="font-size: 0.9rem; color: #B0B0B0; line-height: 1.8;">
                • "Show me post-Deepwater Horizon recovery trends"<br>
                • "Which colonies need monitoring?"<br>
                • "Compare Brown Pelican populations 2010 vs 2021"<br>
                • "Map all Louisiana colonies with their locations"
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
            thinking_status_placeholder = st.empty()  # Live status (will be replaced)
            thought_process_placeholder = st.empty()  # Final thought process (persistent)
            answer_placeholder = st.empty()

            # Variables to store response data
            sql_query = ""
            results = None
            results_count = 0
            answer = ""
            error = None
            query_error = None

            # Visualization directives from backend
            show_chart = False
            chart_type = None
            show_map = False

            # Agentic mode tracking
            thinking_steps = []
            current_attempt = 1

            # Build conversation history for context
            conversation_history = build_conversation_history()

            # Use agentic streaming for better accuracy
            for event in ask_question_agentic_streaming(prompt, conversation_history=conversation_history):
                event_type = event.get('type')

                if event_type == 'error':
                    error_content = event.get('content', '')
                    thinking_status_placeholder.empty()
                    st.error(f"❌ Error: {error_content}")
                    st.session_state.messages.append({"role": "assistant", "content": f"Error: {error_content}"})
                    st.stop()

                elif event_type == 'thinking_step':
                    # Add or update thinking step
                    step_info = {
                        'step': event.get('step'),
                        'content': event.get('content'),
                        'icon': event.get('icon', '⚙️'),
                        'attempt': event.get('attempt', 1),
                        'status': 'in_progress',
                        'details': event.get('details')
                    }
                    thinking_steps.append(step_info)
                    current_attempt = event.get('attempt', 1)

                    # Display live status (compact view)
                    with thinking_status_placeholder.container():
                        st.info(f"{step_info['icon']} {step_info['content']}" +
                               (f" (Attempt {current_attempt}/3)" if current_attempt > 1 else ""))

                elif event_type == 'sql_generated':
                    sql_query = event.get('content')
                    # Mark SQL generation as complete
                    if thinking_steps:
                        thinking_steps[-1]['status'] = 'completed'

                    # Add SQL to thinking steps for the reasoning track
                    thinking_steps.append({
                        'step': 'sql_generated',
                        'content': 'SQL query generated',
                        'icon': '📝',
                        'status': 'completed',
                        'sql_query': sql_query
                    })

                elif event_type == 'validation_result':
                    is_valid = event.get('is_valid')
                    feedback = event.get('feedback')

                    if is_valid:
                        thinking_steps.append({
                            'icon': '✅',
                            'content': 'SQL validation passed!',
                            'status': 'completed'
                        })
                    else:
                        thinking_steps.append({
                            'icon': '⚠️',
                            'content': f'Validation issue: {feedback}',
                            'status': 'warning'
                        })

                elif event_type == 'results':
                    results = event.get('content')
                    results_count = event.get('count', 0)
                    thinking_steps.append({
                        'icon': '💾',
                        'content': f'Query executed successfully ({results_count} rows)',
                        'status': 'completed'
                    })

                elif event_type == 'results_validation':
                    is_valid = event.get('is_valid')
                    feedback = event.get('feedback')

                    if is_valid:
                        thinking_steps.append({
                            'icon': '✅',
                            'content': 'Results validated!',
                            'status': 'completed'
                        })
                    else:
                        thinking_steps.append({
                            'icon': '⚠️',
                            'content': f'Results issue: {feedback}',
                            'status': 'warning'
                        })

                elif event_type == 'retry':
                    reason = event.get('reason')
                    attempt = event.get('attempt')
                    thinking_steps.append({
                        'icon': '🔄',
                        'content': f'Retrying... {reason}',
                        'status': 'retry',
                        'attempt': attempt + 1
                    })

                elif event_type == 'answer_start':
                    # Clear live status and show the full reasoning track
                    thinking_status_placeholder.empty()

                    # Build a natural, conversational thought process display
                    with thought_process_placeholder.expander(
                        f"💭 My Thought Process{f' (took {current_attempt} tries)' if current_attempt > 1 else ''}",
                        expanded=False
                    ):
                        # Group steps by attempt
                        attempts_data = {}
                        for step in thinking_steps:
                            attempt = step.get('attempt', 1)
                            if attempt not in attempts_data:
                                attempts_data[attempt] = {
                                    'sql_query': None,
                                    'validation_passed': False,
                                    'validation_feedback': None,
                                    'results_validation_passed': False,
                                    'results_feedback': None,
                                    'rows_returned': None
                                }

                            # Extract key information
                            if step.get('sql_query'):
                                attempts_data[attempt]['sql_query'] = step['sql_query']
                            elif step.get('status') == 'completed' and '✅' in step.get('icon', ''):
                                if 'SQL validation' in step.get('content', ''):
                                    attempts_data[attempt]['validation_passed'] = True
                                elif 'Results validated' in step.get('content', ''):
                                    attempts_data[attempt]['results_validation_passed'] = True
                            elif step.get('status') == 'warning' and '⚠️' in step.get('icon', ''):
                                if 'Validation issue' in step.get('content', ''):
                                    attempts_data[attempt]['validation_passed'] = False
                                    attempts_data[attempt]['validation_feedback'] = step.get('content', '').replace('Validation issue: ', '')
                                elif 'Results issue' in step.get('content', ''):
                                    attempts_data[attempt]['results_validation_passed'] = False
                                    attempts_data[attempt]['results_feedback'] = step.get('content', '').replace('Results issue: ', '')
                            elif '💾' in step.get('icon', '') and 'rows' in step.get('content', ''):
                                # Extract row count
                                import re
                                match = re.search(r'\((\d+) rows\)', step.get('content', ''))
                                if match:
                                    attempts_data[attempt]['rows_returned'] = match.group(1)

                        # Display each attempt in natural language
                        for attempt_num in sorted(attempts_data.keys()):
                            attempt_info = attempts_data[attempt_num]

                            if attempt_num > 1:
                                st.divider()
                                st.markdown(f"### 🔄 Second Try")
                                if attempt_info['validation_feedback']:
                                    st.markdown(f"*I noticed an issue with my first query: {attempt_info['validation_feedback']}*")
                                elif attempt_info['results_feedback']:
                                    st.markdown(f"*The first results didn't look right: {attempt_info['results_feedback']}*")

                            # Show thought process in natural language
                            if attempt_info['sql_query']:
                                if attempt_num == 1:
                                    st.markdown("**Here's the query I wrote to get your answer:**")
                                else:
                                    st.markdown("**Here's my corrected query:**")
                                st.code(attempt_info['sql_query'], language="sql")

                            # Conversational validation feedback
                            if attempt_info['validation_passed']:
                                st.markdown("✓ *I double-checked the query and it looks correct*")

                            # Show execution in natural language
                            if attempt_info['rows_returned']:
                                st.markdown(f"✓ *I ran this query and found **{attempt_info['rows_returned']} rows** of data*")

                            # Show results validation naturally
                            if attempt_info['results_validation_passed']:
                                st.markdown("✓ *I verified these results make sense for your question*")

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

                elif event_type == 'success':
                    # Query completed successfully
                    pass

                elif event_type == 'done':
                    break

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
