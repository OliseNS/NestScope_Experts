"""
System Status Page
Detailed view of all NestScope service health statuses
"""

import streamlit as st
from components import (
    render_sidebar_section,
    get_services_status
)
from styles import get_custom_css

# ============================================================================
# PAGE CONFIG
# ============================================================================

st.set_page_config(
    page_title="System Status - NestScope",
    page_icon="🦅",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Apply custom styling
st.markdown(get_custom_css(), unsafe_allow_html=True)

# ============================================================================
# SIDEBAR
# ============================================================================

with st.sidebar:
    # Navigation Section
    render_sidebar_section("Navigation")

    if st.button("🏠 Home", use_container_width=True, help="Return to home page"):
        st.switch_page("app.py")

    if st.button("💬 NestChat", use_container_width=True, help="Natural language data queries"):
        st.switch_page("pages/01_nest_chat.py")

    if st.button("🦅 NestVision", use_container_width=True, help="AI bird detection & counting"):
        st.switch_page("pages/02_nest_vision.py")

    if st.button("🗄️ NestDB", use_container_width=True, help="Database management interface"):
        st.switch_page("pages/04_db_editor.py")

    # Tools section
    render_sidebar_section("Tools")

    st.link_button("🧑‍🔬 Nestperts", "http://localhost:5000", use_container_width=True, help="Expert species training platform")

    # System Status section
    render_sidebar_section("System Status")

    st.markdown("""
        <div style="
            background: rgba(76, 175, 80, 0.1);
            border: 1px solid rgba(76, 175, 80, 0.3);
            border-radius: 6px;
            padding: 0.75rem;
            margin: 0.5rem 0;
        ">
            <div style="display: flex; align-items: center; gap: 0.5rem;">
                <span style="color: #4CAF50; font-size: 1rem;">●</span>
                <span style="color: #E5E5E5; font-size: 0.75rem; font-weight: 500;">Viewing Status Page</span>
            </div>
        </div>
    """, unsafe_allow_html=True)

# ============================================================================
# MAIN CONTENT
# ============================================================================

st.markdown("## System Status")
st.markdown("Real-time health monitoring of all NestScope services")

# Fetch status
status_data = get_services_status()
overall = status_data.get("overall_status", "unknown")
services = status_data.get("services", {})

# Overall status card
if overall == "healthy":
    status_color = "#4CAF50"
    status_icon = "✓"
    status_message = "All Systems Operational"
    status_bg = "rgba(76, 175, 80, 0.1)"
elif overall == "degraded":
    status_color = "#FFA500"
    status_icon = "⚠"
    status_message = "Some Services Degraded"
    status_bg = "rgba(255, 165, 0, 0.1)"
else:
    status_color = "#FF6464"
    status_icon = "✗"
    status_message = "Services Offline"
    status_bg = "rgba(255, 100, 100, 0.1)"

st.markdown(f"""
    <div style="
        background: {status_bg};
        border: 2px solid {status_color};
        border-radius: 12px;
        padding: 2rem;
        text-align: center;
        margin: 2rem 0;
    ">
        <div style="color: {status_color}; font-size: 4rem; line-height: 1; margin-bottom: 1rem;">
            {status_icon}
        </div>
        <div style="color: {status_color}; font-size: 1.5rem; font-weight: 600;">
            {status_message}
        </div>
    </div>
""", unsafe_allow_html=True)

# Service details
if services:
    st.markdown("### Service Details")

    for service_key, service_info in services.items():
        name = service_info.get("name", service_key)
        status = service_info.get("status", "unknown")
        port = service_info.get("port", "")
        url = service_info.get("url", "")

        # Determine status styling
        if status == "running":
            color = "#4CAF50"
            status_text = "Running"
            bg = "rgba(76, 175, 80, 0.05)"
        elif status == "offline":
            color = "#FF6464"
            status_text = "Offline"
            bg = "rgba(255, 100, 100, 0.05)"
        elif status == "error":
            color = "#FFA500"
            status_text = "Error"
            bg = "rgba(255, 165, 0, 0.05)"
        else:
            color = "#999"
            status_text = "Unknown"
            bg = "rgba(153, 153, 153, 0.05)"

        # Service card
        st.markdown(f"""
            <div style="
                background: {bg};
                border: 1px solid {color};
                border-radius: 8px;
                padding: 1.5rem;
                margin: 1rem 0;
            ">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.75rem;">
                    <div style="display: flex; align-items: center; gap: 1rem;">
                        <span style="color: {color}; font-size: 1.5rem;">●</span>
                        <div>
                            <div style="color: #E5E5E5; font-weight: 600; font-size: 1.1rem;">{name}</div>
                            <div style="color: #999; font-size: 0.9rem; margin-top: 0.25rem;">Port: {port}</div>
                        </div>
                    </div>
                    <div style="
                        color: {color};
                        font-size: 0.9rem;
                        font-weight: 600;
                        padding: 0.5rem 1rem;
                        background: rgba(255, 255, 255, 0.05);
                        border-radius: 6px;
                    ">
                        {status_text}
                    </div>
                </div>
                {f'<div style="color: #A0A0A0; font-size: 0.85rem;">URL: <code>{url}</code></div>' if url else ''}
            </div>
        """, unsafe_allow_html=True)

else:
    st.warning("Cannot retrieve service status. Backend may be offline.")

# Refresh button
col1, col2, col3 = st.columns([1, 1, 1])
with col2:
    if st.button("🔄 Refresh Status", use_container_width=True, type="primary"):
        st.rerun()
