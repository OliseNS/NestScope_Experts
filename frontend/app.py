"""
NestScope - Main Application Entry Point
Avian Monitoring Analytics Platform
"""

import streamlit as st
from styles import get_custom_css
from components import render_sidebar_header

# Page configuration
st.set_page_config(
    page_title="NestScope",
    page_icon="🦅",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Apply custom styling
st.markdown(get_custom_css(), unsafe_allow_html=True)

# Render sidebar
with st.sidebar:
    render_sidebar_header()

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
        ">Features</div>
    """, unsafe_allow_html=True)

    if st.button("💬 NestChat", use_container_width=True, help="Natural language queries"):
        st.switch_page("pages/01_nest_chat.py")

    if st.button("🦅 NestVision", use_container_width=True, help="Bird detection & counting"):
        st.switch_page("pages/02_nest_vision.py")

# Main landing page
st.title("NestScope")
st.caption("AI-powered Gulf Coast avian monitoring analytics")

st.markdown("""
<div class="title-card">
    <h3>Welcome to NestScope</h3>
    <p>
        Explore Gulf Coast bird colony data from 2010-2021 using natural language queries and AI-powered computer vision.
        Ask questions, visualize trends, and detect birds in aerial imagery.
    </p>
</div>
""", unsafe_allow_html=True)

# Feature cards with clean styling
st.markdown("### Features")
col1, col2 = st.columns(2, gap="medium")

with col1:
    st.markdown("""
    <div style="background: var(--claude-surface); border: 1px solid var(--claude-border); border-radius: 12px; padding: 1.5rem; height: 100%;">
        <h4 style="color: var(--claude-orange); margin-top: 0; font-size: 1.125rem; font-weight: 600;">💬 NestChat</h4>
        <p style="color: var(--claude-text-light); font-size: 0.875rem; line-height: 1.6; margin-bottom: 1rem;">
            Natural language interface for querying bird survey data
        </p>
        <ul style="color: var(--claude-text); font-size: 0.875rem; line-height: 1.8; margin-left: 1.25rem;">
            <li>Ask questions in plain English</li>
            <li>Instant visualizations and insights</li>
            <li>Interactive maps and charts</li>
            <li>10+ years of survey data</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown("""
    <div style="background: var(--claude-surface); border: 1px solid var(--claude-border); border-radius: 12px; padding: 1.5rem; height: 100%;">
        <h4 style="color: var(--claude-orange); margin-top: 0; font-size: 1.125rem; font-weight: 600;">🦅 NestVision</h4>
        <p style="color: var(--claude-text-light); font-size: 0.875rem; line-height: 1.6; margin-bottom: 1rem;">
            Computer vision for bird detection and counting
        </p>
        <ul style="color: var(--claude-text); font-size: 0.875rem; line-height: 1.8; margin-left: 1.25rem;">
            <li>Upload colony images</li>
            <li>Automatic bird detection</li>
            <li>Export annotated results</li>
            <li>Manual correction tools</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# Dataset info in a compact grid
st.markdown("### Dataset Overview")
metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
with metric_col1:
    st.metric("Years", "2010-2021")
with metric_col2:
    st.metric("States", "5")
with metric_col3:
    st.metric("Species", "20+")
with metric_col4:
    st.metric("Observations", "100K+")

st.markdown("<br>", unsafe_allow_html=True)

# Quick start guide
st.markdown("""
### Getting Started

1. **NestChat**: Ask questions about bird populations, trends, and locations
2. **NestVision**: Upload images for automatic bird detection and counting
3. **Export**: Download results as CSV files or annotated images

Navigate to a feature using the sidebar menu.
""")
