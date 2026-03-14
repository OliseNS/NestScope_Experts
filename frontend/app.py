"""
NestScope - Main Application Entry Point
Avian Monitoring Analytics Platform
"""

import streamlit as st
from components import init_page, render_header, render_sidebar
from services import get_backend_config

# Initialize page with shared layout
init_page(page_title="NestScope", page_icon="🦅", layout="wide")

# Render shared header
render_header()

# Render shared sidebar
with st.sidebar:
    render_sidebar(active_page="home")

# Fetch model configuration
try:
    backend_config = get_backend_config()
    model_name = backend_config.get("model", {}).get("name", "minimax/minimax-m2.5")
except Exception:
    model_name = "minimax/minimax-m2.5"

# ── Hero Section ────────────────────────────────────────────────────────────
st.markdown("""
<div style="padding: 2rem 0 2.5rem 0;">
    <div style="
        display: inline-block;
        background: rgba(217, 119, 87, 0.12);
        border: 1px solid rgba(217, 119, 87, 0.25);
        border-radius: 20px;
        padding: 0.3rem 0.875rem;
        font-size: 0.75rem;
        font-weight: 600;
        color: #D97757;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        margin-bottom: 1rem;
    ">Gulf Coast Avian Monitoring</div>
    <h1 style="
        color: #F0F0F0;
        font-size: 2.75rem;
        font-weight: 700;
        margin: 0 0 0.75rem 0;
        letter-spacing: -0.04em;
        line-height: 1.15;
    ">NestScope</h1>
    <p style="
        color: #888;
        font-size: 1.0625rem;
        margin: 0;
        line-height: 1.6;
        max-width: 540px;
    ">AI-powered platform for querying, visualizing, and analyzing 11 years of Gulf Coast bird colony data.</p>
</div>
""", unsafe_allow_html=True)

# ── Stats strip ─────────────────────────────────────────────────────────────
try:
    from services import get_stats_from_backend
    stats = get_stats_from_backend()
    min_year = stats.get("min_year", 2010)
    max_year = stats.get("max_year", 2021)
    total_colonies = stats.get("total_colonies", 0)
    total_species = stats.get("total_species", 0)
    total_records = stats.get("total_observations", 0)
except Exception:
    min_year, max_year, total_colonies, total_species, total_records = 2010, 2021, 592, 73, 0

metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
with metric_col1:
    st.metric("Years of Data", f"{min_year}–{max_year}")
with metric_col2:
    st.metric("Colonies", f"{total_colonies:,}" if total_colonies else "592")
with metric_col3:
    st.metric("Species", f"{total_species}+" if total_species else "73+")
with metric_col4:
    st.metric("Records", f"{total_records:,}" if total_records else "100K+")

st.markdown("<div style='height: 2.5rem;'></div>", unsafe_allow_html=True)

# ── Section label ────────────────────────────────────────────────────────────
st.markdown("""
<div style="
    font-size: 0.6875rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: #666;
    margin-bottom: 1rem;
">Tools</div>
""", unsafe_allow_html=True)

# ── Feature Cards Row 1 ──────────────────────────────────────────────────────
col1, col2 = st.columns(2, gap="medium")

with col1:
    st.markdown(f"""
    <div class="feature-card">
        <div style="
            display: flex;
            align-items: center;
            gap: 0.75rem;
            margin-bottom: 1.25rem;
        ">
            <div style="
                width: 40px; height: 40px;
                background: linear-gradient(135deg, rgba(217,119,87,0.25), rgba(217,119,87,0.08));
                border: 1px solid rgba(217,119,87,0.3);
                border-radius: 10px;
                display: flex; align-items: center; justify-content: center;
                font-size: 1.25rem; flex-shrink: 0;
            ">💬</div>
            <div>
                <div style="color: #F0F0F0; font-weight: 700; font-size: 1.0625rem; letter-spacing: -0.01em;">NestChat</div>
                <div style="color: #D97757; font-size: 0.75rem; font-weight: 600; letter-spacing: 0.04em; text-transform: uppercase;">Natural Language · SQL</div>
            </div>
        </div>
        <p style="color: #999; font-size: 0.875rem; line-height: 1.65; margin: 0 0 1.25rem 0;">
            Ask questions about bird populations, trends, and locations in plain English — get instant charts, maps, and data.
        </p>
        <div style="border-top: 1px solid rgba(255,255,255,0.08); padding-top: 0.875rem; display: flex; align-items: center; justify-content: space-between;">
            <div style="display: flex; gap: 0.5rem; flex-wrap: wrap;">
                <span style="background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.1); border-radius: 5px; padding: 0.2rem 0.5rem; font-size: 0.7rem; color: #999;">Charts</span>
                <span style="background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.1); border-radius: 5px; padding: 0.2rem 0.5rem; font-size: 0.7rem; color: #999;">Maps</span>
                <span style="background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.1); border-radius: 5px; padding: 0.2rem 0.5rem; font-size: 0.7rem; color: #999;">CSV export</span>
            </div>
            <span style="font-size: 0.7rem; color: #555;">⚡ {model_name.split("/")[-1]}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown("""
    <div class="feature-card">
        <div style="
            display: flex;
            align-items: center;
            gap: 0.75rem;
            margin-bottom: 1.25rem;
        ">
            <div style="
                width: 40px; height: 40px;
                background: linear-gradient(135deg, rgba(217,119,87,0.25), rgba(217,119,87,0.08));
                border: 1px solid rgba(217,119,87,0.3);
                border-radius: 10px;
                display: flex; align-items: center; justify-content: center;
                font-size: 1.25rem; flex-shrink: 0;
            ">🦅</div>
            <div>
                <div style="color: #F0F0F0; font-weight: 700; font-size: 1.0625rem; letter-spacing: -0.01em;">NestVision</div>
                <div style="color: #D97757; font-size: 0.75rem; font-weight: 600; letter-spacing: 0.04em; text-transform: uppercase;">Computer Vision · YOLO</div>
            </div>
        </div>
        <p style="color: #999; font-size: 0.875rem; line-height: 1.65; margin: 0 0 1.25rem 0;">
            Upload colony imagery for automatic bird detection and counting using AI. Supports Swift and Apex detection modes.
        </p>
        <div style="border-top: 1px solid rgba(255,255,255,0.08); padding-top: 0.875rem; display: flex; align-items: center; justify-content: space-between;">
            <div style="display: flex; gap: 0.5rem; flex-wrap: wrap;">
                <span style="background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.1); border-radius: 5px; padding: 0.2rem 0.5rem; font-size: 0.7rem; color: #999;">SAHI slicing</span>
                <span style="background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.1); border-radius: 5px; padding: 0.2rem 0.5rem; font-size: 0.7rem; color: #999;">25 species</span>
                <span style="background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.1); border-radius: 5px; padding: 0.2rem 0.5rem; font-size: 0.7rem; color: #999;">Export</span>
            </div>
            <span style="font-size: 0.7rem; color: #555;">⚡ YOLO26 ONNX</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<div style='height: 1rem;'></div>", unsafe_allow_html=True)

# ── Feature Cards Row 2 ──────────────────────────────────────────────────────
col3, col4 = st.columns(2, gap="medium")

with col3:
    st.markdown("""
    <div class="feature-card">
        <div style="
            display: flex;
            align-items: center;
            gap: 0.75rem;
            margin-bottom: 1.25rem;
        ">
            <div style="
                width: 40px; height: 40px;
                background: linear-gradient(135deg, rgba(100,160,255,0.2), rgba(100,160,255,0.06));
                border: 1px solid rgba(100,160,255,0.25);
                border-radius: 10px;
                display: flex; align-items: center; justify-content: center;
                font-size: 1.25rem; flex-shrink: 0;
            ">🧑‍🔬</div>
            <div>
                <div style="color: #F0F0F0; font-weight: 700; font-size: 1.0625rem; letter-spacing: -0.01em;">Nestperts</div>
                <div style="color: #6AA0FF; font-size: 0.75rem; font-weight: 600; letter-spacing: 0.04em; text-transform: uppercase;">Annotation · Training</div>
            </div>
        </div>
        <p style="color: #999; font-size: 0.875rem; line-height: 1.65; margin: 0 0 1.25rem 0;">
            Expert platform for species identification and annotation. Uses MobileSAM for point-click segmentation and training data generation.
        </p>
        <div style="border-top: 1px solid rgba(255,255,255,0.08); padding-top: 0.875rem; display: flex; align-items: center; justify-content: space-between;">
            <div style="display: flex; gap: 0.5rem; flex-wrap: wrap;">
                <span style="background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.1); border-radius: 5px; padding: 0.2rem 0.5rem; font-size: 0.7rem; color: #999;">MobileSAM</span>
                <span style="background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.1); border-radius: 5px; padding: 0.2rem 0.5rem; font-size: 0.7rem; color: #999;">YOLO labels</span>
            </div>
            <span style="font-size: 0.7rem; color: #555;">⚡ Port 5000</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

with col4:
    st.markdown("""
    <div class="feature-card">
        <div style="
            display: flex;
            align-items: center;
            gap: 0.75rem;
            margin-bottom: 1.25rem;
        ">
            <div style="
                width: 40px; height: 40px;
                background: linear-gradient(135deg, rgba(52,199,89,0.2), rgba(52,199,89,0.06));
                border: 1px solid rgba(52,199,89,0.25);
                border-radius: 10px;
                display: flex; align-items: center; justify-content: center;
                font-size: 1.25rem; flex-shrink: 0;
            ">🗄️</div>
            <div>
                <div style="color: #F0F0F0; font-weight: 700; font-size: 1.0625rem; letter-spacing: -0.01em;">NestDB</div>
                <div style="color: #34C759; font-size: 0.75rem; font-weight: 600; letter-spacing: 0.04em; text-transform: uppercase;">Database · Management</div>
            </div>
        </div>
        <p style="color: #999; font-size: 0.875rem; line-height: 1.65; margin: 0 0 1.25rem 0;">
            Browse, edit, and manage survey database tables. Full CRUD support with version history and rollback capability.
        </p>
        <div style="border-top: 1px solid rgba(255,255,255,0.08); padding-top: 0.875rem; display: flex; align-items: center; justify-content: space-between;">
            <div style="display: flex; gap: 0.5rem; flex-wrap: wrap;">
                <span style="background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.1); border-radius: 5px; padding: 0.2rem 0.5rem; font-size: 0.7rem; color: #999;">CRUD</span>
                <span style="background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.1); border-radius: 5px; padding: 0.2rem 0.5rem; font-size: 0.7rem; color: #999;">Version control</span>
                <span style="background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.1); border-radius: 5px; padding: 0.2rem 0.5rem; font-size: 0.7rem; color: #999;">SQL editor</span>
            </div>
            <span style="font-size: 0.7rem; color: #555;">⚡ SQLite</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<div style='height: 1rem;'></div>", unsafe_allow_html=True)

# ── Feature Cards Row 3 ──────────────────────────────────────────────────────
col5, col6 = st.columns(2, gap="medium")

with col5:
    st.markdown("""
    <div class="feature-card">
        <div style="
            display: flex;
            align-items: center;
            gap: 0.75rem;
            margin-bottom: 1.25rem;
        ">
            <div style="
                width: 40px; height: 40px;
                background: linear-gradient(135deg, rgba(255,214,10,0.2), rgba(255,214,10,0.06));
                border: 1px solid rgba(255,214,10,0.25);
                border-radius: 10px;
                display: flex; align-items: center; justify-content: center;
                font-size: 1.25rem; flex-shrink: 0;
            ">🗺️</div>
            <div>
                <div style="color: #F0F0F0; font-weight: 700; font-size: 1.0625rem; letter-spacing: -0.01em;">NestMap</div>
                <div style="color: #FFD60A; font-size: 0.75rem; font-weight: 600; letter-spacing: 0.04em; text-transform: uppercase;">Geographic · STAC</div>
            </div>
        </div>
        <p style="color: #999; font-size: 0.875rem; line-height: 1.65; margin: 0 0 1.25rem 0;">
            Geographic intelligence with expert-validated bird locations, COG mosaic visualization, and STAC catalog integration.
        </p>
        <div style="border-top: 1px solid rgba(255,255,255,0.08); padding-top: 0.875rem; display: flex; gap: 0.5rem; flex-wrap: wrap;">
            <span style="background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.1); border-radius: 5px; padding: 0.2rem 0.5rem; font-size: 0.7rem; color: #999;">STAC catalog</span>
            <span style="background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.1); border-radius: 5px; padding: 0.2rem 0.5rem; font-size: 0.7rem; color: #999;">COG mosaics</span>
            <span style="background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.1); border-radius: 5px; padding: 0.2rem 0.5rem; font-size: 0.7rem; color: #999;">Species maps</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

with col6:
    st.markdown("""
    <div style="
        background: rgba(255,255,255,0.025);
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
        border: 1px dashed rgba(255,255,255,0.1);
        border-radius: 16px;
        padding: 1.75rem;
        height: 100%;
        display: flex;
        align-items: center;
        justify-content: center;
        min-height: 200px;
    ">
        <div style="text-align: center;">
            <div style="font-size: 2rem; margin-bottom: 0.75rem; opacity: 0.4;">🚀</div>
            <div style="font-size: 0.875rem; font-weight: 600; color: rgba(255,255,255,0.25);">More features coming</div>
            <div style="font-size: 0.75rem; color: rgba(255,255,255,0.15); margin-top: 0.25rem;">DevDays 2026</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<div style='height: 2.5rem;'></div>", unsafe_allow_html=True)

# ── Getting Started ──────────────────────────────────────────────────────────
st.markdown("""
<div style="
    font-size: 0.6875rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: #666;
    margin-bottom: 1rem;
">Getting Started</div>
""", unsafe_allow_html=True)

st.markdown("""
<div style="background: rgba(255,255,255,0.04); backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px); border: 1px solid rgba(255,255,255,0.09); border-radius: 16px; padding: 1.5rem 1.75rem; box-shadow: 0 4px 24px rgba(0,0,0,0.35), inset 0 1px 0 rgba(255,255,255,0.06);">
    <div style="display: flex; flex-direction: column; gap: 0.875rem;">
        <div style="display: flex; align-items: flex-start; gap: 1rem;">
            <div style="
                width: 24px; height: 24px; border-radius: 50%;
                background: rgba(217,119,87,0.15); border: 1px solid rgba(217,119,87,0.3);
                display: flex; align-items: center; justify-content: center;
                font-size: 0.7rem; font-weight: 700; color: #D97757; flex-shrink: 0; margin-top: 1px;
            ">1</div>
            <div>
                <span style="color: #E5E5E5; font-weight: 600; font-size: 0.9rem;">Open NestChat</span>
                <span style="color: #777; font-size: 0.875rem;"> — ask questions like "Show Brown Pelican trends 2010–2021"</span>
            </div>
        </div>
        <div style="display: flex; align-items: flex-start; gap: 1rem;">
            <div style="
                width: 24px; height: 24px; border-radius: 50%;
                background: rgba(217,119,87,0.15); border: 1px solid rgba(217,119,87,0.3);
                display: flex; align-items: center; justify-content: center;
                font-size: 0.7rem; font-weight: 700; color: #D97757; flex-shrink: 0; margin-top: 1px;
            ">2</div>
            <div>
                <span style="color: #E5E5E5; font-weight: 600; font-size: 0.9rem;">Try NestVision</span>
                <span style="color: #777; font-size: 0.875rem;"> — upload a colony image and watch AI detect every bird</span>
            </div>
        </div>
        <div style="display: flex; align-items: flex-start; gap: 1rem;">
            <div style="
                width: 24px; height: 24px; border-radius: 50%;
                background: rgba(217,119,87,0.15); border: 1px solid rgba(217,119,87,0.3);
                display: flex; align-items: center; justify-content: center;
                font-size: 0.7rem; font-weight: 700; color: #D97757; flex-shrink: 0; margin-top: 1px;
            ">3</div>
            <div>
                <span style="color: #E5E5E5; font-weight: 600; font-size: 0.9rem;">Export results</span>
                <span style="color: #777; font-size: 0.875rem;"> — download data as CSV or annotated images</span>
            </div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

st.markdown("<div style='height: 3rem;'></div>", unsafe_allow_html=True)

# ── Footer ───────────────────────────────────────────────────────────────────
st.markdown("""
<div style="
    text-align: center;
    padding: 1.5rem;
    color: rgba(255,255,255,0.2);
    font-size: 0.75rem;
    border-top: 1px solid rgba(255,255,255,0.06);
">
    NestScope · Gulf Coast Avian Monitoring Platform · 2026
</div>
""", unsafe_allow_html=True)
