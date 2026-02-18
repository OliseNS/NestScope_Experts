"""
Chart rendering components
"""

import streamlit as st
import pandas as pd
import plotly.express as px


def _select_chart_columns(df: pd.DataFrame, chart_type: str):
    """
    Intelligently select appropriate columns for chart visualization.

    Args:
        df: DataFrame to visualize
        chart_type: Type of chart ("line" or "bar")

    Returns:
        Tuple of (x_column, y_column) or (None, None) if no suitable columns found
    """
    # Skip coordinate columns - they shouldn't be used for charts
    coord_columns = {'latitude', 'longitude', 'lat', 'lon', 'lng'}
    available_cols = [col for col in df.columns
                      if col.lower() not in coord_columns]

    if len(available_cols) < 2:
        available_cols = list(df.columns)  # Fallback to all columns

    # Identify column types
    numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
    text_cols = df.select_dtypes(include=['object', 'string']).columns.tolist()

    # Filter out coordinate columns from numeric
    numeric_cols = [col for col in numeric_cols if col.lower() not in coord_columns]

    # Find time-based columns (Year, Date, etc.)
    time_cols = [col for col in df.columns
                 if any(keyword in col.lower() for keyword in ['year', 'date', 'time', 'month', 'season'])]

    # Find count/aggregate columns (prioritize these for y-axis)
    count_cols = [col for col in numeric_cols
                  if any(keyword in col.lower() for keyword in
                        ['count', 'total', 'sum', 'avg', 'mean', 'nest', 'bird', 'observation'])]

    x_col = None
    y_col = None

    if chart_type == "line":
        # Line chart: Time-based x-axis, numeric y-axis
        if time_cols:
            x_col = time_cols[0]
            # Prefer count columns, otherwise any numeric column
            if count_cols:
                y_col = count_cols[0]
            elif numeric_cols:
                y_col = numeric_cols[0]
        elif numeric_cols and len(numeric_cols) >= 2:
            # Fallback: use first two numeric columns
            x_col = numeric_cols[0]
            y_col = numeric_cols[1]

    elif chart_type == "bar":
        # Bar chart: Categorical x-axis, numeric y-axis
        # Prefer count columns for y-axis
        if count_cols:
            y_col = count_cols[0]
        elif numeric_cols:
            y_col = numeric_cols[0]

        # For x-axis, prefer text columns (colony names, species, etc.)
        # Avoid columns that look like IDs
        id_keywords = ['id', 'autoid', 'recordid', 'number']
        good_text_cols = [col for col in text_cols
                          if not any(keyword in col.lower() for keyword in id_keywords)]

        if good_text_cols:
            x_col = good_text_cols[0]
        elif text_cols:
            x_col = text_cols[0]
        elif time_cols:
            x_col = time_cols[0]
        elif not y_col:
            # No good categorical column and no y_col yet, use first two columns
            if len(available_cols) >= 2:
                x_col = available_cols[0]
                y_col = available_cols[1]

    # Final fallback: use first two available columns
    if not x_col or not y_col:
        if len(available_cols) >= 2:
            x_col = available_cols[0]
            y_col = available_cols[1]

    return x_col, y_col


def render_chart(df: pd.DataFrame, chart_type: str, key_suffix: str = ""):
    """
    Render a chart with clean dark Claude theme.

    Args:
        df: DataFrame to visualize
        chart_type: Type of chart ("line" or "bar")
        key_suffix: Unique suffix to prevent duplicate IDs
    """
    if len(df.columns) < 2:
        return

    # Intelligently select columns for visualization
    x_col, y_col = _select_chart_columns(df, chart_type)

    if not x_col or not y_col:
        st.info("Unable to determine appropriate columns for visualization.")
        return

    # Clean Dark Template matching Claude theme
    template = {
        'layout': {
            'paper_bgcolor': '#2D2D2D',
            'plot_bgcolor': '#1A1A1A',
            'font': {'color': '#E5E5E5', 'family': 'Inter'},
            'xaxis': {
                'gridcolor': '#404040',
                'linecolor': '#4A4A4A',
                'zerolinecolor': '#4A4A4A',
                'showline': True,
                'color': '#A0A0A0'
            },
            'yaxis': {
                'gridcolor': '#404040',
                'linecolor': '#4A4A4A',
                'zerolinecolor': '#4A4A4A',
                'showline': True,
                'color': '#A0A0A0'
            },
            'title': {'font': {'size': 20, 'color': '#E5E5E5', 'family': 'Inter'}},
            'margin': {'l': 60, 'r': 40, 't': 60, 'b': 60}
        }
    }

    # Create readable labels from column names
    x_label = x_col.replace('_', ' ').replace('Name', '').strip().title()
    y_label = y_col.replace('_', ' ').strip().title()

    if chart_type == "line":
        fig = px.line(
            df,
            x=x_col,
            y=y_col,
            title=f"{y_label} Over Time",
            labels={x_col: x_label, y_col: y_label}
        )
        # Use Claude orange line
        fig.update_traces(line_color='#D97757', line_width=3)
        fig.update_layout(template['layout'])
        st.plotly_chart(fig, use_container_width=True, key=f"line_chart_{key_suffix}")

    elif chart_type == "bar":
        # Limit to top 15 for readability
        chart_df = df.copy()
        if len(chart_df) > 15:
            chart_df = chart_df.nlargest(15, y_col)
            st.caption(f"📊 Showing top 15 out of {len(df)} results")

        fig = px.bar(
            chart_df,
            x=x_col,
            y=y_col,
            title=f"{y_label} by {x_label}",
            labels={x_col: x_label, y_col: y_label}
        )
        # Use Claude orange bars
        fig.update_traces(marker_color='#D97757')
        fig.update_layout(template['layout'])

        # Rotate x-axis labels if they're long
        if chart_df[x_col].astype(str).str.len().max() > 15:
            fig.update_xaxes(tickangle=-45)

        st.plotly_chart(fig, use_container_width=True, key=f"bar_chart_{key_suffix}")
