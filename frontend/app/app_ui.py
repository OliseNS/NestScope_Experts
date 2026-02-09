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
import base64
from io import BytesIO
from PIL import Image

# ============================================================================
# CONFIGURATION
# ============================================================================

API_BASE_URL = "http://localhost:8000"  # Update this if the FastAPI server runs on a different host/port

# ============================================================================
# CUSTOM STYLING
# ============================================================================

st.markdown(get_custom_css(), unsafe_allow_html=True)
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

def render_chart(df, chart_type, key_suffix=""):
    """
    Render a chart with clean dark Claude theme.

    Args:
        df: DataFrame to visualize
        chart_type: Type of chart ("line" or "bar")
        key_suffix: Unique suffix to prevent duplicate IDs
    """
    if len(df.columns) < 2:
        return

    x_col, y_col = df.columns[0], df.columns[1]

    # Clean Dark Template matching Claude theme
    template = {
        'layout': {
            'paper_bgcolor': '#2D2D2D',
            'plot_bgcolor': '#1A1A1A',
            'font': {'color': '#E5E5E5', 'family': 'Inter'},
            'xaxis': {
                'gridcolor': '#404040',
                'linecolor': '#4A4A4A',
                'zerolinecolor': '#4A4A4A',
                'showline': True,
                'color': '#A0A0A0'
            },
            'yaxis': {
                'gridcolor': '#404040',
                'linecolor': '#4A4A4A',
                'zerolinecolor': '#4A4A4A',
                'showline': True,
                'color': '#A0A0A0'
            },
            'title': {'font': {'size': 20, 'color': '#E5E5E5', 'family': 'Inter'}},
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
        st.plotly_chart(fig, use_container_width=True, key=f"line_chart_{key_suffix}")

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
        st.plotly_chart(fig, use_container_width=True, key=f"bar_chart_{key_suffix}")


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
    lat_col = None
    lon_col = None

    for col in df.columns:
        if col == 'Latitude':
            lat_col = col
        elif col == 'Longitude':
            lon_col = col

    # Fallback to case-insensitive
    if lat_col is None:
        lat_col = next((col for col in df.columns if 'lat' in str(col).lower()), None)
    if lon_col is None:
        lon_col = next((col for col in df.columns if 'lon' in str(col).lower() or 'lng' in str(col).lower()), None)

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
                        border: 2px solid #CCCCCC; z-index: 9999;
                        padding: 12px; border-radius: 10px;
                        box-shadow: 0 4px 12px rgba(0,0,0,0.2);">
                <p style="font-weight: 600; margin-bottom: 10px;
                          border-bottom: 1px solid #CCCCCC; padding-bottom: 8px;
                          color: #333333; font-family: Inter;">
                    Species Legend
                </p>
            '''
            for species in list(unique_species)[:10]:
                color = species_colors[species]
                legend_html += f'<p style="margin: 5px 0; color: #333333; font-family: Inter; font-size: 14px;"><span style="color: {color}; font-size: 18px;">●</span> {species}</p>'

            if len(unique_species) > 10:
                legend_html += f'<p style="margin: 5px 0; font-style: italic; color: #666666; font-family: Inter; font-size: 13px;">+ {len(unique_species) - 10} more...</p>'

            legend_html += '</div>'
            m.get_root().html.add_child(folium.Element(legend_html))

        # Render map
        st_folium(m, width=None, height=600, returned_objects=[])

        # Show summary statistics
        if len(map_df) > 1:
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


def run_cv_inference(image_file, conf_threshold=0.25):
    """
    Send an image to the backend for bird detection inference.
    """
    try:
        files = {"file": image_file}
        response = requests.post(
            f"{API_BASE_URL}/cv/inference",
            files=files,
            params={"conf_threshold": conf_threshold},
            timeout=60
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}


@st.cache_data(ttl=3600)  # Cache for 1 hour
def get_example_images():
    """
    Fetch list of example images from the backend.
    """
    try:
        response = requests.get(f"{API_BASE_URL}/cv/examples", timeout=10)
        response.raise_for_status()
        return response.json().get("examples", [])
    except requests.exceptions.RequestException as e:
        return []


@st.cache_data(ttl=3600)  # Cache for 1 hour
def fetch_example_image(example_name: str):
    """
    Fetch a single example image from the backend and cache it.
    Returns the image bytes or None if fetch fails.
    """
    try:
        response = requests.get(
            f"{API_BASE_URL}/cv/example/{example_name}",
            timeout=10
        )
        if response.status_code == 200:
            return response.content
        return None
    except Exception:
        return None


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

# ============================================================================
# MAIN INTERFACE
# ============================================================================

st.title("NestScope")
st.caption("Natural language interface for Gulf Coast avian monitoring data")

# Create tabs for different functionalities
main_tab, cv_tab = st.tabs(["💬 NestChat", "🦅 NestVision"])

# ============================================================================
# NESTCHAT TAB
# ============================================================================
with main_tab:
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
                df = message["dataframe"]
                chart_type = message.get("chart_type")
                has_map_data = message.get("has_map_data", False)
                is_single_location = message.get("is_single_location", False)

                # Render single-location map
                if is_single_location:
                    st.markdown("---")
                    st.markdown("### 📍 Location Map")
                    render_map(df)
                    st.markdown("---")

                # Render tabs for multi-result visualizations
                if chart_type or (has_map_data and len(df) > 1):
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
                            key=f"download_{message.get('content', '')[:20]}_{id(message)}"
                        )

                        if chart_type:
                            render_chart(df, chart_type, key_suffix=f"history_{id(message)}")

                    # Map Tab
                    if has_map_data and len(tabs) > 1 and len(df) > 1:
                        with tabs[1]:
                            render_map(df)

                else:
                    # Simple data table in expander
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
                is_single_location = not df.empty and len(df) == 1 and has_map_data

                # Store visualization metadata in response_data
                response_data["chart_type"] = chart_type
                response_data["has_map_data"] = has_map_data
                response_data["lat_col"] = lat_col
                response_data["lon_col"] = lon_col
                response_data["is_single_location"] = is_single_location

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
                            render_chart(df, chart_type, key_suffix=f"current_{id(response_data)}")

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

# ============================================================================
# NESTVISION TAB
# ============================================================================
with cv_tab:
    st.markdown("""
        <div class="title-card">
            <h3>🦅 NestVision: Bird Detection & Counting</h3>
            <p>
                Powered by AI computer vision, NestVision automatically detects and counts birds in your images.
                Upload a photo or try our example images to see the model in action.
            </p>
        </div>
    """, unsafe_allow_html=True)

    # Model Information Expander
    with st.expander("ℹ️ About the Model", expanded=False):
        st.markdown("""
        ### Current Model
        **YOLOv6m-based** bird detection trained on avian monitoring data

        ### Important Notes
        - 🔧 This model is currently in **development** and may not be highly accurate
        - 📊 The team is actively **annotating more training data** to improve performance
        - 🚀 A more **robust model** is being developed with improved accuracy

        ### Future Enhancements
        - 🐦 **Bird species classification** using ImageNet-based models
        - 🎯 Identification of **specific bird species**, not just detection and counting
        - 📈 **Combined detection + classification** will provide complete bird analysis

        ### Technical Details
        - **Input image size**: 1024x1024 pixels
        - **Confidence threshold**: Adjustable (default 0.25)
        - **Model architecture**: YOLO-based object detection
        - **Model file**: `server/best.pt`
        """)

    st.markdown("---")

    # Initialize session state for selected example
    if "selected_example_image" not in st.session_state:
        st.session_state.selected_example_image = None
    if "selected_example_name" not in st.session_state:
        st.session_state.selected_example_name = None

    # Upload Section
    st.markdown("### 📤 Upload Your Image")
    uploaded_file = st.file_uploader(
        "Choose an image file containing birds",
        type=['jpg', 'jpeg', 'png', 'bmp', 'tiff', 'webp'],
        help="Upload an image for bird detection and counting",
        key="bird_image_uploader"
    )

    # Confidence threshold slider
    st.markdown("### ⚙️ Detection Settings")
    conf_threshold = st.slider(
        "Confidence Threshold",
        min_value=0.1,
        max_value=0.9,
        value=0.25,
        step=0.05,
        help="Lower values detect more birds but may include false positives. Higher values are more selective."
    )

    st.markdown("---")

    # Example Images Gallery
    col1, col2 = st.columns([4, 1])
    with col1:
        st.markdown("### 🖼️ Example Images Gallery")
    with col2:
        if st.button("🔄 Refresh", help="Reload example images from server"):
            get_example_images.clear()
            st.rerun()

    st.caption("Click on an image below to use it for detection")

    example_images = get_example_images()

    if example_images:
        # Display gallery in a grid
        cols_per_row = 4
        num_rows = (len(example_images) + cols_per_row - 1) // cols_per_row

        for row in range(num_rows):
            cols = st.columns(cols_per_row)
            for col_idx in range(cols_per_row):
                img_idx = row * cols_per_row + col_idx
                if img_idx < len(example_images):
                    with cols[col_idx]:
                        example_name = example_images[img_idx]
                        try:
                            # Fetch and display thumbnail (cached)
                            image_bytes = fetch_example_image(example_name)
                            if image_bytes:
                                img = Image.open(BytesIO(image_bytes))
                                st.image(img, use_container_width=True)

                                # Button to select this image
                                if st.button(
                                    f"Use this image",
                                    key=f"use_example_{img_idx}",
                                    use_container_width=True
                                ):
                                    st.session_state.selected_example_image = image_bytes
                                    st.session_state.selected_example_name = example_name
                                    st.rerun()

                                st.caption(example_name)
                        except Exception as e:
                            st.error(f"Error loading {example_name}")
    else:
        st.info("""
        **No example images available yet.**

        To add example images:
        1. Place bird images in `server/cv_tools/images/`
        2. Supported formats: JPG, PNG, BMP, TIFF, WEBP
        3. Images will automatically appear in this gallery

        For now, upload your own image to get started!
        """)

    st.markdown("---")

    # Determine which image to process
    image_to_process = None
    image_name = None

    if uploaded_file is not None:
        image_to_process = uploaded_file.getvalue()
        image_name = uploaded_file.name
        st.info(f"📁 Using uploaded image: **{image_name}**")
    elif st.session_state.selected_example_image is not None:
        image_to_process = st.session_state.selected_example_image
        image_name = st.session_state.selected_example_name
        st.info(f"🖼️ Using example image: **{image_name}**")

    # Process and display results
    if image_to_process:
        st.markdown("### 🔍 Detection Analysis")

        # Display original image
        st.markdown("#### Original Image")
        original_img = Image.open(BytesIO(image_to_process))
        st.image(original_img, use_container_width=True)

        # Run detection button
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            run_detection = st.button(
                "🚀 Run Bird Detection",
                type="primary",
                use_container_width=True,
                key="run_detection_btn"
            )

        if run_detection:
            with st.spinner("🔄 Running AI detection... This may take a moment."):
                # Create a file-like object
                image_file = BytesIO(image_to_process)
                image_file.name = image_name

                # Run inference
                result = run_cv_inference(image_file, conf_threshold)

                if "error" in result:
                    st.error(f"❌ Inference failed: {result['error']}")
                else:
                    # Display results
                    bird_count = result.get("bird_count", 0)
                    message = result.get("message", "")

                    st.markdown("---")
                    st.markdown("#### 📊 Results")

                    # Show count with appropriate styling
                    if bird_count == 0:
                        st.warning(message)
                        st.info("💡 **Tip**: Try lowering the confidence threshold or use a different image with more visible birds.")
                    else:
                        st.success(message)

                        # Display metrics in columns
                        metric_cols = st.columns(3)
                        with metric_cols[0]:
                            st.metric("🐦 Birds Detected", bird_count)
                        with metric_cols[1]:
                            st.metric("📐 Image Size", f"{original_img.width}×{original_img.height}")
                        with metric_cols[2]:
                            st.metric("🎯 Confidence", f"{conf_threshold:.0%}")

                    # Display annotated image
                    annotated_base64 = result.get("annotated_image_base64", "")
                    if annotated_base64:
                        annotated_bytes = base64.b64decode(annotated_base64)
                        annotated_img = Image.open(BytesIO(annotated_bytes))

                        st.markdown("---")
                        st.markdown("#### 🎨 Annotated Image")
                        st.caption("Birds detected are highlighted with bounding boxes")
                        st.image(annotated_img, use_container_width=True)

                        # Download button
                        col1, col2, col3 = st.columns([1, 2, 1])
                        with col2:
                            st.download_button(
                                label="📥 Download Annotated Image",
                                data=annotated_bytes,
                                file_name=f"nestvision_detected_{image_name}",
                                mime="image/jpeg",
                                use_container_width=True,
                                type="secondary"
                            )

                    # Show detection details in expandable section
                    if bird_count > 0:
                        with st.expander("🔍 View Detailed Detection Data", expanded=False):
                            detections = result.get("detections", [])
                            if detections:
                                st.markdown(f"**Total Detections:** {len(detections)}")
                                st.markdown("**Detection Details:**")

                                # Create a formatted table
                                detection_data = []
                                for i, det in enumerate(detections, 1):
                                    bbox = det.get('bbox', [])
                                    detection_data.append({
                                        "Detection #": i,
                                        "Confidence": f"{det.get('confidence', 0):.2%}",
                                        "Bounding Box": f"[{bbox[0]:.0f}, {bbox[1]:.0f}, {bbox[2]:.0f}, {bbox[3]:.0f}]",
                                        "Class ID": det.get('class_id', 0)
                                    })

                                st.dataframe(pd.DataFrame(detection_data), use_container_width=True)

                                # Raw JSON data
                                with st.expander("📄 Raw JSON Data"):
                                    st.json({
                                        "total_detections": len(detections),
                                        "detections": detections
                                    })
    else:
        # Show instructions when no image is selected
        st.info("""
        ### 👆 Get Started

        **To detect birds in an image:**
        1. **Upload** your own image using the file uploader above, or
        2. **Select** an example image from the gallery above
        3. Adjust the **confidence threshold** if needed
        4. Click **"Run Bird Detection"** to analyze the image

        The AI will identify and count all birds in your image!
        """)