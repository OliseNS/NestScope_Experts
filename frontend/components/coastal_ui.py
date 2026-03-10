"""
Coastal UI Components
Matches Nestperts labeller design system
"""

import streamlit as st


def card(content: str, hover: bool = True):
    """
    Render a coastal-themed card

    Args:
        content: HTML content to display in card
        hover: Enable hover effect (default True)
    """
    hover_class = "card-hover" if hover else ""

    st.markdown(f"""
        <style>
        .coastal-card {{
            background: var(--surface-base);
            border: 1px solid var(--surface-border);
            border-radius: var(--radius-lg);
            padding: var(--space-6);
            transition: all var(--transition-base);
        }}

        .coastal-card.card-hover:hover {{
            border-color: var(--brand-primary);
            box-shadow: var(--shadow-lg);
            transform: translateY(-2px);
        }}
        </style>
        <div class="coastal-card {hover_class}">
            {content}
        </div>
    """, unsafe_allow_html=True)


def feature_card(icon: str, title: str, description: str, features: list, footer_text: str = None):
    """
    Render a feature card matching the labeller design

    Args:
        icon: Emoji icon
        title: Card title
        description: Brief description
        features: List of feature bullet points
        footer_text: Optional footer text
    """
    features_html = "".join([f"<li>{f}</li>" for f in features])

    footer_html = ""
    if footer_text:
        footer_html = f"""
        <div style="margin-top: var(--space-4); padding-top: var(--space-4); border-top: 1px solid var(--surface-border);">
            <p style="font-size: 0.75rem; color: var(--text-tertiary); margin: 0;">
                {footer_text}
            </p>
        </div>
        """

    st.markdown(f"""
        <div class="coastal-card card-hover">
            <div style="
                display: inline-block;
                background: rgba(217, 119, 87, 0.15);
                border-radius: var(--radius-md);
                padding: var(--space-2) var(--space-3);
                margin-bottom: var(--space-4);
            ">
                <span style="font-size: 1.5rem;">{icon}</span>
            </div>
            <h3 style="color: var(--text-primary); margin: 0 0 var(--space-3) 0; font-size: 1.25rem; font-weight: 600; font-family: var(--font-display);">
                {title}
            </h3>
            <p style="color: var(--text-secondary); font-size: 0.875rem; line-height: 1.6; margin-bottom: var(--space-4);">
                {description}
            </p>
            <ul style="color: var(--text-primary); font-size: 0.875rem; line-height: 1.8; margin-left: var(--space-5); padding-left: 0;">
                {features_html}
            </ul>
            {footer_html}
        </div>
    """, unsafe_allow_html=True)


def section_header(title: str):
    """
    Render a section header with coastal styling

    Args:
        title: Section title
    """
    st.markdown(f"""
        <div style="
            font-size: 0.6875rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            color: var(--text-tertiary);
            margin-bottom: var(--space-4);
            margin-top: var(--space-8);
        ">{title}</div>
    """, unsafe_allow_html=True)


def stat_card(value: str, label: str, change: str = None, change_positive: bool = True):
    """
    Render a statistics card

    Args:
        value: Main stat value
        label: Stat label
        change: Optional change indicator (e.g., "+12%")
        change_positive: Whether change is positive (green) or negative (red)
    """
    change_html = ""
    if change:
        change_color = "var(--success)" if change_positive else "var(--error)"
        change_html = f"""
        <div style="margin-top: var(--space-2); font-size: 0.75rem; font-weight: 600; color: {change_color};">
            {change}
        </div>
        """

    st.markdown(f"""
        <div class="coastal-card card-hover" style="text-align: center;">
            <div style="
                font-size: 2.5rem;
                font-weight: 700;
                font-family: var(--font-display);
                color: var(--brand-primary);
                line-height: 1;
                margin-bottom: var(--space-2);
            ">{value}</div>
            <div style="
                font-size: 0.75rem;
                color: var(--text-tertiary);
                text-transform: uppercase;
                letter-spacing: 0.05em;
                font-weight: 600;
            ">{label}</div>
            {change_html}
        </div>
    """, unsafe_allow_html=True)


def info_banner(message: str, icon: str = "ℹ️", type: str = "info"):
    """
    Render an info banner

    Args:
        message: Message to display
        icon: Icon emoji
        type: Banner type ("info", "success", "warning", "error")
    """
    color_map = {
        "info": "var(--info)",
        "success": "var(--success)",
        "warning": "var(--warning)",
        "error": "var(--error)"
    }

    border_color = color_map.get(type, "var(--info)")

    st.markdown(f"""
        <div style="
            background: var(--surface-base);
            border: 1px solid var(--surface-border);
            border-left: 3px solid {border_color};
            border-radius: var(--radius-md);
            padding: var(--space-4);
            display: flex;
            align-items: center;
            gap: var(--space-3);
            margin: var(--space-4) 0;
        ">
            <span style="font-size: 1.25rem;">{icon}</span>
            <p style="margin: 0; color: var(--text-secondary); font-size: 0.875rem; line-height: 1.6;">
                {message}
            </p>
        </div>
    """, unsafe_allow_html=True)


def badge(text: str, type: str = "primary"):
    """
    Render a badge

    Args:
        text: Badge text
        type: Badge type ("primary", "success", "warning", "error", "info")
    """
    color_map = {
        "primary": ("rgba(217, 119, 87, 0.15)", "var(--brand-primary)"),
        "success": ("rgba(74, 157, 95, 0.15)", "var(--success)"),
        "warning": ("rgba(212, 160, 47, 0.15)", "var(--warning)"),
        "error": ("rgba(199, 74, 74, 0.15)", "var(--error)"),
        "info": ("rgba(74, 127, 157, 0.15)", "var(--info)")
    }

    bg_color, text_color = color_map.get(type, color_map["primary"])

    return f"""
        <span style="
            display: inline-flex;
            align-items: center;
            padding: 0.25rem 0.75rem;
            font-size: 0.75rem;
            font-weight: 600;
            border-radius: var(--radius-full);
            background: {bg_color};
            color: {text_color};
        ">{text}</span>
    """


def divider():
    """Render a coastal-themed divider"""
    st.markdown("""
        <hr style="
            border: none;
            border-top: 1px solid var(--surface-border);
            margin: var(--space-6) 0;
            opacity: 0.5;
        "/>
    """, unsafe_allow_html=True)


def spacer(size: str = "4"):
    """
    Add vertical spacing

    Args:
        size: Space size (1-20, corresponds to spacing scale)
    """
    st.markdown(f'<div style="height: var(--space-{size});"></div>', unsafe_allow_html=True)


def gradient_card(content: str):
    """Render a card with gradient background"""
    st.markdown(f"""
        <div style="
            background: linear-gradient(135deg, rgba(217, 119, 87, 0.08) 0%, rgba(217, 119, 87, 0.02) 100%);
            border: 1px solid rgba(217, 119, 87, 0.2);
            border-radius: var(--radius-lg);
            padding: var(--space-6);
            margin: var(--space-4) 0;
        ">
            <p style="color: var(--text-primary); font-size: 1rem; line-height: 1.7; margin: 0;">
                {content}
            </p>
        </div>
    """, unsafe_allow_html=True)


def page_header(title: str, subtitle: str = None):
    """
    Render a page header with title and optional subtitle

    Args:
        title: Page title
        subtitle: Optional subtitle
    """
    subtitle_html = ""
    if subtitle:
        subtitle_html = f"""
        <p style="
            color: var(--text-secondary);
            font-size: 1rem;
            margin: 0;
            line-height: 1.6;
        ">{subtitle}</p>
        """

    st.markdown(f"""
        <div style="margin: 0 0 var(--space-8) 0;">
            <h1 style="
                color: var(--text-primary);
                font-size: 2.5rem;
                font-weight: 600;
                margin: 0 0 var(--space-2) 0;
                letter-spacing: -0.03em;
                font-family: var(--font-display);
            ">{title}</h1>
            {subtitle_html}
        </div>
    """, unsafe_allow_html=True)
