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
    show_flood_gages: bool = False,
    show_stac_data: bool = False,
    stac_colonies_list: list = None,
    risk_zones: list = None,
    future_projections: list = None
):
    """
    Render an interactive map using Plotly - fast, reliable, native Streamlit.

    Args:
        df: DataFrame with Latitude/Longitude columns
        key: Unique key (not used by Plotly, kept for compatibility)
        height: Map height in pixels
        show_flood_gages: Show NOAA flood stations
        show_stac_data: Highlight STAC colonies
        stac_colonies_list: List of STAC colony names
        risk_zones: Risk zone data for Coastal Risk page
        future_projections: Future projections for Coastal Risk page
    """
    print(f"\n{'='*60}")
    print(f"🗺️  render_map() CALLED (Plotly)")
    print(f"   DataFrame shape: {df.shape}")
    print(f"   Columns: {list(df.columns) if not df.empty else 'EMPTY'}")
    print(f"{'='*60}\n")

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
        # Add dataframe markers (FAST - use Plotly Express)
        if not df.empty and lat_col and lon_col:
            map_df = df.copy()

            # Convert to numeric
            map_df[lat_col] = pd.to_numeric(map_df[lat_col], errors='coerce')
            map_df[lon_col] = pd.to_numeric(map_df[lon_col], errors='coerce')

            # Remove NaN
            map_df = map_df.dropna(subset=[lat_col, lon_col])

            print(f"📍 Creating Plotly Express map with {len(map_df)} points...")

            # Get name column
            name_col = next((col for col in map_df.columns if 'name' in col.lower() and col not in [lat_col, lon_col]), None)

            # Build clean popup text
            popup_texts = []
            for idx, row in map_df.iterrows():
                # Title
                title = str(row[name_col]) if name_col and pd.notna(row[name_col]) else f"Point {idx+1}"

                # Key fields (first 4 non-coordinate columns)
                fields = []
                field_count = 0
                for col in map_df.columns:
                    if col not in [lat_col, lon_col, name_col] and pd.notna(row[col]) and field_count < 4:
                        val = row[col]
                        # Format numbers nicely
                        if isinstance(val, (int, float)):
                            if abs(val) >= 1000:
                                val_str = f"{val:,.0f}"
                            else:
                                val_str = f"{val:.2f}" if val % 1 != 0 else str(int(val))
                        else:
                            val_str = str(val)
                        fields.append(f"<span style='color:#FFFFFF;'><b>{col}:</b> {val_str}</span>")
                        field_count += 1

                # Build popup HTML with light colors for dark background
                popup = f"<b style='font-size:15px;color:#FFFFFF;'>{title}</b><br>"
                if fields:
                    popup += "<br>" + "<br>".join(fields)
                popup += f"<br><br><span style='color:#CCCCCC;font-size:11px;'>📍 {row[lat_col]:.4f}, {row[lon_col]:.4f}</span>"
                popup_texts.append(popup)

            map_df['popup_text'] = popup_texts

            # ULTRA FAST: Use Plotly Express scatter_mapbox
            fig = px.scatter_mapbox(
                map_df,
                lat=lat_col,
                lon=lon_col,
                hover_name='popup_text',
                color_discrete_sequence=['#D97757'],  # Claude orange
                zoom=6,
                height=height
            )

            # Visible circle markers
            fig.update_traces(
                marker=dict(
                    size=18,
                    opacity=0.9
                ),
                hovertemplate='%{hovertext}<extra></extra>'
            )

            center_lat = map_df[lat_col].mean()
            center_lon = map_df[lon_col].mean()
            print(f"✅ Map created, centered at: {center_lat:.4f}, {center_lon:.4f}")

        elif risk_zones:
            # Risk zones for Coastal Risk page (FAST)
            risk_df = pd.DataFrame([{
                'lat': z['latitude'],
                'lon': z['longitude'],
                'Colony': z['colony_name'],
                'Risk Level': z['risk_level'],
                'Risk Score': z['risk_score'],
                'Birds': z.get('birds', 0)
            } for z in risk_zones])

            # Ensure all expected levels have colors
            color_map = {
                'CRITICAL': '#8B0000',  # Dark Red
                'HIGH': '#FF0000',      # Red
                'MODERATE': '#FFA500',  # Orange
                'LOW': '#2E8B57'        # Sea Green
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
                size_max=20,
                zoom=6,
                height=height
            )

            # Visible circle markers for risk zones
            fig.update_traces(
                marker=dict(opacity=0.8, allowoverlap=True),
                selector=dict(type='scattermapbox')
            )

            center_lat = risk_df['lat'].mean()
            center_lon = risk_df['lon'].mean()

        elif future_projections:
            # Future projections for Coastal Risk page (FAST)
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
                color_discrete_map={'submerged': '#808080', 'at_risk': '#FF8C00', 'stable': '#4CAF50'},
                zoom=6,
                height=height
            )

            # Visible circle markers for projections
            fig.update_traces(
                marker=dict(size=18, opacity=0.9)
            )

            center_lat = proj_df['lat'].mean()
            center_lon = proj_df['lon'].mean()

        else:
            # Empty map - just show Gulf Coast
            center_lat, center_lon = 29.5, -89.5
            fig = go.Figure()
            fig.update_layout(
                mapbox=dict(
                    style='open-street-map',
                    center=dict(lat=center_lat, lon=center_lon),
                    zoom=6
                ),
                margin=dict(l=0, r=0, t=0, b=0),
                height=height
            )

        # Final map styling - street view only
        fig.update_layout(
            mapbox_style='open-street-map',
            margin=dict(l=0, r=0, t=0, b=0),
            height=height,
            showlegend=False
        )

        # Display with Plotly (WITH FULLSCREEN)
        print(f"🗺️  Rendering Plotly map...")
        st.plotly_chart(
            fig,
            use_container_width=True,
            config={
                'displayModeBar': True,  # Show toolbar for fullscreen
                'modeBarButtonsToAdd': ['toImage'],
                'modeBarButtonsToRemove': ['pan2d', 'lasso2d', 'select2d'],
                'scrollZoom': True,
                'displaylogo': False
            },
            key=key
        )
        print(f"✅ Plotly map displayed!")

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
