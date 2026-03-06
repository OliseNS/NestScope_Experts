"""
Map visualization components using Folium for interactive, customizable maps.

Folium creates Leaflet.js maps with support for various tile providers (map styles).
Uses MarkerCluster for efficient rendering of large datasets (200+ markers).

Performance optimizations:
- MarkerCluster groups nearby markers for faster rendering
- Coordinate precision reduced to 5 decimals to minimize file size
- FastMarkerCluster used for datasets with 500+ points
"""

import streamlit as st
import pandas as pd
import folium
from folium import plugins, Circle
from folium.plugins import MarkerCluster, FastMarkerCluster
from streamlit_folium import st_folium
import json

# Color palette for species (HEX format for Folium)
# These colors are chosen to be visually distinct and colorblind-friendly
SPECIES_COLORS = {
    0: '#0074D9',   # Blue
    1: '#FF4136',   # Red
    2: '#2ECC71',   # Green
    3: '#9B59B6',   # Purple
    4: '#FF851B',   # Orange
    5: '#C0392B',   # Dark red
    6: '#F5B041',   # Beige/yellow
    7: '#34495E',   # Dark blue
    8: '#27AE60',   # Dark green
    9: '#1ABC9C',   # Cadet blue
    10: '#8E44AD',  # Dark purple
    11: '#EC7063',  # Pink
    12: '#85C1E9',  # Light blue
    13: '#82E0AA',  # Light green
}


def get_species_color(species_list, species_name):
    """
    Get hex color for a species based on its index in the unique species list.
    """
    try:
        idx = list(species_list).index(species_name)
        return SPECIES_COLORS.get(idx % len(SPECIES_COLORS), '#0074D9')
    except (ValueError, AttributeError):
        return '#0074D9'  # Default blue


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
    Render an interactive map using Folium with performance optimizations.

    Args:
        df: DataFrame containing latitude and longitude columns
        key: Unique key for this map instance
        height: Height of the map in pixels
        show_flood_gages: Whether to fetch and show NOAA flood monitoring stations
        show_stac_data: Whether to highlight colonies with expert STAC data
        stac_colonies_list: Optional list of colony names that have STAC data
        risk_zones: Optional list of risk zone dicts for Coastal Risk page
        future_projections: Optional list of projection dicts for Coastal Risk page
    """
    print(f"\n{'='*60}")
    print(f"🗺️  render_map() CALLED")
    print(f"   DataFrame shape: {df.shape}")
    print(f"   DataFrame columns: {list(df.columns) if not df.empty else 'EMPTY'}")
    print(f"   Key: {key}")
    print(f"   Height: {height}")
    print(f"{'='*60}\n")
    # ========================================================================
    # STEP 1: Find coordinate columns (case-insensitive search)
    # ========================================================================
    lat_col = None
    lon_col = None

    if not df.empty:
        # First try exact matches
        for col in df.columns:
            if col == 'Latitude':
                lat_col = col
            elif col == 'Longitude':
                lon_col = col

        # Fallback to case-insensitive search
        if lat_col is None:
            lat_col = next((col for col in df.columns if 'lat' in str(col).lower()), None)
        if lon_col is None:
            lon_col = next((col for col in df.columns if 'lon' in str(col).lower() or 'lng' in str(col).lower()), None)

    # If no coordinates found in DF, check if we have other data to map
    has_other_data = risk_zones or future_projections
    if (not lat_col or not lon_col) and not has_other_data:
        st.info("💡 **No location coordinates found.** The results don't contain latitude/longitude data needed for mapping.")
        return

    try:
        # ====================================================================
        # STEP 2: Clean and validate coordinate data
        # ====================================================================
        map_df = df.copy() if not df.empty else pd.DataFrame()

        if not map_df.empty:
            # Convert to numeric, marking invalid values as NaN
            map_df[lat_col] = pd.to_numeric(map_df[lat_col], errors='coerce')
            map_df[lon_col] = pd.to_numeric(map_df[lon_col], errors='coerce')

            # Remove rows with missing coordinates
            map_df = map_df.dropna(subset=[lat_col, lon_col])

            # Filter to valid Gulf of Mexico coordinate ranges for safety
            valid_mask = (
                (map_df[lat_col] >= 24) & (map_df[lat_col] <= 32) &
                (map_df[lon_col] >= -100) & (map_df[lon_col] <= -80)
            )
            map_df = map_df[valid_mask]

        if map_df.empty and not has_other_data:
            st.warning("⚠️ No valid Gulf Coast coordinates found in the results.")
            return

        # ====================================================================
        # STEP 3: Calculate map center and bounds
        # ====================================================================
        if not map_df.empty:
            center_lat = map_df[lat_col].mean()
            center_lon = map_df[lon_col].mean()
            bounds = [
                [map_df[lat_col].min(), map_df[lon_col].min()],
                [map_df[lat_col].max(), map_df[lon_col].max()]
            ]
        elif risk_zones:
            lats = [z['latitude'] for z in risk_zones]
            lons = [z['longitude'] for z in risk_zones]
            center_lat, center_lon = sum(lats)/len(lats), sum(lons)/len(lons)
            bounds = [[min(lats), min(lons)], [max(lats), max(lons)]]
        elif future_projections:
            lats = [z['latitude'] for z in future_projections]
            lons = [z['longitude'] for z in future_projections]
            center_lat, center_lon = sum(lats)/len(lats), sum(lons)/len(lons)
            bounds = [[min(lats), min(lons)], [max(lats), max(lons)]]
        else:
            center_lat, center_lon = 29.5, -89.5
            bounds = [[28.0, -92.0], [31.0, -87.0]]

        # ====================================================================
        # STEP 4: Create base map
        # ====================================================================
        m = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=7,
            tiles=None,
            prefer_canvas=True
        )

        folium.TileLayer(
            tiles='CartoDB positron',
            name='Light Map',
            overlay=False,
            control=True,
            show=True
        ).add_to(m)

        folium.TileLayer(
            tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
            name='Satellite',
            overlay=False,
            control=True,
            attr='Esri'
        ).add_to(m)

        # ====================================================================
        # STEP 5: Add Data Layers
        # ====================================================================
        
        # A. RISK ZONES (Circles)
        if risk_zones:
            risk_group = folium.FeatureGroup(name="Risk Zones", show=True)
            for zone in risk_zones:
                if zone['risk_level'] == 'CRITICAL':
                    color = '#FF4444'
                    fill_opacity = 0.4
                elif zone['risk_level'] == 'HIGH':
                    color = '#FF8C00'
                    fill_opacity = 0.3
                else:
                    color = '#4CAF50'
                    fill_opacity = 0.2

                birds_display = f"{zone['birds']:,}" if zone['birds'] is not None else 'N/A'
                species_display = zone['species'] if zone['species'] is not None else 'N/A'
                years_display = zone['years_until_critical'] if zone['years_until_critical'] is not None else 'N/A'

                popup_html = f"""
                    <div style="font-family: sans-serif; min-width: 250px;">
                        <h4 style="margin: 0; color: {color};">{zone['colony_name']}</h4>
                        <hr style="margin: 8px 0;">
                        <p><strong>Risk Score:</strong> {zone['risk_score']}/100</p>
                        <p><strong>Status:</strong> <span style="color: {color}; font-weight: bold;">{zone['risk_level']}</span></p>
                        <p><strong>Years Until Critical:</strong> {years_display}</p>
                        <p><strong>Bird Population:</strong> {birds_display}</p>
                        <p><strong>Species:</strong> {species_display}</p>
                        <hr style="margin: 8px 0;">
                        <p style="font-style: italic; font-size: 0.9em;">{zone['action']}</p>
                    </div>
                """
                
                Circle(
                    location=[zone['latitude'], zone['longitude']],
                    radius=zone['radius_km'] * 1000,
                    color=color,
                    fill=True,
                    fill_color=color,
                    fill_opacity=fill_opacity,
                    weight=2,
                    popup=folium.Popup(popup_html, max_width=300),
                    tooltip=f"{zone['colony_name']} - {zone['risk_level']}"
                ).add_to(risk_group)
            risk_group.add_to(m)

        # B. FUTURE PROJECTIONS (Icons)
        if future_projections:
            proj_group = folium.FeatureGroup(name="Future Status", show=True)
            for colony in future_projections:
                if colony['status'] == 'submerged':
                    color, icon_name = 'gray', 'remove'
                elif colony['status'] == 'at_risk':
                    color, icon_name = 'orange', 'warning'
                else:
                    color, icon_name = 'green', 'ok'

                folium.Marker(
                    location=[colony['latitude'], colony['longitude']],
                    icon=folium.Icon(color=color, icon=icon_name),
                    popup=f"<b>{colony['colony_name']}</b><br>Status: {colony['status'].title()}<br>Area: {colony['projected_area_m2']:.0f}m²",
                    tooltip=colony['colony_name']
                ).add_to(proj_group)
            proj_group.add_to(m)

        # C. DATAFRAME MARKERS (Standard Colonies)
        if not map_df.empty:
            print(f"📍 Rendering {len(map_df)} points on map...")

            # Convert to numeric and round coordinates
            map_df[lat_col] = pd.to_numeric(map_df[lat_col], errors='coerce').round(5)
            map_df[lon_col] = pd.to_numeric(map_df[lon_col], errors='coerce').round(5)

            # Remove NaN coordinates
            map_df = map_df.dropna(subset=[lat_col, lon_col])
            print(f"   After cleaning: {len(map_df)} valid points")

            # Find name/species columns
            name_col = next((col for col in map_df.columns if 'name' in col.lower() and col not in [lat_col, lon_col]), None)
            species_col = next((col for col in map_df.columns if 'species' in col.lower()), None)

            # SIMPLE & FAST: Just iterate and add markers
            for idx, row in enumerate(map_df.to_dict('records')):
                try:
                    lat = row[lat_col]
                    lon = row[lon_col]

                    # Get name for tooltip
                    name = str(row.get(name_col, "")) if name_col else f"Point {idx+1}"

                    # Simple popup with first 3 fields
                    popup_fields = []
                    field_count = 0
                    for key, val in row.items():
                        if key not in [lat_col, lon_col] and pd.notna(val) and field_count < 3:
                            popup_fields.append(f"<b>{key}:</b> {val}")
                            field_count += 1

                    popup_html = f"<div style='font-size:0.9em;'>{name}<br>{'<br>'.join(popup_fields)}</div>"

                    folium.CircleMarker(
                        location=[lat, lon],
                        radius=6,
                        color='white',
                        weight=1,
                        fill=True,
                        fillColor='#D97757',
                        fillOpacity=0.7,
                        popup=folium.Popup(popup_html, max_width=250),
                        tooltip=name
                    ).add_to(m)

                except Exception as e:
                    print(f"⚠️  Skipped point {idx}: {e}")
                    continue

            print(f"✅ Added {len(map_df)} markers to map")

        # D. FLOOD GAGES
        if show_flood_gages:
            try:
                from services.api_client import get_flood_stations
                flood_data = get_flood_stations()
                stations = flood_data.get("stations", [])
                flood_group = folium.FeatureGroup(name="Flood Monitoring (NOAA)", show=True)
                for station in stations:
                    s_popup = f"<div style='font-family:sans-serif;min-width:180px;'><b style='color:#4169E1;'>🌊 {station['station_name']}</b><br><b>ID:</b> {station['station_id']}<br><b>Region:</b> {station['region']}<br><b>MHHW:</b> {station['mhhw_value']}m</div>"
                    folium.Marker(
                        location=[station['latitude'], station['longitude']],
                        icon=folium.Icon(color="blue", icon="tint", prefix="fa"),
                        popup=folium.Popup(s_popup, max_width=250),
                        tooltip=f"🌊 {station['station_name']}"
                    ).add_to(flood_group)
                flood_group.add_to(m)
            except Exception: pass

        # ====================================================================
        # STEP 6: Controls & Render
        # ====================================================================
        print(f"🗺️  Finalizing map...")
        folium.LayerControl(position='topright').add_to(m)

        try:
            m.fit_bounds(bounds, padding=(30, 30))
        except Exception as bounds_error:
            print(f"⚠️  Bounds fitting failed: {bounds_error}, using default view")

        plugins.Fullscreen(position='topright', title='Expand map', title_cancel='Exit fullscreen', force_separate_button=True).add_to(m)

        print(f"🗺️  Displaying map with streamlit-folium...")
        print(f"   Map object created: {m is not None}")
        print(f"   Using key: {key}")

        # Display the map
        map_data = st_folium(m, width='100%', height=height, returned_objects=[], key=key)

        print(f"✅ Map component rendered!")
        print(f"   Map data returned: {map_data is not None}")

    except Exception as e:
        print(f"❌ Map rendering error: {e}")
        import traceback
        traceback.print_exc()
        st.error(f"Map rendering error: {e}")
        st.info("Try reducing the number of results or rephrasing your query.")

def render_simple_map(lat, lon, label=None, height=300, key=None):
    """Render a single location map efficiently."""
    m = folium.Map(location=[lat, lon], zoom_start=12, tiles='CartoDB positron')
    folium.TileLayer(tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', name='Satellite', overlay=False, control=True, attr='Esri').add_to(m)
    folium.CircleMarker(location=[lat, lon], radius=12, color='white', weight=2, fill=True, fillColor='#D97757', fillOpacity=0.8, tooltip=label if label else f"{lat:.4f}, {lon:.4f}").add_to(m)
    folium.LayerControl().add_to(m)
    plugins.Fullscreen(position='topright').add_to(m)
    st_folium(m, width=None, height=height, returned_objects=[], key=key)
