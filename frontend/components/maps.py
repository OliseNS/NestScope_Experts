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
from folium import plugins
from folium.plugins import MarkerCluster, FastMarkerCluster
from streamlit_folium import st_folium


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

    This ensures consistent coloring across multiple queries - the same species
    always gets the same color within a single map view.

    Args:
        species_list: List of unique species names
        species_name: The species to get color for

    Returns:
        Hex color string (e.g., '#0074D9')
    """
    try:
        idx = list(species_list).index(species_name)
        return SPECIES_COLORS.get(idx % len(SPECIES_COLORS), '#0074D9')
    except (ValueError, AttributeError):
        return '#0074D9'  # Default blue


def render_map(df: pd.DataFrame, key: str = None):
    """
    Render an interactive map using Folium with performance optimizations for large datasets.

    Automatically adapts rendering strategy based on dataset size:
    - < 200 markers: Individual CircleMarkers (full interactivity)
    - 200-500 markers: MarkerCluster (balanced performance)
    - > 500 markers: FastMarkerCluster (maximum speed)

    Performance Optimizations:
    - Coordinates rounded to 5 decimal places (~1 meter precision)
    - Minimal HTML whitespace to reduce file size
    - Clustering prevents browser overload with large datasets

    Key Features:
    - Two basemap tiles (Street Map, Satellite)
    - Color-coded markers by species
    - Interactive popups with colony details
    - Automatic zoom to fit all markers
    - Species legend
    - Fullscreen mode

    Args:
        df: DataFrame containing latitude and longitude columns
        key: Optional unique key for this map instance (for Streamlit caching)
    """
    # ========================================================================
    # STEP 1: Find coordinate columns (case-insensitive search)
    # ========================================================================
    lat_col = None
    lon_col = None

    # First try exact matches (our database uses these names)
    for col in df.columns:
        if col == 'Latitude':
            lat_col = col
        elif col == 'Longitude':
            lon_col = col

    # Fallback to case-insensitive search (in case column names vary)
    if lat_col is None:
        lat_col = next((col for col in df.columns if 'lat' in str(col).lower()), None)
    if lon_col is None:
        lon_col = next((col for col in df.columns if 'lon' in str(col).lower() or 'lng' in str(col).lower()), None)

    # If no coordinates found, show helpful message
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
        # ====================================================================
        # STEP 2: Clean and validate coordinate data
        # ====================================================================
        map_df = df.copy()

        # Convert to numeric, marking invalid values as NaN
        map_df[lat_col] = pd.to_numeric(map_df[lat_col], errors='coerce')
        map_df[lon_col] = pd.to_numeric(map_df[lon_col], errors='coerce')

        # Remove rows with missing coordinates
        map_df = map_df.dropna(subset=[lat_col, lon_col])

        # Filter to valid Gulf of Mexico coordinate ranges
        # Latitude: 24°N to 31°N (covers TX, LA, MS, AL, FL Gulf Coast)
        # Longitude: -98°W to -80°W (western Texas to southern Florida)
        valid_mask = (
            (map_df[lat_col] >= 24) & (map_df[lat_col] <= 31) &
            (map_df[lon_col] >= -98) & (map_df[lon_col] <= -80)
        )
        map_df = map_df[valid_mask]

        if map_df.empty:
            st.warning("⚠️ No valid coordinates found in the Gulf region.")
            st.info("Valid coordinates: Latitude 24-31°N, Longitude -98 to -80°W")
            return

        # Limit map rendering for extremely large datasets
        if len(map_df) > 2000:
            st.warning(f"⚠️ Dataset has {len(map_df):,} locations - too many to render on a map efficiently.")
            st.info("💡 **Tip:** Refine your query to show fewer locations (e.g., filter by year, species, or colony).")
            with st.expander("📊 View data summary instead"):
                st.dataframe(map_df[[lat_col, lon_col] + ([name_col] if name_col else [])].head(100), use_container_width=True)
                st.caption(f"Showing first 100 of {len(map_df):,} locations")
            return

        # ====================================================================
        # STEP 3: Calculate map center and bounds
        # ====================================================================
        center_lat = map_df[lat_col].mean()
        center_lon = map_df[lon_col].mean()

        # Create bounds for fit_bounds (automatically zooms to show all markers)
        bounds = [
            [map_df[lat_col].min(), map_df[lon_col].min()],  # Southwest corner
            [map_df[lat_col].max(), map_df[lon_col].max()]   # Northeast corner
        ]

        # ====================================================================
        # STEP 4: Create base map with vegetation-friendly tile layer
        # ====================================================================
        # Start with center coordinates (will be adjusted by fit_bounds)
        m = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=7,  # Will be overridden by fit_bounds
            tiles=None,     # We'll add custom tiles below
            prefer_canvas=True  # Better performance for many markers
        )

        # Add two tile layer options (optimized for performance)
        # Users can switch between these using the layer control

        # Option 1: OpenStreetMap (default) - Shows roads, cities, natural features
        # This is lightweight and loads quickly
        folium.TileLayer(
            tiles='OpenStreetMap',
            name='Street Map',
            overlay=False,
            control=True,
            show=True,  # This is the default layer
            attr='OpenStreetMap contributors'
        ).add_to(m)

        # Option 2: Satellite imagery - Perfect for bird habitat visualization
        # Shows actual aerial photography of the Gulf Coast
        folium.TileLayer(
            tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
            name='Satellite',
            overlay=False,
            control=True,
            attr='Esri'
        ).add_to(m)

        # ====================================================================
        # STEP 5: Optimize coordinates for performance
        # ====================================================================
        # Round coordinates to 5 decimal places (~1 meter precision)
        # This reduces HTML file size significantly for large datasets
        # 5 decimals = ~1.1 meter precision, which is more than enough for colony locations
        map_df[lat_col] = map_df[lat_col].round(5)
        map_df[lon_col] = map_df[lon_col].round(5)

        # ====================================================================
        # STEP 6: Check for species column for color-coding
        # ====================================================================
        species_col = next((col for col in df.columns if 'species' in col.lower()), None)
        unique_species = []

        if species_col and species_col in map_df.columns:
            unique_species = sorted(map_df[species_col].dropna().unique())

        # Find colony name column for popup labels
        name_col = next((col for col in df.columns if 'name' in col.lower() and col not in [lat_col, lon_col]), None)

        # ====================================================================
        # STEP 7: Determine clustering strategy based on dataset size
        # ====================================================================
        num_markers = len(map_df)
        use_clustering = num_markers > 200  # Use clustering for large datasets

        # Performance thresholds:
        # < 200 markers: Individual markers (fast, full interactivity)
        # 200-500 markers: Standard MarkerCluster (good balance)
        # > 500 markers: FastMarkerCluster (optimized for speed)

        if use_clustering:
            if num_markers > 500:
                # FastMarkerCluster for very large datasets
                # This is the fastest clustering method
                marker_cluster = FastMarkerCluster(data=[]).add_to(m)
                st.info(f"📊 Displaying {num_markers} locations using fast clustering for optimal performance. Zoom in to see individual colonies.")
            else:
                # Standard MarkerCluster for medium datasets
                # Provides better customization and smoother transitions
                marker_cluster = MarkerCluster(
                    name='Colony Markers',
                    overlay=True,
                    control=False,
                    icon_create_function=None
                ).add_to(m)
                st.info(f"📊 Displaying {num_markers} locations with clustering. Zoom in to see individual colonies.")

        # ====================================================================
        # STEP 8: Add markers for each colony location
        # ====================================================================
        for idx, row in map_df.iterrows():
            lat = row[lat_col]
            lon = row[lon_col]

            # Determine marker color based on species
            if species_col and species_col in row and pd.notna(row[species_col]):
                color = get_species_color(unique_species, row[species_col])
            else:
                color = '#0074D9'  # Default blue

            # Build compact popup content (minimized for performance)
            # Reduce whitespace and use shorter HTML to minimize file size
            popup_html = "<div style='font-family:sans-serif;min-width:200px'>"

            # Add colony name if available
            if name_col and name_col in row and pd.notna(row[name_col]):
                popup_html += f"<h4 style='margin:0 0 8px 0;color:#2C3E50'>{row[name_col]}</h4>"

            # Add species if available
            if species_col and species_col in row and pd.notna(row[species_col]):
                popup_html += f"<p style='margin:4px 0;color:{color};font-weight:bold'>🦅 {row[species_col]}</p>"

            # Add other relevant data (exclude coordinates and ID columns)
            exclude_cols = [lat_col, lon_col, name_col, species_col, 'id', 'ID', 'Id']
            data_cols = [col for col in row.index if col not in exclude_cols and pd.notna(row[col])]

            for col in data_cols[:3]:  # Limit to 3 fields for performance
                value = row[col]
                # Format numbers nicely
                if isinstance(value, (int, float)):
                    if value > 1000:
                        value = f"{value:,.0f}"
                    else:
                        value = f"{value:g}"
                popup_html += f"<p style='margin:2px 0;font-size:0.9em'><b>{col}:</b> {value}</p>"

            popup_html += f"<p style='margin:8px 0 0 0;font-size:0.8em;color:#7F8C8D'>📍 {lat:.4f},{lon:.4f}</p>"
            popup_html += "</div>"

            # Create circle marker (better for clustered points than standard markers)
            marker = folium.CircleMarker(
                location=[lat, lon],
                radius=8,                    # Circle size in pixels
                color='white',               # Border color
                weight=2,                    # Border width
                fill=True,
                fillColor=color,            # Fill color based on species
                fillOpacity=0.7,            # Slight transparency
                popup=folium.Popup(popup_html, max_width=300),
                tooltip=row[name_col] if name_col and name_col in row and pd.notna(row[name_col]) else f"Colony at {lat:.2f},{lon:.2f}"
            )

            # Add marker to cluster or map depending on dataset size
            if use_clustering:
                marker.add_to(marker_cluster)
            else:
                marker.add_to(m)

        # ====================================================================
        # STEP 9: Add layer control and fit bounds
        # ====================================================================
        # Add control to switch between tile layers
        folium.LayerControl(position='topright').add_to(m)

        # Zoom map to show all markers (with some padding)
        m.fit_bounds(bounds, padding=(30, 30))

        # Add fullscreen button
        plugins.Fullscreen(
            position='topright',
            title='Enter fullscreen',
            title_cancel='Exit fullscreen',
            force_separate_button=True
        ).add_to(m)

        # ====================================================================
        # STEP 10: Render the map in Streamlit
        # ====================================================================
        # The returned_objects parameter captures user interactions
        # Width and height set to use full container width
        st_folium(
            m,
            width=None,      # Use full container width
            height=500,      # Fixed height in pixels
            returned_objects=[],
            key=key
        )

        # ====================================================================
        # STEP 11: Show summary statistics and legend
        # ====================================================================
        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("📍 Locations", len(map_df))

        with col2:
            if species_col and len(unique_species) > 0:
                st.metric("🦅 Species", len(unique_species))
            else:
                lat_range = map_df[lat_col].max() - map_df[lat_col].min()
                lon_range = map_df[lon_col].max() - map_df[lon_col].min()
                max_range = max(lat_range, lon_range)
                st.metric("📐 Area (°)", f"{max_range:.2f}")

        with col3:
            st.metric("🌊 Region", "Gulf Coast")

        # Show species legend if we have multiple species
        if species_col and len(unique_species) > 1:
            with st.expander("🎨 Species Legend", expanded=False):
                legend_cols = st.columns(2)
                for idx, species in enumerate(unique_species[:20]):  # Limit to 20 for display
                    color = get_species_color(unique_species, species)
                    with legend_cols[idx % 2]:
                        st.markdown(
                            f'<span style="color: {color}; font-size: 1.2em;">●</span> {species}',
                            unsafe_allow_html=True
                        )

                if len(unique_species) > 20:
                    st.caption(f"+ {len(unique_species) - 20} more species")

        # Show helpful tip for interaction
        if use_clustering:
            st.info("💡 **Tip:** Click cluster numbers to zoom in and reveal individual colonies. Click markers for details. Use the layer control (top right) to switch map styles.")
        else:
            st.info("💡 **Tip:** Click markers for details. Use the layer control (top right) to switch map styles. Scroll to zoom, drag to pan.")

    except Exception as e:
        st.error(f"❌ Error generating map: {str(e)}")
        with st.expander("🔧 Debug Info"):
            st.write(f"**Latitude column:** {lat_col}")
            st.write(f"**Longitude column:** {lon_col}")
            st.write(f"**DataFrame shape:** {df.shape}")
            st.write(f"**Error:** {str(e)}")
            import traceback
            st.code(traceback.format_exc())
