import streamlit as st
import pandas as pd
import plotly.express as px
import folium
from streamlit_folium import st_folium
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
    page_title="Louisiana Coastal Bird Copilot",
    page_icon="🦅",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================================
# PROFESSIONAL DARK THEME CSS
# ============================================================================

st.markdown("""
<style>
    /* Import Modern Font */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    /* ===== DARK THEME GLOBAL SETTINGS ===== */
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    
    /* Dark Background */
    .stApp {
        background: linear-gradient(135deg, #0f0f23 0%, #1a1a2e 100%);
    }
    
    /* Headers - Bright and Readable */
    h1, h2, h3, h4 {
        color: #ffffff !important;
        font-weight: 600 !important;
        letter-spacing: -0.3px;
    }
    
    h1 {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        font-size: 2.5rem !important;
    }


    /* ===== SIDEBAR DARK STYLING ===== */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0d0d1f 0%, #0a0a18 100%);
        border-right: 1px solid rgba(102, 126, 234, 0.2);
        box-shadow: 2px 0 20px rgba(0, 0, 0, 0.5);
    }
    
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3,
    [data-testid="stSidebar"] h4,
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] .stMarkdown,
    [data-testid="stSidebar"] .stCaption,
    [data-testid="stSidebar"] label {
        color: #e0e0e0 !important;
    }
    
    /* Sidebar section headers */
    [data-testid="stSidebar"] h4 {
        color: #8b9dc3 !important;
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        margin-top: 2rem;
        margin-bottom: 0.5rem;
        font-weight: 700;
    }
    
    [data-testid="stSidebar"] h3 {
        color: #ffffff !important;
        font-size: 1.3rem;
        font-weight: 700;
    }

    /* ===== PROFESSIONAL BUTTON STYLING ===== */
    .stButton button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 8px;
        padding: 0.65rem 1rem;
        font-weight: 600;
        font-size: 0.9rem;
        border: none;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
        width: 100%;
        height: 44px;
        display: flex;
        align-items: center;
        justify-content: center;
    }
    
    /* Hover effect */
    .stButton button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(102, 126, 234, 0.5);
        background: linear-gradient(135deg, #764ba2 0%, #667eea 100%);
    }
    
    /* Active/Click effect */
    .stButton button:active {
        transform: translateY(0px);
        box-shadow: 0 2px 8px rgba(102, 126, 234, 0.4);
    }
    
    /* Focus state */
    .stButton button:focus {
        outline: 2px solid rgba(102, 126, 234, 0.5);
        outline-offset: 2px;
    }

    /* ===== CHAT INPUT - FIXED WHITE OVERLAY ===== */
    [data-testid="stChatInput"] {
        background-color: transparent !important;
        border: none !important;
    }
    
    [data-testid="stChatInput"] > div {
        background-color: rgba(22, 22, 42, 0.95) !important;
        border: 1px solid rgba(102, 126, 234, 0.3) !important;
        border-radius: 12px !important;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4) !important;
    }
    
    [data-testid="stChatInput"] textarea {
        background-color: transparent !important;
        color: #ffffff !important;
        border: none !important;
        font-size: 0.95rem !important;
        padding: 0.75rem !important;
    }
    
    [data-testid="stChatInput"] textarea::placeholder {
        color: #8b9dc3 !important;
        opacity: 0.7;
    }
    
    [data-testid="stChatInput"] textarea:focus {
        outline: none !important;
        box-shadow: none !important;
    }
    
    /* Send button in chat input */
    [data-testid="stChatInput"] button {
        background-color: #667eea !important;
        color: white !important;
        border-radius: 8px !important;
        transition: all 0.2s ease !important;
    }
    
    [data-testid="stChatInput"] button:hover {
        background-color: #764ba2 !important;
    }

    /* ===== CHAT MESSAGES DARK THEME ===== */
    .stChatMessage {
        background-color: transparent;
        border: none;
    }
    
    /* Assistant Messages */
    [data-testid="stChatMessageContent"] {
        background: linear-gradient(135deg, rgba(18, 18, 36, 0.95) 0%, rgba(22, 33, 62, 0.95) 100%);
        border-radius: 12px;
        padding: 1.5rem;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3);
        border: 1px solid rgba(102, 126, 234, 0.15);
        color: #e0e0e0;
    }

    /* User Messages */
    [data-testid="stChatMessage"]:has([data-testid="stChatMessageContent"]:first-child) [data-testid="stChatMessageContent"] {
        background: linear-gradient(135deg, rgba(102, 126, 234, 0.15) 0%, rgba(118, 75, 162, 0.15) 100%);
        border: 1px solid rgba(102, 126, 234, 0.4);
        color: #ffffff;
    }

    /* Text readability */
    p, .stMarkdown, .stCaption, label {
        color: #b0b0b0;
    }
    
    /* Make all markdown text readable */
    .stMarkdown p, .stMarkdown li {
        color: #d0d0d0 !important;
    }
    
    /* Strong/bold text */
    strong, b {
        color: #ffffff !important;
    }

    /* ===== TITLE CARD ===== */
    .title-card {
        background: linear-gradient(135deg, rgba(18, 18, 36, 0.9) 0%, rgba(22, 33, 62, 0.9) 100%);
        padding: 2rem;
        border-radius: 12px;
        border: 1px solid rgba(102, 126, 234, 0.2);
        margin-bottom: 2rem;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
    }
    
    .title-card h3 {
        color: #8b9dc3 !important;
        margin-top: 0;
        font-size: 1.1rem;
        text-transform: uppercase;
        letter-spacing: 1px;
        font-weight: 700;
    }
    
    .title-card p {
        color: #c0c0c0 !important;
        font-size: 1rem;
        line-height: 1.6;
    }

    /* ===== INPUT FIELDS DARK ===== */
    .stTextInput input, 
    .stTextArea textarea {
        background-color: rgba(22, 22, 42, 0.8) !important;
        color: #ffffff !important;
        border: 1px solid rgba(102, 126, 234, 0.3) !important;
        border-radius: 8px !important;
    }
    
    .stTextInput input:focus,
    .stTextArea textarea:focus {
        border-color: #667eea !important;
        box-shadow: 0 0 0 2px rgba(102, 126, 234, 0.2) !important;
    }

    /* ===== DATAFRAME DARK STYLING ===== */
    [data-testid="stDataFrame"] {
        background-color: rgba(18, 18, 36, 0.8);
        border-radius: 8px;
        border: 1px solid rgba(102, 126, 234, 0.2);
    }
    
    [data-testid="stDataFrame"] thead tr th {
        background-color: rgba(102, 126, 234, 0.2) !important;
        color: #ffffff !important;
        font-weight: 600;
    }

    /* ===== EXPANDER DARK STYLING ===== */
    .streamlit-expanderHeader {
        background: rgba(102, 126, 234, 0.1);
        border-radius: 8px;
        border: 1px solid rgba(102, 126, 234, 0.3);
        color: #e0e0e0 !important;
        font-weight: 500;
    }
    
    .streamlit-expanderHeader:hover {
        background: rgba(102, 126, 234, 0.2);
        border-color: #667eea;
    }
    
    .streamlit-expanderContent {
        background-color: rgba(18, 18, 36, 0.5);
        border: 1px solid rgba(102, 126, 234, 0.2);
        border-top: none;
        border-radius: 0 0 8px 8px;
    }

    /* ===== TAB STYLING ===== */
    .stTabs [data-baseweb="tab-list"] {
        gap: 4px;
        background-color: rgba(18, 18, 36, 0.5);
        padding: 6px;
        border-radius: 8px;
    }
    
    .stTabs [data-baseweb="tab"] {
        background-color: transparent;
        border-radius: 6px;
        color: #8b9dc3;
        font-weight: 600;
        padding: 10px 20px;
        transition: all 0.3s ease;
        font-size: 0.9rem;
    }
    
    .stTabs [data-baseweb="tab"]:hover {
        background-color: rgba(102, 126, 234, 0.15);
        color: #ffffff;
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
        color: white !important;
    }

    /* ===== DOWNLOAD BUTTON ===== */
    .stDownloadButton button {
        background: linear-gradient(135deg, #43a047 0%, #66bb6a 100%);
        color: white;
        border-radius: 8px;
        padding: 0.65rem 1rem;
        font-weight: 600;
        font-size: 0.9rem;
        border: none;
        transition: all 0.3s ease;
        box-shadow: 0 4px 12px rgba(67, 160, 71, 0.3);
        height: 44px;
    }
    
    .stDownloadButton button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(67, 160, 71, 0.5);
    }

    /* ===== ALERTS ===== */
    .stAlert {
        border-radius: 8px;
        border-left: 4px solid;
        background-color: rgba(18, 18, 36, 0.9) !important;
    }
    
    [data-baseweb="notification"] {
        background-color: rgba(18, 18, 36, 0.95) !important;
        border: 1px solid rgba(102, 126, 234, 0.3);
    }

    /* ===== SPINNER ===== */
    .stSpinner > div {
        border-top-color: #667eea !important;
    }

    /* ===== HIDE STREAMLIT BRANDING - MODIFIED ===== */
    /* Hide specific elements instead of global hiding */
    #MainMenu {
        display: none !important;
    }
    
    footer {
        display: none !important;
    }
    
    .viewerBadge_container__1QSob {
        display: none !important;
    }
    
    /* Ensure Toolbar/Header IS visible for sidebar toggle */
    [data-testid="stToolbar"] {
        display: block !important;
        visibility: visible !important;
        background-color: transparent !important;
        height: 0px; /* Don't take up space */
    }
    
    /* Ensure the sidebar toggle is visible and large - CENTERED LEFT */
    [data-testid="stSidebarCollapsedControl"] {
        display: block !important;
        visibility: visible !important;
        color: #ffffff !important;
        background-color: #667eea !important;
        border-radius: 0 50% 50% 0; /* Half circle on edge */
        width: 60px !important;
        height: 80px !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        box-shadow: 2px 0 12px rgba(102, 126, 234, 0.5);
        z-index: 1000005 !important;
        position: fixed !important;
        top: 50vh;
        left: 0;
        transform: translateY(-50%);
        transition: all 0.3s ease;
    }
    
    [data-testid="stSidebarCollapsedControl"]:hover {
        background-color: #764ba2 !important;
        width: 70px !important;
        padding-left: 10px;
        box-shadow: 4px 0 16px rgba(102, 126, 234, 0.7);
    }
    
    /* Ensure the icon inside is visible and scalled */
    [data-testid="stSidebarCollapsedControl"] svg {
        fill: white !important;
        stroke: white !important;
        width: 30px !important;
        height: 30px !important;
    }

    /* ===== CUSTOM SCROLLBAR ===== */
    ::-webkit-scrollbar {
        width: 10px;
        height: 10px;
    }
    
    ::-webkit-scrollbar-track {
        background: rgba(18, 18, 36, 0.5);
        border-radius: 10px;
    }
    
    ::-webkit-scrollbar-thumb {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 10px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: linear-gradient(135deg, #764ba2 0%, #667eea 100%);
    }
    
    /* ===== LINK BUTTON ===== */
    .stLinkButton a {
        background: linear-gradient(135deg, rgba(102, 126, 234, 0.2) 0%, rgba(118, 75, 162, 0.2) 100%);
        color: #ffffff !important;
        border: 1px solid rgba(102, 126, 234, 0.4);
        border-radius: 8px;
        padding: 0.65rem 1rem;
        font-weight: 600;
        font-size: 0.9rem;
        text-decoration: none;
        transition: all 0.3s ease;
        display: flex;
        align-items: center;
        justify-content: center;
        height: 44px;
        box-shadow: 0 2px 8px rgba(102, 126, 234, 0.2);
    }
    
    .stLinkButton a:hover {
        background: linear-gradient(135deg, rgba(102, 126, 234, 0.3) 0%, rgba(118, 75, 162, 0.3) 100%);
        border-color: #667eea;
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
    }
    
    /* Code blocks */
    code {
        background-color: rgba(18, 18, 36, 0.8) !important;
        color: #e0e0e0 !important;
        border: 1px solid rgba(102, 126, 234, 0.2);
    }
    
    pre {
        background-color: rgba(18, 18, 36, 0.8) !important;
        border: 1px solid rgba(102, 126, 234, 0.2);
    }
[data-testid="stChatInput"] textarea {
    background-color: #0f0f23 !important;
    color: #ffffff !important;
    caret-color: #ffffff !important;
}

[data-testid="stChatInput"] textarea::placeholder {
    color: #9aa4c7 !important;
}
            [data-testid="stBottom"] {
    background: transparent !important;
}

[data-testid="stBottom"] > div {
    background: transparent !important;
}
</style>
""", unsafe_allow_html=True)

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def render_chart(df, chart_type):
    """
    Render a chart with dark theme colors.
    """
    if len(df.columns) < 2:
        return
    
    x_col, y_col = df.columns[0], df.columns[1]
    
    # Dark theme template for plotly
    template = {
        'layout': {
            'paper_bgcolor': 'rgba(18, 18, 36, 0.8)',
            'plot_bgcolor': 'rgba(22, 33, 62, 0.8)',
            'font': {'color': '#e0e0e0', 'family': 'Inter'},
            'xaxis': {'gridcolor': 'rgba(102, 126, 234, 0.1)', 'linecolor': 'rgba(102, 126, 234, 0.3)'},
            'yaxis': {'gridcolor': 'rgba(102, 126, 234, 0.1)', 'linecolor': 'rgba(102, 126, 234, 0.3)'},
            'title': {'font': {'size': 18, 'color': '#ffffff'}}
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
        fig.update_traces(line_color='#667eea', line_width=3)
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
        fig.update_traces(marker_color='#667eea')
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
    
    # Don't chart if the Y-axis column looks like a dimension (Year, ID, etc.) rather than a metric
    dimension_keywords = ['year', 'month', 'day', 'date', 'id', 'latitude', 'longitude', 'lat', 'lon']
    if any(keyword == y_col.lower() for keyword in dimension_keywords):
        return None
    
    temporal_keywords = ['year', 'date', 'time', 'month', 'day', 'season']
    if any(keyword in x_col.lower() for keyword in temporal_keywords):
        return 'line'
    
    if pd.api.types.is_object_dtype(x_dtype) or pd.api.types.is_integer_dtype(x_dtype):
        return 'bar'
    
    return None


def render_map(df):
    """
    Render a Folium map with dark tiles.
    """
    lat_col = next((col for col in df.columns if 'lat' in col.lower()), None)
    lon_col = next((col for col in df.columns if 'lon' in col.lower() or 'lng' in col.lower()), None)
    
    if not lat_col or not lon_col:
        st.info("No geographic coordinates found in results.")
        return
    
    try:
        map_df = df.dropna(subset=[lat_col, lon_col])
        map_df = map_df[
            (map_df[lat_col].between(-90, 90)) & 
            (map_df[lon_col].between(-180, 180))
        ]
        
        if map_df.empty:
            st.warning("No valid geographic coordinates found.")
            return
        
        avg_lat = map_df[lat_col].mean()
        avg_lon = map_df[lon_col].mean()
        
        m = folium.Map(
            location=[avg_lat, avg_lon], 
            zoom_start=7,
            tiles='CartoDB dark_matter'
        )
        
        for idx, row in map_df.iterrows():
            tooltip_lines = [
                f"<b>{col}:</b> {row[col]}" 
                for col in df.columns 
                if col not in [lat_col, lon_col]
            ]
            tooltip_text = "<br>".join(tooltip_lines)
            
            folium.Marker(
                location=[row[lat_col], row[lon_col]],
                tooltip=tooltip_text,
                icon=folium.Icon(color='purple', icon='info-sign')
            ).add_to(m)
        
        st_folium(m, width=800, height=500)
        st.caption(f"Showing {len(map_df)} locations")
        
    except Exception as e:
        st.warning(f"Could not generate map: {str(e)}")


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
    st.markdown("### Bird Copilot")
    st.caption("AI-Powered Analytics for Louisiana Coastal Bird Data")
    st.markdown("---")
    
    st.markdown("#### QUICK PROMPTS")
    st.caption("Try these conversation starters:")
    
    examples = [
        ("Trends", "Show brown pelican trends from 2015 to 2021"),
        ("Top Species", "What were the top 5 species in 2020?"),
        ("Locations", "List all bird colonies in Louisiana"),
        ("Counts", "How many observations were recorded per year?"),
        ("Habitats", "Compare species diversity across different colonies")
    ]
    
    for label, full_prompt in examples:
        if st.button(label, key=label, use_container_width=True):
            st.session_state.current_question = full_prompt
            st.rerun()

    st.markdown("---")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Reset", use_container_width=True):
            st.session_state.messages = []
            st.session_state.pop('current_question', None)
            st.rerun()
    with col2:
        st.link_button("Help", "https://nexusla.org", use_container_width=True)

    st.markdown("---")
    
    st.markdown("#### DATA SOURCE")
    st.info(
        "**NOAA DIVER Database**\n\n"
        "Deepwater Horizon Avian Monitoring\n\n"
        "2010-2021 | Louisiana Coast"
    )

# ============================================================================
# MAIN INTERFACE
# ============================================================================

st.title("Louisiana Coastal Bird Monitoring Copilot")

# Welcome Card
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
    "List all bird colonies in Louisiana",
    "How many observations were recorded per year?",
    "Compare species diversity across different colonies",
    "Which habitat had the most bird sightings?",
    "Analyze the population growth of Seagulls",
    "Identify colonies with declining populations"
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
            
            # Convert results back to DataFrame for visualization
            df = pd.DataFrame(results) if results else pd.DataFrame()
            
            with st.expander("View Generated SQL Query"):
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
            chart_type = detect_chart_type(df)
            
            # Check for map data
            lat_col = next((col for col in df.columns if 'lat' in col.lower()), None)
            lon_col = next((col for col in df.columns if 'lon' in col.lower() or 'lng' in col.lower()), None)
            has_map_data = lat_col is not None and lon_col is not None
            
            if chart_type or has_map_data:
                # If we have a chart OR map, show the Tabs UI
                tab_labels = []
                if chart_type:
                    tab_labels.append("Data & Charts")
                else:
                    tab_labels.append("Data Table")
                    
                if has_map_data:
                    tab_labels.append("Map View")
                
                tabs = st.tabs(tab_labels)
                
                # Render First Tab (Data/Chart)
                with tabs[0]:
                    st.dataframe(df, use_container_width=True)
                    
                    csv = df.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="Download CSV",
                        data=csv,
                        file_name="bird_data_export.csv",
                        mime="text/csv",
                    )
                    
                    if chart_type:
                        response_data["chart_type"] = chart_type
                        render_chart(df, chart_type)
                
                # Render Second Tab (Map) - only if it exists
                if has_map_data and len(tabs) > 1:
                    with tabs[1]:
                        render_map(df)
                        
            else:
                # No charts, no map - just simple data
                # Show in expander to keep UI clean for text-vased answers
                with st.expander("View Source Data"):
                    st.dataframe(df, use_container_width=True)
                    
                    csv = df.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="Download CSV",
                        data=csv,
                        file_name="bird_data_export.csv",
                        mime="text/csv",
                    )
            
            st.session_state.messages.append(response_data)
            
        except Exception as e:
            st.error(f"An unexpected error occurred: {str(e)}")
            st.info("Try rephrasing your question or contact support if the issue persists.")