"""
Service Status Component
Displays the health status of all NestScope services
"""

import streamlit as st
import requests
import os
from typing import Dict, Any


def get_services_status() -> Dict[str, Any]:
    """
    Fetch service status from the backend API
    Returns status information for all services
    """
    try:
        api_base_url = os.getenv("API_BASE_URL", "http://localhost:8000")
        response = requests.get(f"{api_base_url}/services/status", timeout=3)

        if response.status_code == 200:
            return response.json()
        else:
            return {
                "overall_status": "error",
                "services": {},
                "error": f"Status check failed with code {response.status_code}"
            }
    except requests.exceptions.ConnectionError:
        return {
            "overall_status": "offline",
            "services": {},
            "error": "Cannot connect to backend"
        }
    except Exception as e:
        return {
            "overall_status": "error",
            "services": {},
            "error": str(e)
        }


def render_service_status():
    """
    Renders the service status indicator in the sidebar
    Shows a compact view of all service health statuses
    """
    # Fetch status
    status_data = get_services_status()
    services = status_data.get("services", {})

    # If we can't get status, show offline message
    if not services:
        st.markdown("""
            <div style="
                background: rgba(255, 100, 100, 0.1);
                border: 1px solid rgba(255, 100, 100, 0.3);
                border-radius: 8px;
                padding: 0.75rem;
                font-size: 0.75rem;
            ">
                <div style="color: #FF6464; font-weight: 600; margin-bottom: 0.25rem;">
                    ⚠ Status Unavailable
                </div>
                <div style="color: #999; font-size: 0.7rem;">
                    Cannot connect to backend
                </div>
            </div>
        """, unsafe_allow_html=True)
        return

    # Build service status HTML
    status_rows = []
    for service_key, service_info in services.items():
        name = service_info.get("name", service_key)
        status = service_info.get("status", "unknown")
        port = service_info.get("port", "")

        # Determine status color and icon
        if status == "running":
            color = "#4CAF50"
            icon = "●"
            status_text = "Running"
        elif status == "offline":
            color = "#FF6464"
            icon = "●"
            status_text = "Offline"
        elif status == "error":
            color = "#FFA500"
            icon = "●"
            status_text = "Error"
        else:
            color = "#999"
            icon = "○"
            status_text = "Unknown"

        # Service row
        status_rows.append(f'''
            <div style="
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 0.5rem 0;
                {'' if service_key == list(services.keys())[-1] else 'border-bottom: 1px solid rgba(255, 255, 255, 0.05);'}
            ">
                <div style="display: flex; align-items: center; gap: 0.5rem;">
                    <span style="color: {color}; font-size: 0.8rem;">{icon}</span>
                    <div>
                        <div style="color: #E5E5E5; font-weight: 500; font-size: 0.75rem;">{name}</div>
                        <div style="color: #666; font-size: 0.65rem;">:{port}</div>
                    </div>
                </div>
                <div style="color: {color}; font-size: 0.7rem; font-weight: 600;">
                    {status_text}
                </div>
            </div>
        ''')

    status_html = f'''
        <div style="background: #2D2D2D; border: 1px solid #404040; border-radius: 8px; padding: 0.75rem; font-size: 0.75rem;">
            {''.join(status_rows)}
        </div>
    '''

    st.markdown(status_html, unsafe_allow_html=True)

    # Add refresh button
    if st.button("🔄 Refresh Status", key="refresh_status", use_container_width=True, help="Check service status"):
        st.rerun()


def render_service_status_compact():
    """
    Renders a very compact service status indicator
    Shows only overall health with a single indicator
    """
    status_data = get_services_status()
    overall = status_data.get("overall_status", "unknown")
    services = status_data.get("services", {})

    # Count running services
    running_count = sum(1 for s in services.values() if s.get("status") == "running")
    total_count = len(services)

    # Determine color
    if overall == "healthy":
        color = "#4CAF50"
        icon = "●"
        text = "All Systems Operational"
    elif overall == "degraded":
        color = "#FFA500"
        icon = "◐"
        text = f"{running_count}/{total_count} Services Running"
    else:
        color = "#FF6464"
        icon = "○"
        text = "Services Offline"

    st.markdown(f"""
        <div style="
            background: rgba(255, 255, 255, 0.02);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 6px;
            padding: 0.5rem 0.75rem;
            font-size: 0.7rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
            margin: 0.5rem 0;
        ">
            <span style="color: {color}; font-size: 0.9rem;">{icon}</span>
            <span style="color: #A0A0A0;">{text}</span>
        </div>
    """, unsafe_allow_html=True)


def render_service_status_link():
    """
    Renders a simple status link in the sidebar
    Shows overall status and links to detailed status page
    """
    status_data = get_services_status()
    overall = status_data.get("overall_status", "unknown")
    services = status_data.get("services", {})

    # Count running services
    running_count = sum(1 for s in services.values() if s.get("status") == "running")
    total_count = len(services)

    # Determine status text and color
    if overall == "healthy":
        color = "#4CAF50"
        status_text = "All Systems Operational"
    elif overall == "degraded":
        color = "#FFA500"
        status_text = f"{running_count}/{total_count} Services Running"
    else:
        color = "#FF6464"
        status_text = "Services Offline"

    # Simple status indicator
    col1, col2 = st.columns([0.15, 0.85])
    with col1:
        st.markdown(f'<div style="color: {color}; font-size: 1.2rem; line-height: 1;">●</div>', unsafe_allow_html=True)
    with col2:
        st.markdown(f'<div style="color: #E5E5E5; font-size: 0.75rem; line-height: 1.4;">{status_text}</div>', unsafe_allow_html=True)

    # Link to detailed status page
    if st.button("View Details →", key="status_details_link", use_container_width=True, type="secondary"):
        st.switch_page("pages/03_system_status.py")
