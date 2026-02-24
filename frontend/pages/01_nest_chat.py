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

def generate_presentation(description):
    """
    Generate PowerPoint presentation from user description.
    Shows step-by-step progress indicators.
    """
    progress_placeholder = st.empty()
    status_placeholder = st.empty()

    try:
        # Step 1: Planning
        progress_placeholder.progress(0.1)
        status_placeholder.markdown("🤖 **Step 1/4:** Planning report structure and sections...")

        # Make the API call
        progress_placeholder.progress(0.3)
        status_placeholder.markdown("🔍 **Step 2/4:** Querying bird survey data...")

        response = requests.post(
            f"{API_BASE_URL}/presentation/generate",
            json={"description": description},
            timeout=300
        )

        progress_placeholder.progress(0.6)
        status_placeholder.markdown("📊 **Step 3/4:** Generating charts and visualizations...")

        if response.status_code == 200:
            result = response.json()

            progress_placeholder.progress(0.9)
            status_placeholder.markdown("📄 **Step 4/4:** Building PDF report...")

            if result['success']:
                progress_placeholder.progress(1.0)
                status_placeholder.empty()

                st.success(f"✅ PDF report generated successfully!")
                st.markdown(f"**{result['title']}** • {result['num_slides']} sections")

                import os
                filename = os.path.basename(result['file_path'])
                download_url = f"{API_BASE_URL}/presentation/download/{filename}"

                st.markdown(f"""
                    <a href="{download_url}" target="_blank">
                        <button style="
                            background: #D97757;
                            color: white;
                            border: none;
                            padding: 0.75rem 2rem;
                            border-radius: 8px;
                            font-size: 1rem;
                            font-weight: 600;
                            cursor: pointer;
                            margin: 1rem 0;
                            box-shadow: 0 2px 8px rgba(217, 119, 87, 0.3);
                        ">
                            📥 Download PDF Report
                        </button>
                    </a>
                """, unsafe_allow_html=True)

                return True
            else:
                progress_placeholder.empty()
                status_placeholder.empty()
                st.error(f"❌ Error: {result.get('error', 'Unknown error')}")
                return False
        else:
            progress_placeholder.empty()
            status_placeholder.empty()
            st.error(f"❌ Server error: {response.status_code}")
            return False

    except requests.exceptions.Timeout:
        progress_placeholder.empty()
        status_placeholder.empty()
        st.error("❌ Request timed out. The presentation generation took too long. Please try with a simpler request.")
        return False
    except Exception as e:
        progress_placeholder.empty()
        status_placeholder.empty()
        st.error(f"❌ Error: {str(e)}")
        return False

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

# Presentation mode state
if "show_presentation_form" not in st.session_state:
    st.session_state.show_presentation_form = False

if "report_description" not in st.session_state:
    st.session_state.report_description = ""


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

    # Two-column layout: Chat Examples | PDF Report Generator
    col1, col2 = st.columns([1.2, 1], gap="large")

    with col1:
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

    with col2:
        # PDF Report Generator - Prominent Feature Card
        st.markdown("""
            <div style="background: linear-gradient(135deg, rgba(217, 119, 87, 0.15) 0%, rgba(217, 119, 87, 0.08) 100%);
                        padding: 1.25rem; border-radius: 10px; border: 2px solid rgba(217, 119, 87, 0.3);
                        box-shadow: 0 4px 12px rgba(217, 119, 87, 0.15);">
                <div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.5rem;">
                    <span style="font-size: 1.5rem;">📊</span>
                    <h4 style="margin: 0; color: #E5E5E5;">PDF Reports</h4>
                </div>
                <p style="font-size: 0.875rem; color: #B0B0B0; margin: 0 0 1rem 0; line-height: 1.5;">
                    Generate professional analysis reports with charts, maps, and insights
                </p>
            </div>
        """, unsafe_allow_html=True)

        # Show PDF form toggle button
        if st.button("✨ Create PDF Report", key="show_pdf_form", type="primary", use_container_width=True):
            st.session_state.show_presentation_form = True
            st.rerun()

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
# PRESENTATION GENERATOR
# ============================================================================

# Show PDF Report Generator form when activated
if st.session_state.show_presentation_form:
    st.markdown("---")
    st.markdown("""
        <div style="background: rgba(217, 119, 87, 0.05); padding: 1.5rem; border-radius: 10px; border-left: 4px solid #D97757; margin-bottom: 1.5rem;">
            <h3 style="margin: 0 0 0.5rem 0; color: #E5E5E5;">📊 PDF Report Generator</h3>
            <p style="font-size: 0.9rem; color: #B0B0B0; margin: 0;">
                Create professional analysis reports with data-driven insights, charts, and maps
            </p>
        </div>
    """, unsafe_allow_html=True)

    # Template descriptions
    templates = {
        "species_trend": "Create an analysis report examining population trends for major bird species across the Gulf Coast from 2010-2021, including annual counts, geographic patterns, and key findings.",
        "regional": "Create a comprehensive report on bird diversity and colony distribution across Gulf Coast states, with maps, species counts, and conservation priorities.",
        "annual": "Create a detailed summary report of bird survey results for 2021, including top species, colony counts, geographic distribution, and year-over-year changes.",
        "conservation": "Create a conservation-focused report highlighting endangered species trends, priority restoration sites, and data-driven recommendations for stakeholders."
    }

    # Quick template buttons
    st.markdown("**Quick Templates** • Select a pre-configured report:")
    col1, col2 = st.columns(2)

    with col1:
        if st.button("📈 Species Trend Report", key="tmpl_species", use_container_width=True):
            st.session_state.report_description = templates["species_trend"]
            st.rerun()

        if st.button("🗺️ Regional Overview", key="tmpl_regional", use_container_width=True):
            st.session_state.report_description = templates["regional"]
            st.rerun()

    with col2:
        if st.button("📊 Annual Summary", key="tmpl_annual", use_container_width=True):
            st.session_state.report_description = templates["annual"]
            st.rerun()

        if st.button("🦅 Conservation Focus", key="tmpl_conservation", use_container_width=True):
            st.session_state.report_description = templates["conservation"]
            st.rerun()

    st.markdown("---")
    st.markdown("**Custom Report** • Describe what you want to analyze:")

    with st.form("presentation_form"):
        # Main description field with value from session state
        pres_description = st.text_area(
            "Report description",
            value=st.session_state.report_description,
            placeholder="Example: Create an analysis report about Brown Pelican population trends from 2010-2021 across the Gulf Coast. Include annual counts, geographic distribution maps, and comparison with other species. Target audience: wildlife managers.",
            height=120,
            help="Be specific about: topic, time period, geographic scope, key questions, and target audience",
            label_visibility="collapsed"
        )

        # Form buttons
        col1, col2 = st.columns([3, 1])
        with col1:
            generate_button = st.form_submit_button("✨ Generate PDF Report", type="primary", use_container_width=True)
        with col2:
            cancel_button = st.form_submit_button("Cancel", use_container_width=True)

        if generate_button and pres_description:
            # Update session state with current description
            st.session_state.report_description = pres_description
            generate_presentation(pres_description)
        elif generate_button:
            st.warning("Please describe what kind of report you want to create.")
        elif cancel_button:
            st.session_state.show_presentation_form = False
            st.session_state.report_description = ""
            st.rerun()

    st.markdown("---")

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
