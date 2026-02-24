"""
NestScope - Main Application Entry Point
Avian Monitoring Analytics Platform
"""

import streamlit as st
from styles import get_custom_css
from components import render_sidebar_section, render_service_status_link
from services import get_backend_config

# Page configuration
st.set_page_config(
    page_title="NestScope",
    page_icon="🦅",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Hide Streamlit's default page navigation
st.markdown("""
<style>
    /* Hide Streamlit's page navigation */
    [data-testid="stSidebarNav"] {
        display: none;
    }

    /* Fixed header */
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

# Set page name for top bar
if 'page_name' not in st.session_state:
    st.session_state.page_name = "Home"

# Apply custom styling
st.markdown(get_custom_css(), unsafe_allow_html=True)

# Fixed header
st.markdown("""
    <div class="fixed-header">
        <span style="font-size: 1.5rem;">🦅</span>
        <span style="font-size: 1rem; font-weight: 600; color: #E5E5E5;">NestScope</span>
        <span style="color: #666; font-size: 0.875rem;">Avian Monitoring Suite</span>
    </div>
""", unsafe_allow_html=True)

# Render sidebar with Google Cloud-like organization
with st.sidebar:
    # Navigation section
    render_sidebar_section("Navigation")

    if st.button("🏠 Home", use_container_width=True, help="Return to home page", type="primary"):
        st.rerun()

    if st.button("💬 NestChat", use_container_width=True, help="Natural language data queries"):
        st.switch_page("pages/01_nest_chat.py")

    if st.button("🦅 NestVision", use_container_width=True, help="AI bird detection & counting"):
        st.switch_page("pages/02_nest_vision.py")

    if st.button("🗄️ NestDB", use_container_width=True, help="Database management interface"):
        st.switch_page("pages/04_db_editor.py")

    # Tools section
    render_sidebar_section("Tools")

    # Nestperts link using st.link_button
    st.link_button("🧑‍🔬 Nestperts", "http://localhost:5000", use_container_width=True, help="Expert species training platform")

    # System Status section
    render_sidebar_section("System Status")
    render_service_status_link()

# Main content wrapper
st.markdown('<div class="main-content">', unsafe_allow_html=True)

# Main landing page - Google Cloud style
st.markdown("""
    <div style="margin: 0 0 2.5rem 0;">
        <div style="display: flex; align-items: center; margin-bottom: 0.75rem;">
            <h1 style="
                color: #E5E5E5;
                font-size: 2.5rem;
                font-weight: 600;
                margin: 0;
                letter-spacing: -0.03em;
            ">Welcome to NestScope</h1>
        </div>
        <p style="
            color: #A0A0A0;
            font-size: 1rem;
            margin: 0;
            line-height: 1.6;
        ">AI-powered Gulf Coast avian monitoring and analytics platform</p>
    </div>
""", unsafe_allow_html=True)

# Overview card
st.markdown("""
<div style="
    background: linear-gradient(135deg, rgba(217, 119, 87, 0.08) 0%, rgba(217, 119, 87, 0.02) 100%);
    border: 1px solid rgba(217, 119, 87, 0.2);
    border-radius: 12px;
    padding: 2rem;
    margin-bottom: 2.5rem;
">
    <p style="color: #E5E5E5; font-size: 1rem; line-height: 1.7; margin: 0;">
        Explore Gulf Coast bird colony data from 2010-2021 using natural language queries and AI-powered computer vision.
        Ask questions, visualize trends, and detect birds in aerial imagery.
    </p>
</div>
""", unsafe_allow_html=True)

# Feature cards with Google Cloud style
st.markdown("""
    <div style="
        font-size: 0.6875rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: #A0A0A0;
        margin-bottom: 1rem;
    ">Features</div>
""", unsafe_allow_html=True)

col1, col2 = st.columns(2, gap="large")

# Fetch model configuration
try:
    backend_config = get_backend_config()
    model_name = backend_config.get("model", {}).get("name", "minimax/minimax-m2.5")
except Exception:
    model_name = "minimax/minimax-m2.5"

with col1:
    st.markdown(f"""
    <div style="
        background: #2D2D2D;
        border: 1px solid #404040;
        border-radius: 12px;
        padding: 1.75rem;
        height: 100%;
        transition: all 0.2s ease;
    " onmouseover="this.style.borderColor='#D97757'; this.style.background='#333';" onmouseout="this.style.borderColor='#404040'; this.style.background='#2D2D2D';">
        <div style="
            display: inline-block;
            background: rgba(217, 119, 87, 0.15);
            border-radius: 8px;
            padding: 0.5rem 0.75rem;
            margin-bottom: 1rem;
        ">
            <span style="font-size: 1.5rem;">💬</span>
        </div>
        <h3 style="color: #E5E5E5; margin: 0 0 0.75rem 0; font-size: 1.25rem; font-weight: 600;">NestChat</h3>
        <p style="color: #A0A0A0; font-size: 0.875rem; line-height: 1.6; margin-bottom: 1.25rem;">
            Natural language interface for querying bird survey data with intelligent visualizations and PDF report generation
        </p>
        <ul style="color: #E5E5E5; font-size: 0.875rem; line-height: 1.8; margin-left: 1.25rem; padding-left: 0;">
            <li>Ask questions in plain English</li>
            <li>Instant visualizations and insights</li>
            <li>Interactive maps and charts</li>
            <li>Generate professional PDF analysis reports</li>
        </ul>
        <div style="margin-top: 1rem; padding-top: 1rem; border-top: 1px solid #404040;">
            <p style="font-size: 0.75rem; color: #888; margin: 0;">
                ⚡ Powered by <code style="background: #1E1E1E; padding: 2px 6px; border-radius: 3px; color: #D97757;">{model_name}</code>
            </p>
        </div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown("""
    <div style="
        background: #2D2D2D;
        border: 1px solid #404040;
        border-radius: 12px;
        padding: 1.75rem;
        height: 100%;
        transition: all 0.2s ease;
    " onmouseover="this.style.borderColor='#D97757'; this.style.background='#333';" onmouseout="this.style.borderColor='#404040'; this.style.background='#2D2D2D';">
        <div style="
            display: inline-block;
            background: rgba(217, 119, 87, 0.15);
            border-radius: 8px;
            padding: 0.5rem 0.75rem;
            margin-bottom: 1rem;
        ">
            <span style="font-size: 1.5rem;">🦅</span>
        </div>
        <h3 style="color: #E5E5E5; margin: 0 0 0.75rem 0; font-size: 1.25rem; font-weight: 600;">NestVision</h3>
        <p style="color: #A0A0A0; font-size: 0.875rem; line-height: 1.6; margin-bottom: 1.25rem;">
            AI-powered computer vision for bird detection and counting in colony images
        </p>
        <ul style="color: #E5E5E5; font-size: 0.875rem; line-height: 1.8; margin-left: 1.25rem; padding-left: 0;">
            <li>Upload colony images</li>
            <li>Automatic bird detection</li>
            <li>Export annotated results</li>
            <li>Manual correction tools</li>
        </ul>
        <div style="margin-top: 1rem; padding-top: 1rem; border-top: 1px solid #404040;">
            <p style="font-size: 0.75rem; color: #888; margin: 0;">
                ⚡ Powered by <code style="background: #1E1E1E; padding: 2px 6px; border-radius: 3px; color: #D97757;">YOLOv8 (ONNX)</code>
            </p>
        </div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<div style='height: 2rem;'></div>", unsafe_allow_html=True)

# Third feature card for NestDB
col3, col4 = st.columns(2, gap="large")

with col3:
    st.markdown("""
    <div style="
        background: #2D2D2D;
        border: 1px solid #404040;
        border-radius: 12px;
        padding: 1.75rem;
        height: 100%;
        transition: all 0.2s ease;
    " onmouseover="this.style.borderColor='#D97757'; this.style.background='#333';" onmouseout="this.style.borderColor='#404040'; this.style.background='#2D2D2D';">
        <div style="
            display: inline-block;
            background: rgba(217, 119, 87, 0.15);
            border-radius: 8px;
            padding: 0.5rem 0.75rem;
            margin-bottom: 1rem;
        ">
            <span style="font-size: 1.5rem;">🗄️</span>
        </div>
        <h3 style="color: #E5E5E5; margin: 0 0 0.75rem 0; font-size: 1.25rem; font-weight: 600;">NestDB</h3>
        <p style="color: #A0A0A0; font-size: 0.875rem; line-height: 1.6; margin-bottom: 1.25rem;">
            Database management interface for viewing and editing survey data tables
        </p>
        <ul style="color: #E5E5E5; font-size: 0.875rem; line-height: 1.8; margin-left: 1.25rem; padding-left: 0;">
            <li>Browse all database tables</li>
            <li>View and edit records</li>
            <li>Search and filter data</li>
            <li>Export to CSV</li>
        </ul>
        <div style="margin-top: 1rem; padding-top: 1rem; border-top: 1px solid #404040;">
            <p style="font-size: 0.75rem; color: #888; margin: 0;">
                ⚡ Direct database access
            </p>
        </div>
    </div>
    """, unsafe_allow_html=True)

with col4:
    st.markdown("""
    <div style="
        background: #2D2D2D;
        border: 1px solid #404040;
        border-radius: 12px;
        padding: 1.75rem;
        height: 100%;
        transition: all 0.2s ease;
    " onmouseover="this.style.borderColor='#D97757'; this.style.background='#333';" onmouseout="this.style.borderColor='#404040'; this.style.background='#2D2D2D';">
        <div style="
            display: inline-block;
            background: rgba(217, 119, 87, 0.15);
            border-radius: 8px;
            padding: 0.5rem 0.75rem;
            margin-bottom: 1rem;
        ">
            <span style="font-size: 1.5rem;">🧑‍🔬</span>
        </div>
        <h3 style="color: #E5E5E5; margin: 0 0 0.75rem 0; font-size: 1.25rem; font-weight: 600;">Nestperts</h3>
        <p style="color: #A0A0A0; font-size: 0.875rem; line-height: 1.6; margin-bottom: 1.25rem;">
            Expert species training and annotation platform for creating labeled datasets
        </p>
        <ul style="color: #E5E5E5; font-size: 0.875rem; line-height: 1.8; margin-left: 1.25rem; padding-left: 0;">
            <li>MobileSAM segmentation</li>
            <li>Species identification</li>
            <li>Multi-expert workflow</li>
            <li>Training data generation</li>
        </ul>
        <div style="margin-top: 1rem; padding-top: 1rem; border-top: 1px solid #404040;">
            <p style="font-size: 0.75rem; color: #888; margin: 0;">
                ⚡ Flask app on port 5000
            </p>
        </div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<div style='height: 2rem;'></div>", unsafe_allow_html=True)

# Dataset metrics - Google Cloud style
st.markdown("""
    <div style="
        font-size: 0.6875rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: #A0A0A0;
        margin-bottom: 1rem;
    ">Dataset Overview</div>
""", unsafe_allow_html=True)

metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
with metric_col1:
    st.metric("Years", "2010-2021")
with metric_col2:
    st.metric("States", "5")
with metric_col3:
    st.metric("Species", "20+")
with metric_col4:
    st.metric("Observations", "100K+")

st.markdown("<div style='height: 2rem;'></div>", unsafe_allow_html=True)

# Quick start guide - cleaner format
st.markdown("""
    <div style="
        font-size: 0.6875rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: #A0A0A0;
        margin-bottom: 1rem;
    ">Getting Started</div>
""", unsafe_allow_html=True)

st.markdown("""
<div style="background: #2D2D2D; border: 1px solid #404040; border-radius: 12px; padding: 1.5rem;">
    <ol style="color: #E5E5E5; font-size: 0.875rem; line-height: 2; margin: 0; padding-left: 1.5rem;">
        <li><strong style="color: #D97757;">NestChat:</strong> Ask questions about bird populations, trends, and locations</li>
        <li><strong style="color: #D97757;">NestVision:</strong> Upload images for automatic bird detection and counting</li>
        <li><strong style="color: #D97757;">Export:</strong> Download results as CSV files or annotated images</li>
    </ol>
</div>
""", unsafe_allow_html=True)
