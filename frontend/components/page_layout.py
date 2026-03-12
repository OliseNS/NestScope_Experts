"""
Shared Page Layout Component
Provides consistent page structure, header, and sidebar across all pages
"""

import streamlit as st
from .sidebar import render_sidebar_section
from .status import render_service_status_link
from styles import get_custom_css


def init_page(page_title: str, page_icon: str = "🦅", layout: str = "wide"):
    """
    Initialize page configuration and styling.
    Call this FIRST in every page file.

    Args:
        page_title: Browser tab title (e.g., "NestChat - NestScope")
        page_icon: Emoji icon for browser tab
        layout: Page layout ("wide" or "centered")
    """
    st.set_page_config(
        page_title=page_title,
        page_icon=page_icon,
        layout=layout,
        initial_sidebar_state="expanded"
    )

    # Apply custom CSS
    st.markdown(get_custom_css(), unsafe_allow_html=True)

    # Hide Streamlit's default page navigation more aggressively
    # Also fix header z-index to not block UI elements
    # Ensure background matches Claude Code theme
    st.markdown("""
    <style>
        /* CRITICAL: Hide Streamlit's default page nav immediately */
        [data-testid="stSidebarNav"] {
            display: none !important;
            height: 0 !important;
            min-height: 0 !important;
        }

        /* Force Claude Code background color */
        .stApp, [data-testid="stAppViewContainer"], .main {
            background-color: #1e1e1e !important;
        }

        [data-testid="stAppViewContainer"] > section:first-child {
            background-color: #1e1e1e !important;
        }

        /* Fixed header - REDUCED z-index to not block publish button */
        .fixed-header {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            background: #1e1e1e;
            border-bottom: 1px solid rgba(86, 184, 151, 0.2);
            padding: 0.75rem 1.5rem;
            display: flex;
            align-items: center;
            gap: 0.75rem;
            z-index: 100;
        }

        /* Push main content down to account for fixed header */
        .main .block-container {
            padding-top: 4rem;
            background-color: #1e1e1e !important;
        }

        /* Ensure sidebar is below header */
        [data-testid="stSidebar"] {
            padding-top: 3.5rem;
            background-color: #1e1e1e !important;
        }
    </style>
    """, unsafe_allow_html=True)


def render_header(page_name: str = None):
    """
    Render the fixed header at the top of the page.
    No longer shows a large title that blocks UI elements.

    Args:
        page_name: Optional page name to display in header
    """
    page_display = f' / {page_name}' if page_name else ''

    st.markdown(f"""
        <div class="fixed-header">
            <span style="font-size: 1.25rem;">🦅</span>
            <span style="font-size: 0.95rem; font-weight: 600; color: #E5E5E5;">NestScope</span>
            <span style="color: #666; font-size: 0.8rem;">{page_display}</span>
        </div>
    """, unsafe_allow_html=True)


def render_sidebar(active_page: str = "home"):
    """
    Render the shared sidebar with navigation and tools.
    Call this in every page's sidebar context.

    Args:
        active_page: Current page identifier ("home", "nestchat", "nestvision", "nestdb", "status")
    """
    from .sidebar import render_sidebar_header
    
    # Brand Header
    render_sidebar_header()

    # Exploration tools Section
    render_sidebar_section("Exploration tools")

    # Home button
    if st.button(
        "🏠 Home",
        use_container_width=True,
        help="Return to home page",
        type="primary" if active_page == "home" else "secondary",
        key="sb_nav_home"
    ):
        st.switch_page("app.py")

    # NestChat button
    if st.button(
        "💬 NestChat",
        use_container_width=True,
        help="Natural language data queries",
        type="primary" if active_page == "nestchat" else "secondary",
        key="sb_nav_chat"
    ):
        st.switch_page("pages/01_nest_chat.py")

    # NestVision button
    if st.button(
        "🦅 NestVision",
        use_container_width=True,
        help="AI bird detection & counting",
        type="primary" if active_page == "nestvision" else "secondary",
        key="sb_nav_vision"
    ):
        st.switch_page("pages/02_nest_vision.py")

    # Expert tools section
    render_sidebar_section("Expert tools")

    st.link_button(
        "🧑‍🔬 Nestperts",
        "http://localhost:5000",
        use_container_width=True,
        help="Expert species training platform"
    )

    st.link_button(
        "🗄️ NestDB",
        "http://localhost:5000/nestdb",
        use_container_width=True,
        help="Database management interface"
    )

    st.link_button(
        "🌊 Flood Intelligence",
        "http://localhost:5000/flood-intelligence",
        use_container_width=True,
        help="Real-time coastal flood risk monitoring (Expert tool)"
    )

    # System Status section
    render_sidebar_section("System Status")
    render_service_status_link()
