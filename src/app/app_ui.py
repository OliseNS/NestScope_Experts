import streamlit as st
import pandas as pd
import requests
import random
import time
import threading
import itertools
import plotly.express as px
from folium.plugins import Fullscreen
from streamlit.runtime.scriptrunner import add_script_run_ctx
import folium
from streamlit_folium import st_folium
import json
from styles import get_custom_css

# ============================================================================
# CONFIGURATION
# ============================================================================

API_BASE_URL = "http://localhost:8000"  # Update this if the FastAPI server runs on a different host/port

# ============================================================================
# CUSTOM STYLING
# ============================================================================

st.markdown(get_custom_css(), unsafe_allow_html=True)

st.session_state.chat_placeholder = ""
# ============================================================================
# SESSION STATE INITIALIZATION
# ============================================================================

if "messages" not in st.session_state:
    st.session_state.messages = []

if "query_history" not in st.session_state:
    st.session_state.query_history = []

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def render_chart(df, chart_type):
    """
    Render a chart with clean light Claude theme.
    """
    if len(df.columns) < 2:
        return

    x_col, y_col = df.columns[0], df.columns[1]

    # Clean Light Template matching Claude theme
    template = {
        'layout': {
            'paper_bgcolor': '#FFFFFF',
            'plot_bgcolor': '#FAFAF8',
            'font': {'color': '#2D2D2D', 'family': 'Inter'},
            'xaxis': {
                'gridcolor': '#E5E5E3',
                'linecolor': '#D4D4D2',
                'zerolinecolor': '#D4D4D2',
                'showline': True,
                'color': '#6B6B6B'
            },
            'yaxis': {
                'gridcolor': '#E5E5E3',
                'linecolor': '#D4D4D2',
                'zerolinecolor': '#D4D4D2',
                'showline': True,
                'color': '#6B6B6B'
            },
            'title': {'font': {'size': 20, 'color': '#2D2D2D', 'family': 'Inter'}},
            'margin': {'l': 60, 'r': 40, 't': 60, 'b': 60}
        }
    }

    if chart_type == "line":
        fig = px.line(
            df,
            x=x_col,
            y=y_col,
            title="Trend Analysis",
            labels={x_col: x_col.replace('_', ' ').title(),
                    y_col: y_col.replace('_', ' ').title()}
        )
        # Use Claude orange line
        fig.update_traces(line_color='#D97757', line_width=3)
        fig.update_layout(template['layout'])
        st.plotly_chart(fig, use_container_width=True)

    elif chart_type == "bar":
        # Limit to top 15 for readability
        if len(df) > 15:
            df = df.nlargest(15, y_col)

        fig = px.bar(
            df,
            x=x_col,
            y=y_col,
            title="Comparison Analysis",
            labels={x_col: x_col.replace('_', ' ').title(),
                    y_col: y_col.replace('_', ' ').title()}
        )
        # Use Claude orange bars
        fig.update_traces(marker_color='#D97757')
        fig.update_layout(template['layout'])
        st.plotly_chart(fig, use_container_width=True)


def detect_chart_type(df):
    """
    Intelligently detect chart type.
    """
    if df is None or len(df.columns) < 2:
        return None

    x_col, y_col = df.columns[0], df.columns[1]
    x_dtype = df.dtypes[0]
    y_dtype = df.dtypes[1]

    if not pd.api.types.is_numeric_dtype(y_dtype):
        return None

    # Don't chart if the Y-axis column looks like a dimension
    dimension_keywords = ['year', 'month', 'day', 'date', 'id', 'latitude', 'longitude', 'lat', 'lon']
    # Check if y_col CONTAINS any dimension keyword (not just equals)
    if any(keyword in y_col.lower() for keyword in dimension_keywords):
        return None

    temporal_keywords = ['year', 'date', 'time', 'month', 'day', 'season']
    if any(keyword in x_col.lower() for keyword in temporal_keywords):
        return 'line'

    if pd.api.types.is_object_dtype(x_dtype) or pd.api.types.is_integer_dtype(x_dtype):
        return 'bar'

    return None



def render_map(df):
    """
    Render an enhanced Folium map with interactive features.
    """
    # Find coordinate columns (case-insensitive)
    # Be specific to avoid matching "ColonyName" (which contains "lon")
    lat_col = next((col for col in df.columns if 'latit' in col.lower()), None)
    lon_col = next((col for col in df.columns if 'longi' in col.lower() or 'lng' in col.lower()), None)

    if not lat_col or not lon_col:
        st.info("💡 No geographic coordinates found in results.")
        with st.expander("ℹ️ How to get map data"):
            st.markdown("""
            To see results on a map, try queries like:
            - "Show all colonies in Louisiana with their locations"
            - "List bird colonies in Chandeleur Islands"
            - "Where are the brown pelican colonies in 2021?"
            - "Map the locations of sandwich tern nests"
            """)
        return

    try:
        # Clean and validate coordinates
        map_df = df.copy()
        map_df[lat_col] = pd.to_numeric(map_df[lat_col], errors='coerce')
        map_df[lon_col] = pd.to_numeric(map_df[lon_col], errors='coerce')

        # Remove rows with missing coordinates
        map_df = map_df.dropna(subset=[lat_col, lon_col])

        # Filter to valid coordinate ranges (Gulf of Mexico region)
        # Latitude: 24-31°N, Longitude: -98 to -80°W
        valid_mask = (
            (map_df[lat_col] >= 24) & (map_df[lat_col] <= 31) &
            (map_df[lon_col] >= -98) & (map_df[lon_col] <= -80)
        )
        map_df = map_df[valid_mask]

        if map_df.empty:
            st.warning("⚠️ No valid coordinates found in the Gulf region.")
            st.info("Valid coordinates: Latitude 24-31°N, Longitude -98 to -80°W")
            with st.expander("🔍 Debug Info"):
                st.write(f"**Detected columns:**")
                st.write(f"- Latitude column: `{lat_col}`")
                st.write(f"- Longitude column: `{lon_col}`")
                st.write(f"\n**All columns:** {', '.join([f'`{col}`' for col in df.columns])}")
                st.write(f"\n**Data stats:**")
                st.write(f"- Original rows: {len(df)}")
                st.write(f"- After numeric conversion: {len(df.dropna(subset=[lat_col, lon_col]))}")
                st.write(f"\n**Sample coordinates:**")
                st.dataframe(df[[lat_col, lon_col]].head())
            return

        # Calculate center and smart zoom
        avg_lat = map_df[lat_col].mean()
        avg_lon = map_df[lon_col].mean()

        lat_range = map_df[lat_col].max() - map_df[lat_col].min()
        lon_range = map_df[lon_col].max() - map_df[lon_col].min()
        max_range = max(lat_range, lon_range)

        # Smart zoom based on data spread
        if max_range < 0.1:
            zoom = 12
        elif max_range < 0.5:
            zoom = 10
        elif max_range < 2:
            zoom = 8
        else:
            zoom = 7

        # Create map with light clean theme
        m = folium.Map(
            location=[avg_lat, avg_lon],
            zoom_start=zoom,
            tiles='CartoDB positron',
            control_scale=True
        )

        # Add fullscreen button
        Fullscreen().add_to(m)

        # Color markers by species if available
        species_col = next((col for col in df.columns if 'species' in col.lower()), None)

        species_colors = {}
        unique_species = []
        if species_col:
            unique_species = map_df[species_col].unique()
            color_palette = ['blue', 'red', 'green', 'purple', 'orange', 'darkred',
                             'beige', 'darkblue', 'darkgreen', 'cadetblue',
                             'darkpurple', 'pink', 'lightblue', 'lightgreen']
            for idx, species in enumerate(unique_species):
                species_colors[species] = color_palette[idx % len(color_palette)]

        # Add markers
        for idx, row in map_df.iterrows():
            # Build tooltip with all relevant columns
            tooltip_lines = []
            for col in df.columns:
                if col not in [lat_col, lon_col] and pd.notna(row[col]):
                    val = row[col]
                    if isinstance(val, float):
                        val = f"{val:.2f}" if val < 1000 else f"{val:,.0f}"
                    tooltip_lines.append(f"<b>{col}:</b> {val}")

            tooltip_text = "<br>".join(tooltip_lines) if tooltip_lines else "No data"

            # Color by species if available
            marker_color = 'black'
            if species_col and pd.notna(row[species_col]):
                marker_color = species_colors.get(row[species_col], 'black')

            folium.Marker(
                location=[row[lat_col], row[lon_col]],
                tooltip=folium.Tooltip(tooltip_text, sticky=True),
                popup=folium.Popup(tooltip_text, max_width=300),
                icon=folium.Icon(color=marker_color, icon='info-sign', prefix='glyphicon')
            ).add_to(m)

        # Add legend if multiple species
        if species_col and len(unique_species) > 1:
            legend_html = '''
            <div style="position: fixed; bottom: 50px; right: 50px;
                        width: 220px; background-color: #FFFFFF;
                        border: 2px solid #E5E5E3; z-index: 9999;
                        padding: 12px; border-radius: 10px;
                        box-shadow: 0 4px 12px rgba(0,0,0,0.1);">
                <p style="font-weight: 600; margin-bottom: 10px;
                          border-bottom: 1px solid #E5E5E3; padding-bottom: 8px;
                          color: #2D2D2D; font-family: Inter;">
                    Species Legend
                </p>
            '''
            for species in list(unique_species)[:10]:
                color = species_colors[species]
                legend_html += f'<p style="margin: 5px 0; color: #2D2D2D; font-family: Inter; font-size: 14px;"><span style="color: {color}; font-size: 18px;">●</span> {species}</p>'

            if len(unique_species) > 10:
                legend_html += f'<p style="margin: 5px 0; font-style: italic; color: #6B6B6B; font-family: Inter; font-size: 13px;">+ {len(unique_species) - 10} more...</p>'

            legend_html += '</div>'
            m.get_root().html.add_child(folium.Element(legend_html))

        # Render map
        st_folium(m, width=None, height=600, returned_objects=[])

        # Show summary statistics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("📍 Locations", len(map_df))
        with col2:
            if species_col:
                st.metric("🦅 Species", len(unique_species))
            else:
                st.metric("🗺️ Zoom", zoom)
        with col3:
            st.metric("📐 Area (°)", f"{max_range:.2f}")

    except Exception as e:
        st.error(f"❌ Error generating map: {str(e)}")
        with st.expander("🔧 Debug Info"):
            st.write(f"**Latitude column:** {lat_col}")
            st.write(f"**Longitude column:** {lon_col}")
            st.write(f"**DataFrame shape:** {df.shape}")
            st.write(f"**Error:** {str(e)}")


def ask_question_to_backend(question, model="anthropic/claude-opus-4.5"):
    """
    Send a question to the FastAPI backend and return the response.
    """
    try:
        response = requests.post(
            f"{API_BASE_URL}/ask",
            json={"question": question, "model": model},
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"success": False, "error": str(e)}


def ask_question_streaming(question, model="anthropic/claude-opus-4.5"):
    """
    Send a question to the FastAPI backend and stream the response.
    Yields events: {'type': 'sql_query'|'results'|'answer_chunk'|'error'|'done', 'content': ...}
    """
    try:
        response = requests.post(
            f"{API_BASE_URL}/ask/stream",
            json={"question": question, "model": model},
            stream=True,
            timeout=60
        )
        response.raise_for_status()

        # Process the SSE stream
        for line in response.iter_lines():
            if line:
                line = line.decode('utf-8')
                if line.startswith('data: '):
                    data = line[6:]  # Remove 'data: ' prefix
                    try:
                        event = json.loads(data)
                        yield event
                    except json.JSONDecodeError:
                        continue
    except requests.exceptions.RequestException as e:
        yield {"type": "error", "content": str(e)}


def get_stats_from_backend():
    """
    Fetch database statistics from the FastAPI backend.
    """
    try:
        response = requests.get(f"{API_BASE_URL}/stats", timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"success": False, "error": str(e)}


# ============================================================================
# LOADING ANIMATION
# ============================================================================

class LoadingCarousel:
    """
    Context manager to display a carousel of loading messages.
    """

    def __init__(self, placeholder, messages):
        self.placeholder = placeholder
        self.messages = messages
        self.stop_event = threading.Event()
        self.thread = threading.Thread(target=self._animate)
        add_script_run_ctx(self.thread)

    def _animate(self):
        for message in itertools.cycle(self.messages):
            if self.stop_event.is_set():
                break
            self.placeholder.markdown(f"🔄 **{message}**")
            time.sleep(1.5)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop_event.set()
        self.thread.join()
        self.placeholder.empty()

# ============================================================================
# SIDEBAR
# ============================================================================

with st.sidebar:
    st.markdown("### NestScope")
    st.caption("Avian Monitoring Analytics")
    st.markdown("---")

    # Quick Prompts Section
    st.markdown("#### Examples")

    examples = [
        ("Trends", "Show brown pelican trends from 2015 to 2021"),
        ("Top Species", "What were the top 5 species in 2021?"),
        ("Locations", "Show all bird colonies in Louisiana with their locations"),
        ("Annual Counts", "How many observations were recorded per year?"),
        ("Diversity", "Compare species diversity across different colonies")
    ]

    for label, full_prompt in examples:
        if st.button(label, key=f"quick_prompt_{label}", use_container_width=True):
            st.session_state.current_question = full_prompt
            st.rerun()

    st.markdown("---")

    # Session History Section
    if st.session_state.query_history:
        st.markdown("#### Recent")
        for i, (q_label, q_prompt) in enumerate(reversed(st.session_state.query_history[-5:])):
            display_label = (q_label[:30] + '...') if len(q_label) > 32 else q_label
            if st.button(display_label, key=f"hist_{i}", use_container_width=True, help=q_prompt):
                st.session_state.current_question = q_prompt
                st.rerun()

        if st.button("Clear History", key="clear_hist", use_container_width=True):
            st.session_state.query_history = []
            st.rerun()

        st.markdown("---")

    # Data Source Section
    st.markdown("#### About")
    st.info(
        "**Data Source:** NOAA DIVER Database\n\n"
        "Gulf Coast avian monitoring (2010-2021) covering TX, LA, MS, AL, and FL.\n\n"
        "Part of the Deepwater Horizon response program."
    )

# ============================================================================
# MAIN INTERFACE
# ============================================================================

st.title("NestScope")
st.caption("Natural language interface for Gulf Coast avian monitoring data")

# Welcome Card
if "messages" not in st.session_state:
    st.session_state.messages = []

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
            st.dataframe(message["dataframe"], use_container_width=True)

# ============================================================================
# USER INPUT HANDLING
# ============================================================================

# Placeholder examples for the input box
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

# Initialize the placeholder if not already set
if "chat_placeholder" not in st.session_state:
    st.session_state.chat_placeholder = f'Try "{random.choice(placeholder_examples)}"'

# Always render the chat input at the bottom (must be called every render)
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

            status_placeholder.markdown("🔄 **Processing your question...**")

            # Try streaming first, fallback to regular API if it fails
            try:
                for event in ask_question_streaming(prompt):
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
                response = ask_question_to_backend(prompt)

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
                "dataframe": df
            }

            # Detect chart type and map data
            cols_lower = [str(col).lower() for col in df.columns]
            # Use 'latit' and 'longi' to avoid matching 'ColonyName' (which contains 'lon')
            has_lat = any('latit' in col for col in cols_lower)
            has_lon = any('longi' in col or 'lng' in col for col in cols_lower)

            if has_lat and has_lon:
                chart_type = None
            else:
                chart_type = detect_chart_type(df)

            # Find coordinate columns with specific patterns to avoid false matches
            lat_col = next((col for col in df.columns if 'latit' in str(col).lower()), None)
            lon_col = next((col for col in df.columns if 'longi' in str(col).lower() or 'lng' in str(col).lower()), None)

            # Fallback to exact column names
            if lat_col is None and 'Latitude' in df.columns:
                lat_col = 'Latitude'
            if lon_col is None and 'Longitude' in df.columns:
                lon_col = 'Longitude'

            has_map_data = lat_col is not None and lon_col is not None

            # Render map for single-location queries
            if not df.empty and len(df) == 1 and has_map_data:
                st.markdown("---")
                st.markdown("### 📍 Location Map")
                render_map(df)
                st.markdown("---")

            if chart_type or has_map_data:
                # Tabs for data, charts, and maps
                tab_labels = []

                if chart_type:
                    tab_labels.append("📊 Data & Charts")
                else:
                    tab_labels.append("📋 Data Table")

                if has_map_data and len(df) > 1:
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

                    if chart_type:
                        response_data["chart_type"] = chart_type
                        render_chart(df, chart_type)

                # Map Tab
                if has_map_data and len(tabs) > 1 and len(df) > 1:
                    with tabs[1]:
                        render_map(df)

            else:
                # Simple data table
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