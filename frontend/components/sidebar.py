"""
Shared sidebar component for consistent branding and navigation
Google Cloud-like sidebar organization
"""

import streamlit as st
import base64
import os


def _get_logo_b64() -> str:
    logo_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logo1.png")
    try:
        with open(logo_path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except Exception:
        return ""


def render_sidebar_header():
    """
    Renders the NestScope brand header at the top of the sidebar.
    """
    logo_b64 = _get_logo_b64()
    if logo_b64:
        logo_html = f'<img src="data:image/png;base64,{logo_b64}" style="width: 140px; filter: invert(1); opacity: 0.88;" />'
    else:
        logo_html = '<span style="font-size: 1.5rem;">🦅</span><span style="font-size: 1.25rem; font-weight: 600; color: #E5E5E5; margin-left: 0.5rem;">NestScope</span>'

    st.markdown(f"""
        <div style="
            padding: 1rem 0.75rem 1.25rem;
            margin-bottom: 1rem;
            border-bottom: 1px solid rgba(255, 255, 255, 0.08);
        ">
            {logo_html}
            <div style="
                color: #666;
                font-size: 0.6875rem;
                margin-top: 0.375rem;
                font-weight: 500;
                letter-spacing: 0.02em;
            ">Avian Monitoring Suite</div>
        </div>
    """, unsafe_allow_html=True)


def render_sidebar_navigation():
    """
    Renders the navigation section in the sidebar.
    Shows links to different pages of the application.
    """
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
        ">Navigation</div>
    """, unsafe_allow_html=True)

    # Get current page
    try:
        current_page = st.session_state.get("current_page", "Home")
    except:
        current_page = "Home"

    # Navigation links
    nav_items = [
        ("🏠", "Home", "/"),
        ("💬", "NestChat", "/nest_chat"),
        ("🦅", "NestVision", "/nest_vision"),
    ]

    for icon, label, _ in nav_items:
        is_active = current_page == label
        button_style = "active" if is_active else ""

        if st.button(
            f"{icon} {label}",
            key=f"nav_{label}",
            use_container_width=True,
            type="secondary" if is_active else "tertiary"
        ):
            # Navigation handled by Streamlit's page system
            pass


def render_sidebar_section(title: str):
    """
    Renders a Google Cloud-style section header in the sidebar

    Args:
        title: Section title to display
    """
    st.markdown(f"""
        <div style="
            font-size: 0.6875rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            color: #A0A0A0;
            margin: 1.5rem 0 0.625rem;
            padding: 0 0.75rem;
            opacity: 0.7;
        ">{title}</div>
    """, unsafe_allow_html=True)


def render_sidebar_footer():
    """
    Renders optional footer content in the sidebar.
    Google Cloud-style compact footer.
    """
    st.markdown("""
        <div style="
            margin-top: 2rem;
            padding: 0.75rem;
            font-size: 0.6875rem;
            color: #666;
            border-top: 1px solid rgba(255, 255, 255, 0.05);
        ">
            <div style="margin-bottom: 0.25rem; font-weight: 500;">Gulf Coast Bird Data</div>
            <div style="opacity: 0.6;">2010-2021 • 5 States</div>
        </div>
    """, unsafe_allow_html=True)
