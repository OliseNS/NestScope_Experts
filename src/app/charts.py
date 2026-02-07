"""
Visualization components for bird survey data.

This module creates Plotly charts for different query types:
- Line charts for trends over time
- Bar charts for rankings and comparisons
- Geographic maps for spatial data
- Before/after comparisons for impact assessment

Person 3 (Frontend Developer) implementation
"""

import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from typing import Optional


def create_trend_chart(
    df: pd.DataFrame,
    species: str,
    title: Optional[str] = None
) -> go.Figure:
    """
    Create a line chart for species population trend.

    Args:
        df: DataFrame with columns: year, count
        species: Species name for title
        title: Optional custom title

    Returns:
        Plotly Figure object
    """
    if title is None:
        title = f"{species} Population Trend"

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=df['year'],
        y=df['count'],
        mode='lines+markers',
        name=species,
        line=dict(width=3),
        marker=dict(size=8)
    ))

    fig.update_layout(
        title=title,
        xaxis_title="Year",
        yaxis_title="Population Count",
        hovermode='x unified',
        template='plotly_white'
    )

    return fig


def create_ranking_chart(
    df: pd.DataFrame,
    title: Optional[str] = None
) -> go.Figure:
    """
    Create a horizontal bar chart for species rankings.

    Args:
        df: DataFrame with columns: species, count
        title: Optional custom title

    Returns:
        Plotly Figure object
    """
    if title is None:
        title = "Top Species by Population"

    # Sort by count descending
    df_sorted = df.sort_values('count', ascending=True)

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=df_sorted['count'],
        y=df_sorted['species'],
        orientation='h',
        marker=dict(
            color=df_sorted['count'],
            colorscale='Viridis'
        )
    ))

    fig.update_layout(
        title=title,
        xaxis_title="Population Count",
        yaxis_title="Species",
        template='plotly_white'
    )

    return fig


def create_comparison_chart(
    df: pd.DataFrame,
    regions: list,
    title: Optional[str] = None
) -> go.Figure:
    """
    Create a grouped bar chart comparing regions.

    Args:
        df: DataFrame with columns: region, species, count
        regions: List of region names
        title: Optional custom title

    Returns:
        Plotly Figure object
    """
    if title is None:
        title = f"Regional Comparison: {', '.join(regions)}"

    fig = px.bar(
        df,
        x='species',
        y='count',
        color='region',
        barmode='group',
        title=title,
        template='plotly_white'
    )

    fig.update_layout(
        xaxis_title="Species",
        yaxis_title="Population Count"
    )

    return fig


def create_temporal_comparison_chart(
    df: pd.DataFrame,
    event_name: str = "Event",
    title: Optional[str] = None
) -> go.Figure:
    """
    Create a before/after comparison chart.

    Args:
        df: DataFrame with columns: period (before/after), count
        event_name: Name of the event (e.g., "Hurricane Ida")
        title: Optional custom title

    Returns:
        Plotly Figure object
    """
    if title is None:
        title = f"Population Impact: {event_name}"

    fig = go.Figure()

    # Assuming df has 'period' column with 'before' and 'after'
    colors = {'before': '#2E86AB', 'after': '#A23B72'}

    for period in ['before', 'after']:
        period_data = df[df['period'] == period]
        fig.add_trace(go.Bar(
            name=period.capitalize(),
            x=period_data['species'],
            y=period_data['count'],
            marker_color=colors.get(period, '#888888')
        ))

    fig.update_layout(
        title=title,
        xaxis_title="Species",
        yaxis_title="Average Population Count",
        barmode='group',
        template='plotly_white'
    )

    return fig


def create_map_visualization(
    df: pd.DataFrame,
    title: Optional[str] = None
) -> go.Figure:
    """
    Create a map visualization for geographic data.

    Args:
        df: DataFrame with columns: latitude, longitude, location, count
        title: Optional custom title

    Returns:
        Plotly Figure object
    """
    if title is None:
        title = "Geographic Distribution"

    fig = px.scatter_mapbox(
        df,
        lat='latitude',
        lon='longitude',
        size='count',
        hover_name='location',
        hover_data={'count': True},
        zoom=7,
        center={"lat": 29.5, "lon": -90.5},  # Louisiana coast
        title=title
    )

    fig.update_layout(
        mapbox_style="open-street-map",
        template='plotly_white'
    )

    return fig
