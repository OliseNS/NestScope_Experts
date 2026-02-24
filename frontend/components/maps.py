"""
Map visualization components
"""

import streamlit as st
import pandas as pd
import folium
from folium.plugins import Fullscreen
from streamlit_folium import st_folium


def render_map(df: pd.DataFrame):
    """
    Render an enhanced Folium map with interactive features.

    Args:
        df: DataFrame containing latitude and longitude columns
    """
    # Find coordinate columns (case-insensitive)
    # Be specific to avoid matching "ColonyName" (which contains "lon")
    lat_col = None
    lon_col = None

    for col in df.columns:
        if col == 'Latitude':
            lat_col = col
        elif col == 'Longitude':
            lon_col = col

    # Fallback to case-insensitive
    if lat_col is None:
        lat_col = next((col for col in df.columns if 'lat' in str(col).lower()), None)
    if lon_col is None:
        lon_col = next((col for col in df.columns if 'lon' in str(col).lower() or 'lng' in str(col).lower()), None)

    if not lat_col or not lon_col:
        st.info("💡 No geographic coordinates found in results.")
        with st.expander("ℹ️ How to get map data"):
            st.markdown("""
            To see results on a map, try queries like:
            - "Show all colonies in Louisiana with their locations"
            - "List bird colonies in Chandeleur Islands"
            - "Where are the brown pelican colonies in 2021?"
            - "Map the locations of sandwich tern nests"
            """)
        return

    try:
        # Clean and validate coordinates
        map_df = df.copy()
        map_df[lat_col] = pd.to_numeric(map_df[lat_col], errors='coerce')
        map_df[lon_col] = pd.to_numeric(map_df[lon_col], errors='coerce')

        # Remove rows with missing coordinates
        map_df = map_df.dropna(subset=[lat_col, lon_col])

        # Filter to valid coordinate ranges (Gulf of Mexico region)
        # Latitude: 24-31°N, Longitude: -98 to -80°W
        valid_mask = (
            (map_df[lat_col] >= 24) & (map_df[lat_col] <= 31) &
            (map_df[lon_col] >= -98) & (map_df[lon_col] <= -80)
        )
        map_df = map_df[valid_mask]

        if map_df.empty:
            st.warning("⚠️ No valid coordinates found in the Gulf region.")
            st.info("Valid coordinates: Latitude 24-31°N, Longitude -98 to -80°W")
            with st.expander("🔍 Debug Info"):
                st.write(f"**Detected columns:**")
                st.write(f"- Latitude column: `{lat_col}`")
                st.write(f"- Longitude column: `{lon_col}`")
                st.write(f"\n**All columns:** {', '.join([f'`{col}`' for col in df.columns])}")
                st.write(f"\n**Data stats:**")
                st.write(f"- Original rows: {len(df)}")
                st.write(f"- After numeric conversion: {len(df.dropna(subset=[lat_col, lon_col]))}")
                st.write(f"\n**Sample coordinates:**")
                st.dataframe(df[[lat_col, lon_col]].head())
            return

        # Calculate center and smart zoom
        avg_lat = map_df[lat_col].mean()
        avg_lon = map_df[lon_col].mean()

        lat_range = map_df[lat_col].max() - map_df[lat_col].min()
        lon_range = map_df[lon_col].max() - map_df[lon_col].min()
        max_range = max(lat_range, lon_range)

        # Smart zoom based on data spread
        if max_range < 0.1:
            zoom = 12
        elif max_range < 0.5:
            zoom = 10
        elif max_range < 2:
            zoom = 8
        else:
            zoom = 7

        # Create map with clear shoreline and vegetation visualization
        m = folium.Map(
            location=[avg_lat, avg_lon],
            zoom_start=zoom,
            tiles='OpenStreetMap',
            control_scale=True
        )

        # Add fullscreen button
        Fullscreen().add_to(m)

        # Color markers by species if available
        species_col = next((col for col in df.columns if 'species' in col.lower()), None)

        species_colors = {}
        unique_species = []
        if species_col:
            unique_species = map_df[species_col].unique()
            color_palette = ['blue', 'red', 'green', 'purple', 'orange', 'darkred',
                             'beige', 'darkblue', 'darkgreen', 'cadetblue',
                             'darkpurple', 'pink', 'lightblue', 'lightgreen']
            for idx, species in enumerate(unique_species):
                species_colors[species] = color_palette[idx % len(color_palette)]

        # Add markers
        for idx, row in map_df.iterrows():
            # Build tooltip with all relevant columns
            tooltip_lines = []
            for col in df.columns:
                if col not in [lat_col, lon_col] and pd.notna(row[col]):
                    val = row[col]
                    if isinstance(val, float):
                        val = f"{val:.2f}" if val < 1000 else f"{val:,.0f}"
                    tooltip_lines.append(f"<b>{col}:</b> {val}")

            tooltip_text = "<br>".join(tooltip_lines) if tooltip_lines else "No data"

            # Color by species if available
            marker_color = 'black'
            if species_col and pd.notna(row[species_col]):
                marker_color = species_colors.get(row[species_col], 'black')

            folium.Marker(
                location=[row[lat_col], row[lon_col]],
                tooltip=folium.Tooltip(tooltip_text, sticky=True),
                popup=folium.Popup(tooltip_text, max_width=300),
                icon=folium.Icon(color=marker_color, icon='info-sign', prefix='glyphicon')
            ).add_to(m)

        # Add legend if multiple species
        if species_col and len(unique_species) > 1:
            legend_html = '''
            <div style="position: fixed; bottom: 50px; right: 50px;
                        width: 220px; background-color: #FFFFFF;
                        border: 2px solid #CCCCCC; z-index: 9999;
                        padding: 12px; border-radius: 10px;
                        box-shadow: 0 4px 12px rgba(0,0,0,0.2);">
                <p style="font-weight: 600; margin-bottom: 10px;
                          border-bottom: 1px solid #CCCCCC; padding-bottom: 8px;
                          color: #333333; font-family: Inter;">
                    Species Legend
                </p>
            '''
            for species in list(unique_species)[:10]:
                color = species_colors[species]
                legend_html += f'<p style="margin: 5px 0; color: #333333; font-family: Inter; font-size: 14px;"><span style="color: {color}; font-size: 18px;">●</span> {species}</p>'

            if len(unique_species) > 10:
                legend_html += f'<p style="margin: 5px 0; font-style: italic; color: #666666; font-family: Inter; font-size: 13px;">+ {len(unique_species) - 10} more...</p>'

            legend_html += '</div>'
            m.get_root().html.add_child(folium.Element(legend_html))

        # Render map
        st_folium(m, width=None, height=600, returned_objects=[])

        # Show summary statistics
        if len(map_df) > 1:
            col1, col2 = st.columns(2)
            with col1:
                st.metric("📍 Locations", len(map_df))
            with col2:
                if species_col:
                    st.metric("🦅 Species", len(unique_species))
                else:
                    st.metric("🗺️ Zoom", zoom)

    except Exception as e:
        st.error(f"❌ Error generating map: {str(e)}")
        with st.expander("🔧 Debug Info"):
            st.write(f"**Latitude column:** {lat_col}")
            st.write(f"**Longitude column:** {lon_col}")
            st.write(f"**DataFrame shape:** {df.shape}")
            st.write(f"**Error:** {str(e)}")
