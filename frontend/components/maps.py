"""
Plotly-based map visualization - reliable, fast, no iframe issues.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


def render_map(
    df: pd.DataFrame,
    key: str = None,
    height: int = 500,
    risk_zones: list = None,
    future_projections: list = None,
    show_stac_data: bool = False,
    stac_colonies_list: list = None
):
    """
    Render an interactive map using Plotly - fast, reliable, native Streamlit.

    Args:
        df: DataFrame with Latitude/Longitude columns
        key: Unique key for Streamlit
        height: Map height in pixels
        risk_zones: Risk zone data for Coastal Risk page
        future_projections: Future projections for Coastal Risk page
        show_stac_data: Highlight STAC colonies
        stac_colonies_list: List of STAC colony names
    """
    # Find coordinate columns
    lat_col = None
    lon_col = None

    if not df.empty:
        for col in df.columns:
            col_lower = str(col).lower()
            if 'latitude' in col_lower and not lat_col:
                lat_col = col
            if 'longitude' in col_lower and not lon_col:
                lon_col = col

    # If no coordinates in df, check if we have other data to map
    has_other_data = risk_zones or future_projections

    if (not lat_col or not lon_col) and not has_other_data:
        st.info("💡 **No location coordinates found.** Results don't contain latitude/longitude data.")
        return

    try:
        if risk_zones:
            # Risk zones for Coastal Risk page
            risk_df = pd.DataFrame([{
                'lat': z['latitude'],
                'lon': z['longitude'],
                'Colony': z['colony_name'],
                'Risk Level': z['risk_level'],
                'Risk Score': z['risk_score'],
                'Birds': z.get('bird_count', 0)
            } for z in risk_zones])

            # Standard Red to Green color map
            color_map = {
                'CRITICAL': '#FF0000',  # Pure Red
                'HIGH': '#FF8C00',      # Dark Orange
                'MODERATE': '#FFD700',  # Gold/Yellow
                'LOW': '#00FF00'        # Pure Green
            }

            fig = px.scatter_mapbox(
                risk_df,
                lat='lat',
                lon='lon',
                hover_name='Colony',
                hover_data={
                    'lat': False,
                    'lon': False,
                    'Risk Level': True,
                    'Risk Score': ':.1f',
                    'Birds': ':,'
                },
                color='Risk Level',
                color_discrete_map=color_map,
                size='Risk Score',
                size_max=10,  # Small size like typical map markers
                zoom=7,
                height=height,
                mapbox_style="open-street-map"
            )
            fig.update_layout(showlegend=True, legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01, bgcolor="rgba(0,0,0,0.5)"))

        elif future_projections:
            proj_df = pd.DataFrame([{
                'lat': p['latitude'],
                'lon': p['longitude'],
                'Colony': p['colony_name'],
                'Status': p['status']
            } for p in future_projections])

            fig = px.scatter_mapbox(
                proj_df,
                lat='lat',
                lon='lon',
                hover_name='Colony',
                hover_data=['Status'],
                color='Status',
                color_discrete_map={'submerged': '#FF0000', 'at_risk': '#FFA500', 'stable': '#00FF00'},
                zoom=7,
                height=height,
                mapbox_style="open-street-map"
            )

        else:
            # Standard dataframe mapping with coordinate validation
            # Validate that coordinates are numeric and not concatenated strings
            import numpy as np

            # Convert to numeric, coercing errors to NaN
            df_map = df.copy()
            df_map[lat_col] = pd.to_numeric(df_map[lat_col], errors='coerce')
            df_map[lon_col] = pd.to_numeric(df_map[lon_col], errors='coerce')

            # Filter out invalid coordinates
            valid_mask = df_map[lat_col].notna() & df_map[lon_col].notna()
            valid_mask &= (df_map[lat_col].abs() <= 90)  # Valid latitude range
            valid_mask &= (df_map[lon_col].abs() <= 180)  # Valid longitude range
            df_map = df_map[valid_mask]

            if len(df_map) == 0:
                st.error("❌ **Coordinate validation failed**: All coordinates are invalid or out of range.")
                st.info("Coordinates must be numeric values (Latitude: -90 to 90, Longitude: -180 to 180)")
                return

            if len(df_map) < len(df):
                st.warning(f"⚠️ {len(df) - len(df_map)} rows had invalid coordinates and were filtered out.")

            # Create hover text with colony names if available
            if 'ColonyName' in df_map.columns:
                hover_name = 'ColonyName'
                hover_data = {lat_col: ':.4f', lon_col: ':.4f'}
            else:
                hover_name = None
                hover_data = None

            # Add a constant size column for all markers
            df_map['marker_size'] = 1  # Very small constant size (like Google Maps pins)

            fig = px.scatter_mapbox(
                df_map,
                lat=lat_col,
                lon=lon_col,
                hover_name=hover_name,
                hover_data=hover_data,
                zoom=7,
                height=height,
                size='marker_size',  # Use constant size column
                size_max=8,  # Small maximum marker size (like typical map pins)
                mapbox_style="open-street-map",
                color_discrete_sequence=['#D97757']
            )

            # Enhance marker visibility
            fig.update_traces(
                marker=dict(
                    opacity=0.9,
                    sizemode='diameter'  # Use diameter for consistent sizing
                )
            )

        # Ensure interactivity
        fig.update_layout(
            margin=dict(l=0, r=0, t=0, b=0),
            mapbox=dict(zoom=7)
        )

        st.plotly_chart(
            fig, 
            use_container_width=True, 
            key=key,
            config={
                'scrollZoom': True,
                'displayModeBar': True,
                'modeBarButtonsToAdd': ['toImage'],
                'displaylogo': False
            }
        )

    except Exception as e:
        st.error(f"Map error: {e}")

    except Exception as e:
        print(f"❌ Map error: {e}")
        import traceback
        traceback.print_exc()
        st.error(f"Map error: {e}")


def render_simple_map(lat, lon, label=None, height=300, key=None):
    """Render a single location map - FAST."""
    fig = px.scatter_mapbox(
        pd.DataFrame({'lat': [lat], 'lon': [lon], 'name': [label or 'Location']}),
        lat='lat',
        lon='lon',
        hover_name='name',
        color_discrete_sequence=['#D97757'],
        zoom=12,
        height=height
    )

    fig.update_layout(
        mapbox_style='open-street-map',
        margin=dict(l=0, r=0, t=0, b=0),
        showlegend=False
    )

    st.plotly_chart(
        fig,
        use_container_width=True,
        config={'displayModeBar': False},
        key=key
    )
