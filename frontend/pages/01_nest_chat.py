"""
NestChat Page - Natural Language Interface for Bird Survey Data
"""

import streamlit as st
import pandas as pd
import random
import requests
from datetime import datetime

# Import from modular structure
from services import (
    ask_question_streaming,
    ask_question_agentic_streaming,
    ask_question_to_backend,
    get_backend_config
)
from components import render_chart, render_map, init_page, render_header, render_sidebar
from utils.bookmarks import get_all_bookmarks, save_bookmark, delete_bookmark, get_bookmark
import json

# API configuration
API_BASE_URL = "http://localhost:8000"

# ============================================================================
# PAGE CONFIGURATION
# ============================================================================

# Initialize page with shared layout
init_page(page_title="NestChat - NestScope", page_icon="💬", layout="wide")

# Render shared header
render_header(page_name="NestChat")

# Handle Loading Bookmarks
if "load_bookmark_id" in st.session_state:
    bookmark_id = st.session_state.load_bookmark_id
    bookmark_data = get_bookmark(bookmark_id)
    if bookmark_data:
        st.session_state.messages = bookmark_data["messages"]
        st.toast(f"✅ Loaded bookmark: {bookmark_data['title']}", icon="📖")
    del st.session_state.load_bookmark_id

# Fetch STAC data for map highlighting
try:
    from services.api_client import get_stac_summary
    stac_data = get_stac_summary()
    stac_colonies_list = [c["id"] for c in stac_data.get("colonies", [])]
except Exception:
    stac_colonies_list = []

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

def export_chat_history_json():
    """Convert chat history to JSON for download."""
    serializable_messages = []
    for msg in st.session_state.messages:
        msg_copy = msg.copy()
        if "dataframe" in msg_copy and msg_copy["dataframe"] is not None:
            msg_copy["dataframe"] = msg_copy["dataframe"].to_dict(orient="records")
        serializable_messages.append(msg_copy)
    return json.dumps(serializable_messages, indent=2)

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

    # Chat Actions Section
    from components import render_sidebar_section
    render_sidebar_section("Chat Controls")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🗑️ Clear", use_container_width=True, help="Clear current chat session"):
            st.session_state.messages = []
            st.rerun()
    with col2:
        if st.session_state.messages:
            if st.button("🔖 Save", use_container_width=True, help="Bookmark this chat"):
                # Get first user message as title
                title = "Untitled Chat"
                for msg in st.session_state.messages:
                    if msg["role"] == "user":
                        title = msg["content"][:30] + ("..." if len(msg["content"]) > 30 else "")
                        break
                save_bookmark(title, st.session_state.messages)
                st.toast("✅ Chat bookmarked!", icon="🔖")
                st.rerun()

    if st.session_state.messages:
        chat_json = export_chat_history_json()
        st.download_button(
            label="📥 Download Chat (JSON)",
            data=chat_json,
            file_name=f"nestchat_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json",
            use_container_width=True
        )

    # Saved Bookmarks Section
    bookmarks = get_all_bookmarks()
    if bookmarks:
        render_sidebar_section("Saved Chats")
        for b in reversed(bookmarks):
            col_b1, col_b2 = st.columns([0.8, 0.2])
            with col_b1:
                if st.button(f"📖 {b['title']}", key=f"load_{b['id']}", use_container_width=True, help=f"Saved on {b['timestamp'][:10]}"):
                    st.session_state.load_bookmark_id = b["id"]
                    st.rerun()
            with col_b2:
                if st.button("🗑️", key=f"del_{b['id']}", help="Delete bookmark"):
                    delete_bookmark(b["id"])
                    st.toast("🗑️ Bookmark deleted")
                    st.rerun()

    # Quick Prompts Section (NestChat-specific)
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
        f'''<p style="font-size: 0.8rem; color: #888; margin-top: -0.5rem; margin-bottom: 1rem;">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" style="vertical-align: middle; margin-right: 4px;">
            <rect x="2" y="2" width="20" height="20" rx="4" fill="#D97757"/>
            <path d="M7 12h10M12 7v10" stroke="white" stroke-width="2" stroke-linecap="round"/>
        </svg>
        Powered by <code style="background: #2d2d2d; padding: 2px 6px; border-radius: 3px; color: #D97757;">{model_name}</code>
        </p>''',
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

            # Reset index to avoid Streamlit bugs
            if not df.empty:
                df = df.reset_index(drop=True)

            show_chart = message.get("show_chart", False)
            chart_type = message.get("chart_type")
            show_map = message.get("show_map", False)

            # Enhanced coordinate detection for historical messages
            cols_lower = [str(col).lower() for col in df.columns]

            # Flexible pattern matching
            lat_patterns = ['latitude', 'lat']
            lon_patterns = ['longitude', 'lon', 'lng', 'long']

            has_lat = any(any(pattern in col for pattern in lat_patterns) for col in cols_lower)
            has_lon = any(any(pattern in col for pattern in lon_patterns) for col in cols_lower)
            has_coords = has_lat and has_lon

            # Force map if coordinates exist (override backend directive)
            if has_coords and not df.empty:
                show_map = True

            # Build tab structure
            tabs_to_render = []
            if show_chart:
                tabs_to_render.append(("data_chart", "📊 Data & Charts"))
            else:
                tabs_to_render.append(("data", "📋 Data Table"))

            if show_map:
                tabs_to_render.append(("map", "🗺️ Map View"))

            # Render visualization
            if len(tabs_to_render) > 1:
                # Multiple tabs
                tab_labels = [label for _, label in tabs_to_render]
                tabs = st.tabs(tab_labels)

                for idx, (tab_type, _) in enumerate(tabs_to_render):
                    with tabs[idx]:
                        if tab_type in ["data", "data_chart"]:
                            # Data table
                            st.dataframe(df, use_container_width=True)
                            csv = df.to_csv(index=False).encode('utf-8')
                            st.download_button(
                                label="📥 Download CSV",
                                data=csv,
                                file_name="bird_data_export.csv",
                                mime="text/csv",
                                key=f"download_hist_{id(message)}_{idx}"
                            )
                            # Chart if needed
                            if tab_type == "data_chart" and chart_type:
                                render_chart(df, chart_type, key_suffix=f"history_{id(message)}")

                        elif tab_type == "map":
                            # Map
                            render_map(df, key=f"map_history_{id(message)}", height=500, show_stac_data=True, stac_colonies_list=stac_colonies_list)
            else:
                # Single view - just data
                with st.expander("View Source Data"):
                    st.dataframe(df, use_container_width=True)
                    csv = df.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="📥 Download CSV",
                        data=csv,
                        file_name="bird_data_export.csv",
                        mime="text/csv",
                        key=f"download_simple_{id(message)}"
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

                elif event_type == 'question_analysis':
                    # Store detailed question analysis
                    analysis_data = event.get('content', {})
                    thinking_steps.append({
                        'step': 'question_analysis',
                        'content': 'Question analyzed',
                        'icon': '🔍',
                        'status': 'completed',
                        'analysis': analysis_data,
                        'attempt': event.get('attempt', 1)
                    })

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
                    reasoning = event.get('reasoning', feedback)

                    if is_valid:
                        thinking_steps.append({
                            'icon': '✅',
                            'content': 'SQL validation passed!',
                            'status': 'completed',
                            'reasoning': reasoning,
                            'step': 'sql_validation'
                        })
                    else:
                        thinking_steps.append({
                            'icon': '⚠️',
                            'content': f'Validation issue: {feedback}',
                            'status': 'warning',
                            'reasoning': reasoning,
                            'step': 'sql_validation'
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
                    reasoning = event.get('reasoning', feedback)

                    if is_valid:
                        thinking_steps.append({
                            'icon': '✅',
                            'content': 'Results validated!',
                            'status': 'completed',
                            'reasoning': reasoning,
                            'step': 'results_validation'
                        })
                    else:
                        thinking_steps.append({
                            'icon': '⚠️',
                            'content': f'Results issue: {feedback}',
                            'status': 'warning',
                            'reasoning': reasoning,
                            'step': 'results_validation'
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

                    # Build a detailed, step-by-step thought process display
                    with thought_process_placeholder.expander(
                        f"🔍 Detailed Reasoning & Validation{f' (took {current_attempt} tries)' if current_attempt > 1 else ''}",
                        expanded=False
                    ):
                        st.markdown("*This shows the step-by-step reasoning process to ensure accuracy and reliability.*")
                        st.markdown("")

                        # Group steps by attempt
                        attempts_data = {}
                        for step in thinking_steps:
                            attempt = step.get('attempt', 1)
                            if attempt not in attempts_data:
                                attempts_data[attempt] = {
                                    'analysis': None,
                                    'sql_query': None,
                                    'sql_validation_reasoning': None,
                                    'validation_passed': False,
                                    'validation_feedback': None,
                                    'results_validation_reasoning': None,
                                    'results_validation_passed': False,
                                    'results_feedback': None,
                                    'rows_returned': None
                                }

                            # Extract key information
                            if step.get('step') == 'question_analysis' and step.get('analysis'):
                                attempts_data[attempt]['analysis'] = step['analysis']
                            elif step.get('sql_query'):
                                attempts_data[attempt]['sql_query'] = step['sql_query']
                            elif step.get('step') == 'sql_validation':
                                attempts_data[attempt]['sql_validation_reasoning'] = step.get('reasoning')
                                attempts_data[attempt]['validation_passed'] = step.get('status') == 'completed'
                                if not attempts_data[attempt]['validation_passed']:
                                    attempts_data[attempt]['validation_feedback'] = step.get('content', '').replace('Validation issue: ', '')
                            elif step.get('step') == 'results_validation':
                                attempts_data[attempt]['results_validation_reasoning'] = step.get('reasoning')
                                attempts_data[attempt]['results_validation_passed'] = step.get('status') == 'completed'
                                if not attempts_data[attempt]['results_validation_passed']:
                                    attempts_data[attempt]['results_feedback'] = step.get('content', '').replace('Results issue: ', '')
                            elif '💾' in step.get('icon', '') and 'rows' in step.get('content', ''):
                                # Extract row count
                                import re
                                match = re.search(r'\((\d+) rows\)', step.get('content', ''))
                                if match:
                                    attempts_data[attempt]['rows_returned'] = match.group(1)

                        # Show question analysis only once (from first attempt)
                        first_attempt_analysis = None
                        for attempt_num in sorted(attempts_data.keys()):
                            if attempts_data[attempt_num]['analysis']:
                                first_attempt_analysis = attempts_data[attempt_num]['analysis']
                                break

                        if first_attempt_analysis:
                            st.markdown("### 📋 Step 1: Question Analysis")
                            analysis = first_attempt_analysis

                            # Handle case where analysis might be a string or improperly formatted
                            if isinstance(analysis, str):
                                st.markdown(f"**Understanding:** {analysis}")
                            elif isinstance(analysis, dict):
                                # Extract summary
                                summary = analysis.get('summary', '')
                                if summary and not summary.startswith('{'):  # Check it's not raw JSON
                                    st.markdown(f"**Understanding:** {summary}")

                                # Extract reasoning steps
                                reasoning_steps = analysis.get('step_by_step_reasoning', [])
                                if reasoning_steps and isinstance(reasoning_steps, list):
                                    # Filter out any non-string items or raw JSON strings
                                    clean_steps = []
                                    for step in reasoning_steps:
                                        if isinstance(step, str) and not step.strip().startswith('{'):
                                            clean_steps.append(step)

                                    if clean_steps:
                                        st.markdown("**Reasoning Steps:**")
                                        for i, reasoning_step in enumerate(clean_steps, 1):
                                            st.markdown(f"{i}. {reasoning_step}")

                                # Extract query type
                                query_type = analysis.get('question_type', '')
                                if query_type and query_type != 'unknown':
                                    st.markdown(f"**Query Type:** {query_type}")

                                # Extract tables needed
                                tables = analysis.get('tables_needed', [])
                                if tables and isinstance(tables, list) and len(tables) > 0:
                                    st.markdown(f"**Tables Required:** {', '.join(tables)}")

                            st.markdown("")

                        # Display each attempt with SQL and validation
                        for attempt_num in sorted(attempts_data.keys()):
                            attempt_info = attempts_data[attempt_num]

                            if attempt_num > 1:
                                st.divider()
                                st.markdown(f"### 🔄 Retry Attempt {attempt_num}")
                                if attempt_info['validation_feedback']:
                                    st.warning(f"**Issue found in previous attempt:** {attempt_info['validation_feedback']}")
                                elif attempt_info['results_feedback']:
                                    st.warning(f"**Results concern from previous attempt:** {attempt_info['results_feedback']}")
                                st.markdown("")

                            # SQL Query
                            if attempt_info['sql_query']:
                                if attempt_num == 1:
                                    st.markdown("### 📝 Step 2: SQL Query Construction")
                                else:
                                    st.markdown("### 📝 Revised SQL Query")
                                st.code(attempt_info['sql_query'], language="sql")
                                st.markdown("")

                            # SQL Validation with detailed checklist (ALWAYS VISIBLE for judges)
                            if attempt_info['sql_validation_reasoning']:
                                if attempt_num == 1:
                                    st.markdown("### ✅ Step 3: SQL Validation")
                                else:
                                    st.markdown("### ✅ SQL Validation")

                                reasoning = attempt_info['sql_validation_reasoning']

                                # Display validation checklist prominently
                                if isinstance(reasoning, dict):
                                    # Check for nested 'reasoning' key
                                    reasoning_details = reasoning.get('reasoning', reasoning)

                                    if isinstance(reasoning_details, dict):
                                        st.markdown("**Validation Checklist:**")
                                        for check_name, check_result in reasoning_details.items():
                                            if check_name not in ['issues_found', 'summary'] and check_result:
                                                # Format check name nicely
                                                display_name = check_name.replace('_', ' ').title()
                                                st.markdown(f"✓ **{display_name}**: {check_result}")

                                        if 'issues_found' in reasoning_details and reasoning_details['issues_found']:
                                            st.markdown("**Issues Found:**")
                                            for issue in reasoning_details['issues_found']:
                                                st.error(f"⚠️ {issue}")

                                        # Show overall status
                                        if attempt_info['validation_passed']:
                                            st.success("✓ **Overall**: All validation checks passed")
                                        else:
                                            st.error(f"✗ **Overall**: {attempt_info['validation_feedback']}")
                                    else:
                                        # Legacy string format
                                        st.markdown(reasoning_details)
                                        if attempt_info['validation_passed']:
                                            st.success("✓ Validation passed")
                                        else:
                                            st.error(f"✗ {attempt_info['validation_feedback']}")
                                elif isinstance(reasoning, str):
                                    st.markdown(reasoning)
                                    if attempt_info['validation_passed']:
                                        st.success("✓ Validation passed")
                                    else:
                                        st.error(f"✗ {attempt_info['validation_feedback']}")

                                st.markdown("")

                            # Query Execution
                            if attempt_info['rows_returned']:
                                if attempt_num == 1:
                                    st.markdown("### ⚡ Step 4: Query Execution")
                                else:
                                    st.markdown("### ⚡ Query Execution")
                                st.markdown(f"Retrieved **{attempt_info['rows_returned']} rows**")
                                st.markdown("")

                            # Results Validation with detailed checklist (ALWAYS VISIBLE for judges)
                            if attempt_info['results_validation_reasoning']:
                                if attempt_num == 1:
                                    st.markdown("### 🔬 Step 5: Results Validation")
                                else:
                                    st.markdown("### 🔬 Results Validation")

                                reasoning = attempt_info['results_validation_reasoning']

                                # Display validation checklist prominently
                                if isinstance(reasoning, dict):
                                    # Check for nested 'reasoning' key
                                    reasoning_details = reasoning.get('reasoning', reasoning)

                                    if isinstance(reasoning_details, dict):
                                        st.markdown("**Results Quality Checklist:**")
                                        for check_name, check_result in reasoning_details.items():
                                            if check_name not in ['issues_found', 'summary'] and check_result:
                                                # Format check name nicely
                                                display_name = check_name.replace('_', ' ').title()
                                                st.markdown(f"✓ **{display_name}**: {check_result}")

                                        if 'issues_found' in reasoning_details and reasoning_details['issues_found']:
                                            st.markdown("**Issues Found:**")
                                            for issue in reasoning_details['issues_found']:
                                                st.error(f"⚠️ {issue}")

                                        # Show overall status
                                        if attempt_info['results_validation_passed']:
                                            st.success("✓ **Overall**: Results validated and match the question")
                                        else:
                                            st.error(f"✗ **Overall**: {attempt_info['results_feedback']}")
                                    else:
                                        # Legacy string format
                                        st.markdown(reasoning_details)
                                        if attempt_info['results_validation_passed']:
                                            st.success("✓ Results validated")
                                        else:
                                            st.error(f"✗ {attempt_info['results_feedback']}")
                                elif isinstance(reasoning, str):
                                    st.markdown(reasoning)
                                    if attempt_info['results_validation_passed']:
                                        st.success("✓ Results validated")
                                    else:
                                        st.error(f"✗ {attempt_info['results_feedback']}")

                                st.markdown("")

                        st.divider()
                        st.markdown("*This multi-step validation process ensures accuracy and reliability of the data you receive.*")

                elif event_type == 'answer_chunk':
                    chunk = event.get('content', '')
                    answer += chunk
                    # Update the answer display with streaming text
                    answer_placeholder.markdown(answer + "▌")

                elif event_type == 'answer_end':
                    # Use clean answer if provided (without visualization directives)
                    clean_answer = event.get('clean_answer')
                    if clean_answer:
                        answer = clean_answer  # Replace accumulated answer with cleaned version
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

            # CRITICAL FIX: Reset index to avoid Streamlit's "Row index out of range" bug
            # This prevents JavaScript errors when displaying certain dataframe sizes
            if not df.empty:
                df = df.reset_index(drop=True)

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

            # DEAD SIMPLE: If Latitude and Longitude columns exist, show map
            has_lat = any('latitude' in str(col).lower() for col in df.columns)
            has_lon = any('longitude' in str(col).lower() for col in df.columns)

            if has_lat and has_lon and not df.empty:
                show_map = True

            response_data = {
                "role": "assistant",
                "content": answer,
                "dataframe": df,
                "show_chart": show_chart,
                "chart_type": chart_type,
                "show_map": show_map
            }

            # Build tab structure
            tabs_to_render = []
            if show_chart:
                tabs_to_render.append(("data_chart", "📊 Data & Charts"))
            else:
                tabs_to_render.append(("data", "📋 Data Table"))

            if show_map:
                tabs_to_render.append(("map", "🗺️ Map View"))

            # Render visualization
            if len(tabs_to_render) > 1:
                # Multiple tabs
                tab_labels = [label for _, label in tabs_to_render]
                tabs = st.tabs(tab_labels)

                for idx, (tab_type, _) in enumerate(tabs_to_render):
                    with tabs[idx]:
                        if tab_type in ["data", "data_chart"]:
                            # Data table
                            st.dataframe(df, use_container_width=True)
                            csv = df.to_csv(index=False).encode('utf-8')
                            st.download_button(
                                label="📥 Download CSV",
                                data=csv,
                                file_name="bird_data_export.csv",
                                mime="text/csv",
                                key=f"download_current_{idx}"
                            )
                            # Chart if needed
                            if tab_type == "data_chart" and chart_type:
                                render_chart(df, chart_type, key_suffix=f"current_{id(response_data)}")

                        elif tab_type == "map":
                            # Map
                            render_map(df, key=f"map_current_{id(response_data)}", height=500, show_stac_data=True, stac_colonies_list=stac_colonies_list)
            else:
                # Single view - just data
                with st.expander("View Source Data"):
                    st.dataframe(df, use_container_width=True)
                    csv = df.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="📥 Download CSV",
                        data=csv,
                        file_name="bird_data_export.csv",
                        mime="text/csv",
                        key="download_simple_current"
                    )

            # LAYER 5: User-facing map troubleshooting (simplified)
            if not show_map and 'ColonyName' in df.columns:
                # Should have map but doesn't - system failure
                with st.expander("🗺️ Why isn't there a map?", expanded=False):
                    st.error("**System Issue:** This colony query should have included geographic coordinates.")
                    st.markdown("**What you can try:**")
                    st.markdown('- Rephrase with: "Show me [your question] **with locations**"')
                    st.markdown('- Ask explicitly: "Map all colonies in [state]"')
                    st.markdown('- Use keywords: "where are", "locations", "coordinates"')

            st.session_state.messages.append(response_data)

        except Exception as e:
            st.error(str(e))
            st.error(f"An unexpected error occurred: {str(e)}")
            st.info("Try rephrasing your question or contact support if the issue persists.")
