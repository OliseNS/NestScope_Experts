"""
Top Navigation Bar Component
Google Cloud-like top bar with service status and navigation
"""

import streamlit as st
from .status import get_services_status


def render_top_status_bar():
    """
    Renders a Google Cloud-style top status bar with service health indicators
    Shows current page and system status in a compact horizontal layout
    """
    # Get service status
    status_data = get_services_status()
    services = status_data.get("services", {})
    overall = status_data.get("overall_status", "unknown")

    # Count running services
    running_count = sum(1 for s in services.values() if s.get("status") == "running")
    total_count = len(services)

    # Determine status color and text
    if overall == "healthy":
        status_color = "#4CAF50"
        status_icon = "●"
        status_text = "All Systems Operational"
    elif running_count > 0:
        status_color = "#FFA500"
        status_icon = "◐"
        status_text = f"{running_count}/{total_count} Services Online"
    else:
        status_color = "#FF6464"
        status_icon = "○"
        status_text = "Services Offline"

    # Render top bar
    st.markdown(f"""
        <div style="
            background: #1E1E1E;
            border-bottom: 1px solid #333;
            padding: 0.75rem 1.5rem;
            margin: -5rem -5rem 2rem -5rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
        ">
            <div style="display: flex; align-items: center; gap: 1rem;">
                <span style="font-size: 1.25rem;">🦅</span>
                <span style="
                    color: #E5E5E5;
                    font-weight: 600;
                    font-size: 0.95rem;
                ">NestScope</span>
                <span style="color: #666; margin: 0 0.25rem;">/</span>
                <span style="color: #A0A0A0; font-size: 0.875rem;">{st.session_state.get('page_name', 'Home')}</span>
            </div>
            <div style="
                display: flex;
                align-items: center;
                gap: 1rem;
            ">
                <div style="
                    display: flex;
                    align-items: center;
                    gap: 0.5rem;
                    padding: 0.4rem 0.75rem;
                    background: rgba(255, 255, 255, 0.02);
                    border: 1px solid rgba(255, 255, 255, 0.08);
                    border-radius: 6px;
                    font-size: 0.8rem;
                ">
                    <span style="color: {status_color}; font-size: 0.7rem;">{status_icon}</span>
                    <span style="color: #A0A0A0;">{status_text}</span>
                </div>
                <a href="http://localhost:5000" target="_blank" style="
                    text-decoration: none;
                    color: #A0A0A0;
                    font-size: 0.875rem;
                    padding: 0.4rem 0.75rem;
                    border-radius: 6px;
                    transition: all 0.2s;
                    display: inline-block;
                " onmouseover="this.style.color='#D97757'; this.style.background='rgba(217, 119, 87, 0.1)';" onmouseout="this.style.color='#A0A0A0'; this.style.background='transparent';">
                    🏷️ Labeller
                </a>
            </div>
        </div>
    """, unsafe_allow_html=True)


def render_page_header(title: str, description: str, icon: str = ""):
    """
    Renders a Google Cloud-style page header

    Args:
        title: Page title
        description: Page description
        icon: Optional emoji icon
    """
    icon_html = f'<span style="font-size: 2rem; margin-right: 0.75rem;">{icon}</span>' if icon else ""

    st.markdown(f"""
        <div style="
            margin: 2rem 0 2.5rem 0;
        ">
            <div style="display: flex; align-items: center; margin-bottom: 0.5rem;">
                {icon_html}
                <h1 style="
                    color: #E5E5E5;
                    font-size: 2rem;
                    font-weight: 600;
                    margin: 0;
                    letter-spacing: -0.03em;
                ">{title}</h1>
            </div>
            <p style="
                color: #A0A0A0;
                font-size: 0.9375rem;
                margin: 0;
                line-height: 1.6;
            ">{description}</p>
        </div>
    """, unsafe_allow_html=True)
