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
    execute_custom_sql,
    get_ai_insights
)
from components import render_chart, render_map, render_sidebar_header
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

# Query Editor session state
if "query_editor_sql" not in st.session_state:
    st.session_state.query_editor_sql = ""

if "query_editor_results" not in st.session_state:
    st.session_state.query_editor_results = None

if "query_editor_insights" not in st.session_state:
    st.session_state.query_editor_insights = None

if "show_insights_button" not in st.session_state:
    st.session_state.show_insights_button = False

# ============================================================================
# SIDEBAR
# ============================================================================

with st.sidebar:
    # Render brand header
    render_sidebar_header()

    # Quick Prompts Section
    st.markdown("""
        <div style="
            font-size: 0.6875rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            color: #A0A0A0;
            margin: 1.5rem 0 0.75rem;
            padding: 0 0.5rem;
            opacity: 0.7;
        ">Quick Examples</div>
    """, unsafe_allow_html=True)

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
        st.markdown("---")
        st.markdown("""
            <div style="
                font-size: 0.6875rem;
                font-weight: 600;
                text-transform: uppercase;
                letter-spacing: 0.08em;
                color: #A0A0A0;
                margin: 1.5rem 0 0.75rem;
                padding: 0 0.5rem;
                opacity: 0.7;
            ">Recent Queries</div>
        """, unsafe_allow_html=True)

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

# Create tabs for Chat and Query Editor
tab1, tab2 = st.tabs(["💬 Chat", "🔧 Query Editor"])

# ============================================================================
# TAB 1: CHAT INTERFACE
# ============================================================================

with tab1:
    # Welcome Card
    if not st.session_state.messages:
        st.markdown("""
            <div class="title-card">
                <h3>How can I help you today?</h3>
                <p>
                    I can help you explore bird survey data from the Gulf Coast (2010-2021).
                    Ask about population trends, colony locations, species distribution, or habitat patterns across Texas, Louisiana, Mississippi, Alabama, and Florida.
                </p>
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

# ============================================================================
# TAB 2: QUERY EDITOR
# ============================================================================

with tab2:
    st.markdown("""
    <div style="background: var(--claude-surface); border: 1px solid var(--claude-border); border-radius: 12px; padding: 1.5rem; margin-bottom: 1.5rem;">
        <h4 style="color: var(--claude-orange); margin-top: 0; font-size: 1.125rem; font-weight: 600;">🔧 SQL Query Editor</h4>
        <p style="color: var(--claude-text-light); font-size: 0.875rem; line-height: 1.6; margin: 0;">
            For advanced users: Write custom SQL queries to explore the database directly. After running a query, click the AI Insights button to get intelligent analysis of your results.
        </p>
    </div>
    """, unsafe_allow_html=True)

    # SQL Query Input
    st.markdown("### Write Your Query")

    # Example queries in expander
    with st.expander("📚 View Example Queries"):
        st.markdown("""
        **Get top 10 colonies by bird count:**
        ```sql
        SELECT ColonyName, State, Latitude, Longitude, SUM(Birds) as total_birds
        FROM colony_totals
        WHERE Latitude IS NOT NULL AND Longitude IS NOT NULL
        GROUP BY ColonyName, State, Latitude, Longitude
        ORDER BY total_birds DESC
        LIMIT 10;
        ```

        **Species distribution by year:**
        ```sql
        SELECT Year, SpeciesCode, SUM(Nests) as total_nests
        FROM colony_totals
        WHERE Year >= 2015
        GROUP BY Year, SpeciesCode
        ORDER BY Year, total_nests DESC;
        ```

        **Colonies in Louisiana with coordinates:**
        ```sql
        SELECT DISTINCT ColonyName, State, Latitude, Longitude, GeoRegion
        FROM colony_totals
        WHERE State = 'LA' AND Latitude IS NOT NULL
        ORDER BY ColonyName;
        ```

        **Available tables:** `colony_totals`, `species_codes`, `colony_coordinates`, `colony_inventory`, `species_data_2010`, `species_data_2011_2013`, `species_data_2015_2021`
        """)

    # Text area for SQL input
    sql_query = st.text_area(
        "SQL Query",
        value=st.session_state.query_editor_sql,
        height=200,
        placeholder="SELECT * FROM colony_totals LIMIT 10;",
        help="Write your SQL query here. Use exact column names (case-sensitive): ColonyName, Latitude, Longitude, etc."
    )

    # Update session state
    st.session_state.query_editor_sql = sql_query

    # Execute button
    col1, col2 = st.columns([1, 4])
    with col1:
        execute_button = st.button("▶️ Execute Query", type="primary", use_container_width=True)
    with col2:
        if st.button("🗑️ Clear", use_container_width=True):
            st.session_state.query_editor_sql = ""
            st.session_state.query_editor_results = None
            st.session_state.query_editor_insights = None
            st.session_state.show_insights_button = False
            st.rerun()

    # Execute query when button is clicked
    if execute_button and sql_query.strip():
        with st.spinner("Executing query..."):
            response = execute_custom_sql(sql_query)

            if response.get("success"):
                st.session_state.query_editor_results = response.get("results")
                st.session_state.show_insights_button = True
                st.session_state.query_editor_insights = None  # Reset insights
                st.success(f"✅ Query executed successfully! Found {response.get('results_count', 0)} rows.")
            else:
                st.error(f"❌ Query failed: {response.get('error', 'Unknown error')}")
                st.session_state.show_insights_button = False

    # Display results if available
    if st.session_state.query_editor_results:
        st.markdown("---")
        st.markdown("### Query Results")

        df = pd.DataFrame(st.session_state.query_editor_results)

        # Display data table
        st.dataframe(df, use_container_width=True, height=400)

        # Download button
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download Results as CSV",
            data=csv,
            file_name="query_results.csv",
            mime="text/csv",
        )

        st.markdown("")  # Spacing

        # AI Insights button
        if st.session_state.show_insights_button:
            col1, col2, col3 = st.columns([2, 1, 2])
            with col2:
                if st.button("✨ AI Insights", type="secondary", use_container_width=True):
                    with st.spinner("Generating insights..."):
                        # Determine sample size
                        sample_size = min(50, len(df))

                        insights_response = get_ai_insights(
                            st.session_state.query_editor_results,
                            sample_size=sample_size
                        )

                        if insights_response.get("success"):
                            st.session_state.query_editor_insights = insights_response.get("insights")
                        else:
                            st.error(f"Failed to generate insights: {insights_response.get('error')}")

        # Display insights if generated
        if st.session_state.query_editor_insights:
            st.markdown("---")
            st.markdown("### ✨ AI-Powered Insights")
            st.markdown(f"""
            <div style="background: var(--claude-surface); border-left: 3px solid var(--claude-orange); border-radius: 8px; padding: 1.5rem; margin-top: 1rem;">
                {st.session_state.query_editor_insights.replace('\n', '<br>')}
            </div>
            """, unsafe_allow_html=True)
