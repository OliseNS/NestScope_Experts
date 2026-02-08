import streamlit as st
import pandas as pd
import plotly.express as px
import folium
from streamlit_folium import st_folium
from folium.plugins import Fullscreen
import sys
import os
import random
import time
import threading
import itertools
from streamlit.runtime.scriptrunner import add_script_run_ctx

# ============================================================================
# INITIALIZATION & IMPORTS
# ============================================================================

# Add project root to path for chatbot import
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

try:
    from sql_chatbot import SQLChatbot
except ImportError as e:
    st.error(f"Cannot import SQLChatbot: {e}")
    st.info("Make sure sql_chatbot.py exists in the project root directory.")
    st.stop()

# ============================================================================
# PAGE CONFIGURATION
# ============================================================================

st.set_page_config(
    page_title="NestScope",
    page_icon="🦅",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================================
# PROFESSIONAL LIGHT THEME CSS (Structured & Contrast)
# ============================================================================

st.markdown("""
<style>
    /* Import Modern Font */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    /* ===== GLOBAL SETTINGS ===== */
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
        color: #111827;
    }

    /* Global Background - Off-white/Light Gray for contrast */
    .stApp {
        background-color: #F3F4F6;
    }

    /* Headers */
    h1, h2, h3, h4 {
        color: #111827 !important;
        font-weight: 700 !important;
    }

    h1 {
        font-size: 2.2rem !important;
        margin-bottom: 1rem !important;
    }

    /* ===== SIDEBAR STYLING ===== */
    [data-testid="stSidebar"] {
        background-color: #FFFFFF; /* White sidebar */
        border-right: 1px solid #E5E7EB;
    }

    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {
        color: #111827 !important;
    }

    [data-testid="stSidebar"] p, [data-testid="stSidebar"] label, [data-testid="stSidebar"] .stMarkdown {
        color: #4B5563 !important;
    }

    /* Sidebar Headers */
    [data-testid="stSidebar"] h4 {
        color: #6B7280 !important;
        text-transform: uppercase;
        font-size: 0.75rem;
        letter-spacing: 0.05em;
        margin-top: 1.5rem;
    }

    /* ===== BOXED CONTAINERS (Cards) ===== */

    /* Assistant Message - DISTINCT WHITE BOX */
    [data-testid="stChatMessageContent"] {
        background-color: #FFFFFF;
        border: 1px solid #E5E7EB;
        border-radius: 12px;
        padding: 1.5rem;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
        color: #111827;
        margin-bottom: 1rem;
    }

    /* User Message - DISTINCT GRAY BOX */
    [data-testid="stChatMessage"]:has([data-testid="stChatMessageContent"]:first-child) [data-testid="stChatMessageContent"] {
        background-color: #E5E7EB; /* Darker gray than background */
        border: 1px solid #D1D5DB;
        color: #111827;
        box-shadow: none;
    }

    /* Avatars */
    .stChatMessage .stAvatar {
        background-color: #FFFFFF !important;
        border: 1px solid #E5E7EB;
    }

    /* ===== CHAT INPUT - FLOATING BOX ===== */
    [data-testid="stChatInput"] {
        background-color: transparent !important;
        padding-bottom: 2rem !important;
    }

    [data-testid="stChatInput"] > div {
        background-color: #FFFFFF !important;
        border: 1px solid #D1D5DB !important;
        border-radius: 16px !important;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1) !important;
        padding: 5px;
    }

    [data-testid="stChatInput"]:focus-within > div {
        border-color: #111827 !important;
        box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1) !important;
    }

    [data-testid="stChatInput"] textarea {
        color: #111827 !important;
    }

    [data-testid="stChatInput"] button {
        background-color: #111827 !important;
        color: white !important;
        border-radius: 8px !important;
    }

    /* ===== WELCOME CARD (The 'Box' User Wanted) ===== */
    .title-card {
        background-color: #FFFFFF;
        padding: 3rem 2rem;
        border-radius: 16px;
        border: 1px solid #E5E7EB;
        text-align: center;
        margin-bottom: 2rem;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
    }

    .title-card h3 {
        color: #111827 !important;
        font-size: 2rem;
        margin-bottom: 1rem;
    }

    .title-card p {
        color: #4B5563 !important;
        font-size: 1.1rem;
        line-height: 1.7;
        max-width: 700px;
        margin: 0 auto;
    }

    /* ===== BUTTONS ===== */
    .stButton button {
        background-color: #FFFFFF;
        color: #111827;
        border: 1px solid #D1D5DB;
        border-radius: 8px;
        font-weight: 600;
        box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
    }

    .stButton button:hover {
        background-color: #F9FAFB;
        border-color: #9CA3AF;
        color: #000000;
    }

    /* ===== DATAFRAME & TABS ===== */
    [data-testid="stDataFrame"] {
        background-color: #FFFFFF;
        border: 1px solid #E5E7EB;
        border-radius: 8px;
        padding: 1px;
    }

    .stTabs [data-baseweb="tab-list"] {
        background-color: #FFFFFF;
        padding: 0.5rem;
        border-radius: 8px;
        border: 1px solid #E5E7EB;
        margin-bottom: 1rem;
    }

    .stTabs [data-baseweb="tab"] {
        border-radius: 6px;
        padding: 0.5rem 1rem;
        border: none;
    }

    .stTabs [aria-selected="true"] {
        background-color: #111827 !important;
        color: #FFFFFF !important;
    }


    /* ===== SCROLLBAR ===== */
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }
    ::-webkit-scrollbar-track {
        background: transparent;
    }
    ::-webkit-scrollbar-thumb {
        background: #D1D5DB;
        border-radius: 4px;
    }
    ::-webkit-scrollbar-thumb:hover {
        background: #9CA3AF;
    }

    /* Hide Default Elements */
    #MainMenu { display: none !important; }
    footer { display: none !important; }
    .viewerBadge_container__1QSob { display: none !important; }

</style>
""", unsafe_allow_html=True)


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def render_chart(df, chart_type):
    """
    Render a chart with CLEAN LIGHT THEME (White/Black).
    """
    if len(df.columns) < 2:
        return

    x_col, y_col = df.columns[0], df.columns[1]

    # Minimalist Light Template
    template = {
        'layout': {
            'paper_bgcolor': 'white',
            'plot_bgcolor': 'white',
            'font': {'color': '#111827', 'family': 'Inter'},
            'xaxis': {
                'gridcolor': '#F3F4F6',
                'linecolor': '#E5E7EB',
                'zerolinecolor': '#E5E7EB',
                'showline': True
            },
            'yaxis': {
                'gridcolor': '#F3F4F6',
                'linecolor': '#E5E7EB',
                'zerolinecolor': '#E5E7EB',
                'showline': True
            },
            'title': {'font': {'size': 20, 'color': '#000000', 'family': 'Inter', 'weight': 700}},
            'margin': {'l': 40, 'r': 40, 't': 60, 'b': 40}
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
        # Use simple black line or very dark gray
        fig.update_traces(line_color='#000000', line_width=2.5)
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
        # Use black bars
        fig.update_traces(marker_color='#000000')
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
    lat_col = next((col for col in df.columns if 'lat' in col.lower()), None)
    lon_col = next((col for col in df.columns if 'lon' in col.lower() or 'lng' in col.lower()), None)

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
        map_df = map_df.dropna(subset=[lat_col, lon_col])

        # Filter to valid coordinate ranges (Gulf of Mexico region)
        map_df = map_df[
            (map_df[lat_col].between(24, 31)) &
            (map_df[lon_col].between(-98, -80))
            ]

        if map_df.empty:
            st.warning("⚠️ No valid coordinates found in the Gulf region.")
            st.info("Valid coordinates: Latitude 24-31°N, Longitude -98 to -80°W")
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

        # Create map with light theme
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
                        width: 220px; background-color: white; 
                        border:2px solid grey; z-index:9999; 
                        padding: 10px; border-radius: 5px;
                        box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                <p style="font-weight: bold; margin-bottom: 10px; 
                          border-bottom: 1px solid #ccc; padding-bottom: 5px;">
                    Species Legend
                </p>
            '''
            for species in list(unique_species)[:10]:
                color = species_colors[species]
                legend_html += f'<p style="margin: 3px 0;"><span style="color: {color}; font-size: 18px;">●</span> {species}</p>'

            if len(unique_species) > 10:
                legend_html += f'<p style="margin: 3px 0; font-style: italic; color: #666;">+ {len(unique_species) - 10} more...</p>'

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
            # Display message with a spinner icon or similar
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
# SESSION STATE INITIALIZATION
# ============================================================================

if "messages" not in st.session_state:
    st.session_state.messages = []

if "query_history" not in st.session_state:
    st.session_state.query_history = []

if "chatbot" not in st.session_state:
    try:
        st.session_state.chatbot = SQLChatbot()
    except Exception as e:
        st.error(f"Failed to initialize chatbot: {e}")
        st.info("Make sure the database file exists and SQLChatbot is properly configured.")
        st.stop()

# ============================================================================
# SIDEBAR
# ============================================================================

with st.sidebar:
    st.markdown("### NestScope")
    st.caption("AI-Powered Analytics for Louisiana Coastal Bird Data")
    st.markdown("---")

    st.markdown("#### QUICK PROMPTS")
    st.caption("Try these conversation starters:")

    examples = [
        ("Trends", "Show brown pelican trends from 2015 to 2021"),
        ("Top Species", "What were the top 5 species in 2020?"),
        ("Locations", "Show all bird colonies in Louisiana with their locations"),
        ("Counts", "How many observations were recorded per year?"),
        ("Habitats", "Compare species diversity across different colonies")
    ]

    for label, full_prompt in examples:
        if st.button(label, key=label, use_container_width=True):
            st.session_state.current_question = full_prompt
            st.rerun()

    st.markdown("---")

    if st.session_state.query_history:
        st.markdown("#### HISTORY")
        st.markdown("**Session History**")
        # Show last 10 queries, newest first
        for i, (q_label, q_prompt) in enumerate(reversed(st.session_state.query_history[-10:])):
            # Create a label that is truncated if too long
            display_label = (q_label[:25] + '..') if len(q_label) > 27 else q_label
            if st.button(f"🕒 {display_label}", key=f"hist_{i}", use_container_width=True, help=q_prompt):
                st.session_state.current_question = q_prompt
                st.rerun()

    if st.session_state.query_history:
        if st.button("🗑️ Clear History", use_container_width=True):
            st.session_state.query_history = []
            st.rerun()

    st.markdown("---")

    st.markdown("#### DATA SOURCE")
    st.info(
        "**NOAA DIVER Database**\n\n"
        "Deepwater Horizon Avian Monitoring\n\n"
        "📅 2010-2021 | 📍 Louisiana Coast"
    )

# ============================================================================
# MAIN INTERFACE
# ============================================================================

st.title("NestScope: Coastal Avian Monitoring")

# Welcome Card
if not st.session_state.messages:
    st.markdown("""
        <div class="title-card">
            <h3>Welcome</h3>
            <p>
                This intelligent assistant allows you to query <b>10+ years of bird survey data</b> 
                using natural language. Simply ask a question below to analyze population trends, 
                species distribution, and colony health across Louisiana's coastal habitats.
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

        if "chart_type" in message and "dataframe" in message:
            render_chart(message["dataframe"], message["chart_type"])

# ============================================================================
# USER INPUT HANDLING
# ============================================================================

placeholder_examples = [
    "Show brown pelican trends from 2015 to 2021",
    "What were the top 5 species in 2020?",
    "List all bird colonies in Louisiana with locations",
    "How many observations were recorded per year?",
    "Compare species diversity across different colonies",
    "Which habitat had the most bird sightings?",
    "Where are the Chandeleur Islands colonies?",
    "Map brown pelican nests in Louisiana"
]

if "chat_placeholder" not in st.session_state:
    st.session_state.chat_placeholder = f'Try "{random.choice(placeholder_examples)}"'


prompt = st.chat_input(st.session_state.chat_placeholder) or st.session_state.get("current_question")

if prompt:
    if "current_question" in st.session_state:
        st.session_state.pop("current_question")

    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        try:
            loading_placeholder = st.empty()
            loading_messages = [
                "Hatching data...",
                "Scanning observation records...",
                "Migrating results to you...",
                "Flocking together insights...",
                "Pecking at the database...",
                "Flying through 10 years of data..."
            ]

            with LoadingCarousel(loading_placeholder, loading_messages):
                # Use the new structured API
                response = st.session_state.chatbot.query(prompt)

            if not response['success']:
                error_msg = response['error']
                st.error(error_msg)
                st.session_state.messages.append({"role": "assistant", "content": error_msg})
                st.stop()

            # Extract response components
            sql_query = response['sql']
            answer = response['answer']
            results = response['results']

            # SAVE TO HISTORY (Success only)
            if prompt and prompt not in [h[1] for h in st.session_state.query_history]:
                st.session_state.query_history.append((prompt, prompt))

            # Convert results back to DataFrame for visualization
            df = pd.DataFrame(results) if results else pd.DataFrame()

            with st.expander("🔍 View Generated SQL Query"):
                st.code(sql_query, language="sql")

            # Always show the AI's answer (it will explain if no results were found)
            st.markdown(answer)

            # If there are no results, stop here and don't try to show tables/charts
            if df.empty:
                st.info("This query returned no matching records.")
                st.session_state.messages.append({"role": "assistant", "content": answer})
                st.stop()

            response_data = {
                "role": "assistant",
                "content": answer,
                "dataframe": df
            }

            # Smart Visualization Logic
            # CRITICAL: Prevent charting coordinate data
            cols_lower = [str(col).lower() for col in df.columns]
            has_lat = any('lat' in col for col in cols_lower)
            has_lon = any('lon' in col or 'lng' in col for col in cols_lower)

            if has_lat and has_lon:
                # This is geographic data - don't try to chart it
                chart_type = None
            else:
                chart_type = detect_chart_type(df)

            # Check for map data with multiple fallbacks
            lat_col = next((col for col in df.columns if 'lat' in str(col).lower()), None)
            lon_col = next((col for col in df.columns if 'lon' in str(col).lower() or 'lng' in str(col).lower()), None)

            # Explicit check for exact column names
            if lat_col is None and 'Latitude' in df.columns:
                lat_col = 'Latitude'
            if lon_col is None and 'Longitude' in df.columns:
                lon_col = 'Longitude'

            has_map_data = lat_col is not None and lon_col is not None
            if 'Latitude' in df.columns and 'Longitude' in df.columns:
                has_map_data = True
                lat_col = 'Latitude'
                lon_col = 'Longitude'

            # 🔍 Debug output (you can remove this later)
            print(f"🗺️ Map Detection Debug:")
            # 🔍 Debug output (you can remove this later)
            print(f"🗺️ Map Detection Debug:")
            print(f"  - Columns: {df.columns.tolist()}")
            print(f"  - lat_col: {lat_col}")
            print(f"  - lon_col: {lon_col}")
            print(f"  - has_map_data: {has_map_data}")
            print(f"  - chart_type: {chart_type}")

            # Show inline map for single-location queries
            if not df.empty and len(df) == 1 and has_map_data:
                st.markdown("---")
                st.markdown("### 📍 Location Map")
                render_map(df)
                st.markdown("---")

            if chart_type or has_map_data:
                # If we have a chart OR map, show the Tabs UI
                tab_labels = []

                # ALWAYS show data table first
                if chart_type:
                    tab_labels.append("📊 Data & Charts")
                else:
                    tab_labels.append("📋 Data Table")

                # Add map tab if coordinates exist (and not single location)
                if has_map_data and len(df) > 1:
                    tab_labels.append("🗺️ Map View")
                    print(f"✅ Adding Map View tab (found {lat_col} and {lon_col})")

                tabs = st.tabs(tab_labels)

                # Render First Tab (Data/Chart)
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

                # Render Second Tab (Map) - only if it exists and multiple locations
                if has_map_data and len(tabs) > 1 and len(df) > 1:
                    with tabs[1]:
                        st.markdown("### 🗺️ Map Locations")
                        st.caption(f"Click to view each location on Google Maps")

                        for idx, row in df.iterrows():
                            lat = row[lat_col]
                            lon = row[lon_col]
                            name = row.get('ColonyName', f'Location {idx + 1}')

                            maps_link = f"https://www.google.com/maps?q={lat},{lon}"
                            st.markdown(f"📍 **{name}** - [View on Map]({maps_link})")


            else:
                # No charts, no map - just simple data
                # Show in expander to keep UI clean for text-based answers
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
            # st.rerun()

        except Exception as e:
            st.error(f"An unexpected error occurred: {str(e)}")
            st.info("Try rephrasing your question or contact support if the issue persists.")