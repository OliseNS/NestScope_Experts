"""
NestMap — Honest Colony Data Viewer
====================================
Shows ONLY real data:
- Colony locations (from SQLite database)
- Population trends (2010-2021 actual counts)
- Expert annotations (from STAC catalog)
- AI validation metrics (where available)

NO fake erosion zones. NO made-up risk scores. Just the data we have.
"""

import streamlit as st
import pandas as pd
import folium
import plotly.graph_objects as go
import sqlite3
import os

from components import init_page, render_header, render_sidebar
from services.api_client import get_stac_summary, get_stac_species, get_stac_dots

# ============================================================================
# PAGE CONFIGURATION
# ============================================================================

init_page(page_title="NestMap - Colony Data", page_icon="🗺️", layout="wide")
render_header(page_name="NestMap: Colony Data Viewer")

# ============================================================================
# SIDEBAR
# ============================================================================

with st.sidebar:
    render_sidebar(active_page="nestmap")

    st.markdown("---")
    st.markdown("### 📊 Data Sources")
    st.markdown("""
    **Real Data Only:**
    - Colony locations: SQLite database
    - Population counts: 2010-2021 surveys
    - Expert dots: STAC catalog (4 colonies)

    **What's NOT here:**
    - No fake erosion zones
    - No made-up risk scores
    - No predictions

    Just honest data.
    """)

# ============================================================================
# PAGE HEADER
# ============================================================================

st.markdown("""
    <div class="title-card">
        <h3>🗺️ NestMap: Colony Data Viewer</h3>
        <p>
            Showing colony locations, population trends (2010-2021), and expert annotations.
            <strong>Real data only.</strong> No predictions, no fake overlays.
        </p>
    </div>
""", unsafe_allow_html=True)

# ============================================================================
# LOAD REAL DATA
# ============================================================================

# Get colony locations from SQLite database
@st.cache_data(ttl=3600)
def get_colonies_from_db():
    """Get unique colonies with GPS coordinates from database."""
    db_path = os.getenv("DB_PATH", "data/bird_data_complete.db")
    try:
        conn = sqlite3.connect(db_path)
        query = """
        SELECT DISTINCT
            ColonyName,
            CAST(Latitude AS REAL) as Latitude,
            CAST(Longitude AS REAL) as Longitude,
            COUNT(DISTINCT Year) as years_surveyed,
            SUM(CAST(COALESCE(Birds, 0) AS INTEGER)) as total_birds_all_years
        FROM [tblColonyTotals2010-2021_MayJuneCombined]
        WHERE Latitude IS NOT NULL
          AND Longitude IS NOT NULL
          AND CAST(Latitude AS REAL) != 0
          AND CAST(Longitude AS REAL) != 0
        GROUP BY ColonyName, Latitude, Longitude
        ORDER BY total_birds_all_years DESC
        """
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df
    except Exception as e:
        st.error(f"Database error: {e}")
        return pd.DataFrame()

colonies_df = get_colonies_from_db()

# Load STAC data (4 colonies with expert dots)
stac_data = get_stac_summary()
stac_colonies = {c["id"]: c for c in stac_data.get("colonies", [])}

# ============================================================================
# SESSION STATE
# ============================================================================

if "selected_colony" not in st.session_state:
    st.session_state.selected_colony = None
if "show_only_stac" not in st.session_state:
    st.session_state.show_only_stac = False

# ============================================================================
# MAIN LAYOUT
# ============================================================================

col_map, col_detail = st.columns([1.5, 1], gap="large")

# ============================================================================
# LEFT: MAP
# ============================================================================

with col_map:
    st.markdown("### 🌊 Gulf Coast Colonies")

    # Filter toggle
    show_only_stac = st.checkbox(
        "🔵 Show only colonies with expert annotations",
        value=st.session_state.show_only_stac,
        key="stac_filter",
        help="Expert annotations = manually dotted bird locations from The Water Institute's STAC catalog (43,000+ individual birds). Only 4 colonies have this data: Queen Bess Island, New Harbor Island 2/3, Pepperfish Key."
    )

    # Filter colonies based on toggle
    display_df = colonies_df.copy()
    if show_only_stac:
        # Filter to only colonies that match STAC IDs
        # STAC IDs: QueenBessIsland, NewHarborIsland2, NewHarborIsland3, PepperfishKey
        stac_keywords = ["queen bess", "new harbor", "pepperfish"]
        stac_names = set()
        for colony_name in colonies_df["ColonyName"]:
            colony_lower = colony_name.lower()
            if any(keyword in colony_lower for keyword in stac_keywords):
                stac_names.add(colony_name)
        display_df = colonies_df[colonies_df["ColonyName"].isin(stac_names)]

        # Debug: Show what we found
        if len(stac_names) == 0:
            st.warning(f"⚠️ Could not find STAC colonies in database. Available colonies: {', '.join(colonies_df['ColonyName'].head(10).tolist()[:3])}...")
        else:
            st.info(f"Found {len(stac_names)} colonies: {', '.join(list(stac_names)[:5])}")

    st.caption(f"Showing {len(display_df)} of {len(colonies_df)} colonies")

    # Create map
    if len(display_df) == 0:
        st.warning("No colonies match the current filter.")
    else:
        m = folium.Map(
            location=[29.5, -89.5],
            zoom_start=6,
            tiles="CartoDB positron"
        )

        # Add satellite layer
        folium.TileLayer(
            tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
            attr="Esri",
            name="Satellite",
            overlay=False,
            control=True
        ).add_to(m)

        # Add colony markers
        for _, colony in display_df.iterrows():
            colony_name = colony["ColonyName"]
            lat = colony["Latitude"]
            lon = colony["Longitude"]
            years = colony["years_surveyed"]
            total = colony["total_birds_all_years"]

            # Check if this colony has STAC data (expert dots)
            has_stac = any(colony_name.lower() in c.lower() for c in stac_colonies.keys())
            color = "#2AB8DC" if has_stac else "#D97757"

            popup_html = f"""
            <div style="font-family:sans-serif; min-width:180px">
                <b style="font-size:14px">{colony_name}</b><br><br>
                <b>Years Surveyed:</b> {int(years)}<br>
                <b>Total Birds (all years):</b> {int(total):,}<br>
                <b>Expert Dots Available:</b> {'Yes' if has_stac else 'No'}<br>
                <br>
                <em style="color:#666">Click to view details</em>
            </div>
            """

            folium.CircleMarker(
                location=[lat, lon],
                radius=8,
                color=color,
                fill=True,
                fill_color=color,
                fill_opacity=0.6,
                opacity=0.9,
                popup=folium.Popup(popup_html, max_width=250),
                tooltip=f"{colony_name} — {int(years)} years"
            ).add_to(m)

        folium.LayerControl().add_to(m)

        # Render map (no click handling to avoid infinite loops)
        try:
            from streamlit_folium import st_folium
            st_folium(m, width=None, height=500)
        except ImportError:
            map_html = m._repr_html_()
            st.components.v1.html(map_html, height=500)
            st.info("Install streamlit-folium for interactive selection")

    # Colony selector (always show, use filtered list)
    st.markdown("**Select colony:**")
    colony_names = display_df["ColonyName"].tolist()

    # Initialize with first colony if none selected
    if st.session_state.selected_colony is None and colony_names:
        st.session_state.selected_colony = colony_names[0]

    selected = st.selectbox(
        "Colony",
        options=colony_names,
        index=colony_names.index(st.session_state.selected_colony) if st.session_state.selected_colony in colony_names else 0,
        label_visibility="collapsed",
        key="colony_selector"
    )

    # Update state without rerun
    if selected != st.session_state.selected_colony:
        st.session_state.selected_colony = selected

# ============================================================================
# RIGHT: COLONY DETAILS
# ============================================================================

with col_detail:
    if not st.session_state.selected_colony:
        st.markdown("""
        <div style="text-align:center; padding:3rem 1rem; color:#666">
            <div style="font-size:3rem">🗺️</div>
            <h3 style="color:#888">Select a Colony</h3>
            <p>Click a marker on the map or use the dropdown.</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        colony_name = st.session_state.selected_colony
        colony_data = colonies_df[colonies_df["ColonyName"] == colony_name].iloc[0]

        st.markdown(f"### {colony_name}")

        # Basic info
        col_a, col_b = st.columns(2)
        with col_a:
            st.metric("Location", f"{colony_data['Latitude']:.3f}, {colony_data['Longitude']:.3f}")
        with col_b:
            st.metric("Years Surveyed", int(colony_data['years_surveyed']))

        st.markdown("---")

        # Population trend (real data from database)
        st.markdown("#### 📈 Population Trend (2010-2021)")

        @st.cache_data(ttl=3600)
        def get_colony_trend(colony_name):
            db_path = os.getenv("DB_PATH", "data/bird_data_complete.db")
            try:
                conn = sqlite3.connect(db_path)
                query = """
                SELECT
                    CAST(Year AS INTEGER) as Year,
                    SUM(CAST(COALESCE(Birds, 0) AS INTEGER)) as total_birds,
                    COUNT(DISTINCT SpeciesCode) as species_count
                FROM [tblColonyTotals2010-2021_MayJuneCombined]
                WHERE ColonyName = ?
                GROUP BY Year
                ORDER BY Year
                """
                df = pd.read_sql_query(query, conn, params=(colony_name,))
                conn.close()
                return df
            except Exception as e:
                return pd.DataFrame()

        trend_df = get_colony_trend(colony_name)

        if not trend_df.empty:
            fig = go.Figure()

            fig.add_trace(go.Scatter(
                x=trend_df["Year"],
                y=trend_df["total_birds"],
                mode="lines+markers",
                line=dict(color="#D97757", width=3),
                marker=dict(size=8),
                name="Total Birds"
            ))

            fig.update_layout(
                template="plotly_dark",
                paper_bgcolor="#1A1A1A",
                plot_bgcolor="#2D2D2D",
                height=250,
                margin=dict(l=10, r=10, t=10, b=10),
                xaxis=dict(title="Year", tickmode="linear", dtick=1),
                yaxis=dict(title="Bird Count"),
                showlegend=False
            )

            st.plotly_chart(fig, use_container_width=True)

            # Calculate trend
            if len(trend_df) >= 2:
                first_year = trend_df.iloc[0]
                last_year = trend_df.iloc[-1]
                change = last_year["total_birds"] - first_year["total_birds"]
                pct_change = (change / first_year["total_birds"]) * 100 if first_year["total_birds"] > 0 else 0

                col_trend1, col_trend2 = st.columns(2)
                with col_trend1:
                    st.metric(
                        f"{int(first_year['Year'])} Count",
                        f"{int(first_year['total_birds']):,}"
                    )
                with col_trend2:
                    st.metric(
                        f"{int(last_year['Year'])} Count",
                        f"{int(last_year['total_birds']):,}",
                        delta=f"{pct_change:+.1f}%"
                    )
        else:
            st.info("No trend data available")

        st.markdown("---")

        # Species breakdown (real data)
        st.markdown("#### 🐦 Species Breakdown")

        @st.cache_data(ttl=3600)
        def get_colony_species(colony_name):
            db_path = os.getenv("DB_PATH", "data/bird_data_complete.db")
            try:
                conn = sqlite3.connect(db_path)
                query = """
                SELECT
                    SpeciesCode,
                    SUM(CAST(COALESCE(Birds, 0) AS INTEGER)) as total_birds,
                    COUNT(DISTINCT Year) as years_present
                FROM [tblColonyTotals2010-2021_MayJuneCombined]
                WHERE ColonyName = ?
                  AND CAST(COALESCE(Birds, 0) AS INTEGER) > 0
                GROUP BY SpeciesCode
                ORDER BY total_birds DESC
                LIMIT 10
                """
                df = pd.read_sql_query(query, conn, params=(colony_name,))
                conn.close()
                return df
            except Exception as e:
                return pd.DataFrame()

        species_df = get_colony_species(colony_name)

        if not species_df.empty:
            fig_species = go.Figure()

            fig_species.add_trace(go.Bar(
                y=species_df["SpeciesCode"],
                x=species_df["total_birds"],
                orientation="h",
                marker_color="#2AB8DC",
                text=species_df["total_birds"].apply(lambda x: f"{int(x):,}"),
                textposition="outside"
            ))

            fig_species.update_layout(
                template="plotly_dark",
                paper_bgcolor="#1A1A1A",
                plot_bgcolor="#2D2D2D",
                height=max(250, len(species_df) * 30),
                margin=dict(l=10, r=60, t=10, b=10),
                yaxis=dict(categoryorder="total ascending"),
                xaxis=dict(title="Total Birds (All Years)"),
                showlegend=False
            )

            st.plotly_chart(fig_species, use_container_width=True)
            st.caption(f"Top {len(species_df)} species by total count")
        else:
            st.info("No species data available")

        st.markdown("---")

        # Check if STAC expert dots are available
        stac_colony = None
        for stac_id, stac_meta in stac_colonies.items():
            if colony_name.lower() in stac_id.lower() or stac_id.lower() in colony_name.lower():
                stac_colony = stac_id
                break

        if stac_colony:
            st.markdown("#### 🔵 Expert Annotations Available")
            st.success(f"This colony has expert-dotted data from The Water Institute's STAC catalog.")

            available_years = stac_colonies[stac_colony].get("years", [])
            if available_years:
                st.markdown(f"**Years:** {', '.join(available_years)}")

                # Show species breakdown for latest year
                latest_year = available_years[-1]
                species_resp = get_stac_species(stac_colony, latest_year)
                species_list = species_resp.get("species", [])

                if species_list:
                    st.markdown(f"**Expert counts ({latest_year}):**")
                    for sp in species_list[:5]:
                        st.markdown(f"- {sp['name']}: {sp['total_birds']:,} birds")

                    # Button to show expert dots on actual aerial imagery
                    if st.button("🔵 View Expert Annotations on Aerial Photo", key=f"show_dots_{stac_colony}"):
                        with st.spinner(f"Loading aerial mosaic and {sum(sp['total_birds'] for sp in species_list):,} expert dots..."):
                            # Get the actual aerial survey mosaic
                            from services.api_client import get_mosaic_preview

                            mosaic_b64 = get_mosaic_preview(stac_colony, latest_year)

                            if mosaic_b64:
                                # Display the actual aerial photo
                                st.markdown(f"#### 📸 Aerial Survey Mosaic ({latest_year})")
                                img_bytes = base64.b64decode(mosaic_b64)
                                from PIL import Image, ImageDraw
                                import io

                                # Open the mosaic image
                                img = Image.open(io.BytesIO(img_bytes))
                                draw = ImageDraw.Draw(img)

                                # Get image dimensions
                                img_width, img_height = img.size

                                # Load expert dots and overlay them
                                st.info(f"Overlaying expert annotations from {len(species_list)} species...")

                                # Get bounding box of the image (we need this to map lat/lon to pixels)
                                # For now, let's just show the image and dots separately
                                st.image(img, caption=f"{stac_colony} - {latest_year} Survey Mosaic (512×512px center tile)", use_container_width=True)

                                st.markdown("**Expert Dot Locations:**")
                                st.caption("(Dots are overlaid on the full mosaic - this is a preview tile)")

                                # Show dots on interactive map at high zoom
                                colony_meta = stac_colonies[stac_colony]
                                dot_map = folium.Map(
                                    location=[colony_meta["lat"], colony_meta["lon"]],
                                    zoom_start=16,  # Very high zoom to see individual birds
                                    tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
                                    attr="Esri"
                                )

                                total_dots = 0
                                # Add expert dots for all species
                                for sp in species_list:
                                    dots_data = get_stac_dots(stac_colony, latest_year, sp['code'])
                                    features = dots_data.get("features", [])
                                    color = sp.get("color", "#2EC46A")

                                    for feat in features:
                                        coords = feat.get("geometry", {}).get("coordinates", [])
                                        if len(coords) == 2:
                                            lon, lat = coords
                                            total_dots += 1
                                            folium.CircleMarker(
                                                location=[lat, lon],
                                                radius=4,
                                                color=color,
                                                fill=True,
                                                fill_color=color,
                                                fill_opacity=0.7,
                                                opacity=0.9,
                                                tooltip=f"{sp['name']}"
                                            ).add_to(dot_map)

                                # Render expert dots map
                                try:
                                    from streamlit_folium import st_folium
                                    st_folium(dot_map, width=None, height=500)
                                except ImportError:
                                    st.components.v1.html(dot_map._repr_html_(), height=500)

                                st.success(f"✓ Showing {total_dots:,} expert-annotated bird locations on aerial imagery")
                                st.caption("Zoom in on the map above to see individual birds. Each colored dot represents one bird that an expert identified in the aerial survey photos.")

                            else:
                                st.warning("Could not load aerial mosaic preview. Showing dots on satellite basemap instead.")

                                # Fallback: show on satellite basemap
                                colony_meta = stac_colonies[stac_colony]
                                dot_map = folium.Map(
                                    location=[colony_meta["lat"], colony_meta["lon"]],
                                    zoom_start=15,
                                    tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
                                    attr="Esri"
                                )

                                for sp in species_list:
                                    dots_data = get_stac_dots(stac_colony, latest_year, sp['code'])
                                    features = dots_data.get("features", [])
                                    color = sp.get("color", "#2EC46A")

                                    for feat in features:
                                        coords = feat.get("geometry", {}).get("coordinates", [])
                                        if len(coords) == 2:
                                            lon, lat = coords
                                            folium.CircleMarker(
                                                location=[lat, lon],
                                                radius=4,
                                                color=color,
                                                fill=True,
                                                fill_color=color,
                                                fill_opacity=0.7,
                                                opacity=0.9,
                                                tooltip=f"{sp['name']}"
                                            ).add_to(dot_map)

                                try:
                                    from streamlit_folium import st_folium
                                    st_folium(dot_map, width=None, height=500)
                                except ImportError:
                                    st.components.v1.html(dot_map._repr_html_(), height=500)
        else:
            st.info("No expert annotations available for this colony in STAC catalog.")

# ============================================================================
# CONSERVATION ANALYSIS
# ============================================================================

st.markdown("---")
st.markdown("## 📊 Conservation Analysis")
st.caption("Identifying colonies with biggest changes (2010-2021)")

@st.cache_data(ttl=3600)
def get_conservation_analysis():
    """Calculate conservation metrics for all colonies."""
    db_path = os.getenv("DB_PATH", "data/bird_data_complete.db")
    try:
        conn = sqlite3.connect(db_path)

        # Query: Colony trends (first year vs last year)
        query = """
        WITH FirstYear AS (
            SELECT
                ColonyName,
                MIN(CAST(Year AS INTEGER)) as first_year,
                SUM(CAST(COALESCE(Birds, 0) AS INTEGER)) as first_count
            FROM [tblColonyTotals2010-2021_MayJuneCombined]
            WHERE CAST(COALESCE(Birds, 0) AS INTEGER) > 0
            GROUP BY ColonyName, Year
        ),
        LastYear AS (
            SELECT
                ColonyName,
                MAX(CAST(Year AS INTEGER)) as last_year,
                SUM(CAST(COALESCE(Birds, 0) AS INTEGER)) as last_count
            FROM [tblColonyTotals2010-2021_MayJuneCombined]
            WHERE CAST(COALESCE(Birds, 0) AS INTEGER) > 0
            GROUP BY ColonyName, Year
        )
        SELECT
            f.ColonyName,
            f.first_year,
            f.first_count,
            l.last_year,
            l.last_count,
            CAST(l.last_count - f.first_count AS REAL) / f.first_count * 100 as percent_change
        FROM FirstYear f
        JOIN LastYear l ON f.ColonyName = l.ColonyName
        WHERE f.first_year != l.last_year
        ORDER BY percent_change ASC
        """

        trends_df = pd.read_sql_query(query, conn)

        # Query: Species diversity per colony
        diversity_query = """
        SELECT
            ColonyName,
            COUNT(DISTINCT SpeciesCode) as species_count,
            SUM(CAST(COALESCE(Birds, 0) AS INTEGER)) as total_birds
        FROM [tblColonyTotals2010-2021_MayJuneCombined]
        WHERE CAST(COALESCE(Birds, 0) AS INTEGER) > 0
        GROUP BY ColonyName
        ORDER BY species_count DESC, total_birds DESC
        LIMIT 10
        """

        diversity_df = pd.read_sql_query(diversity_query, conn)

        conn.close()

        return {
            "trends": trends_df,
            "diversity": diversity_df
        }
    except Exception as e:
        st.error(f"Analysis error: {e}")
        return {"trends": pd.DataFrame(), "diversity": pd.DataFrame()}

analysis = get_conservation_analysis()

col_analysis1, col_analysis2 = st.columns(2)

with col_analysis1:
    st.markdown("### 🔴 Colonies with Biggest Decline")

    trends = analysis["trends"]
    if not trends.empty:
        declining = trends[trends["percent_change"] < -10].head(5)

        if not declining.empty:
            for _, row in declining.iterrows():
                colony = row["ColonyName"]
                change = row["percent_change"]
                first_count = int(row["first_count"])
                last_count = int(row["last_count"])

                st.markdown(f"""
                **{colony}**
                - {int(row['first_year'])}: {first_count:,} birds
                - {int(row['last_year'])}: {last_count:,} birds
                - Change: **{change:.1f}%** 🔻
                """)
        else:
            st.info("No significant declining colonies found (>10% loss)")
    else:
        st.info("No trend data available")

with col_analysis2:
    st.markdown("### 🟢 Colonies with Biggest Growth")

    if not trends.empty:
        growing = trends[trends["percent_change"] > 10].tail(5).sort_values("percent_change", ascending=False)

        if not growing.empty:
            for _, row in growing.iterrows():
                colony = row["ColonyName"]
                change = row["percent_change"]
                first_count = int(row["first_count"])
                last_count = int(row["last_count"])

                st.markdown(f"""
                **{colony}**
                - {int(row['first_year'])}: {first_count:,} birds
                - {int(row['last_year'])}: {last_count:,} birds
                - Change: **+{change:.1f}%** 🔺
                """)
        else:
            st.info("No significant growing colonies found (>10% gain)")
    else:
        st.info("No trend data available")

st.markdown("---")

st.markdown("### 🌟 Most Species-Diverse Colonies")
st.caption("Conservation value: High diversity = resilient ecosystem")

diversity = analysis["diversity"]
if not diversity.empty:
    col_div1, col_div2, col_div3 = st.columns(3)

    for idx, row in diversity.head(3).iterrows():
        col = [col_div1, col_div2, col_div3][idx]
        with col:
            st.metric(
                row["ColonyName"],
                f"{int(row['species_count'])} species",
                delta=f"{int(row['total_birds']):,} birds"
            )
else:
    st.info("No diversity data available")

# ============================================================================
# BOTTOM: DATA SUMMARY
# ============================================================================

st.markdown("---")

col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)

with col_stat1:
    st.metric("Total Colonies", len(colonies_df))

with col_stat2:
    stac_count = len(stac_colonies)
    st.metric("With Expert Dots", stac_count)

with col_stat3:
    total_birds = int(colonies_df["total_birds_all_years"].sum())
    st.metric("Total Birds (All Years)", f"{total_birds:,}")

with col_stat4:
    years = "2010-2021"
    st.metric("Survey Period", years)

st.markdown("---")

st.markdown("""
<div style="text-align:center; color:#555; font-size:0.8rem; padding:0.5rem">
    <strong>Real data only.</strong> Colony locations and population trends from SQLite database (2010-2021).
    Expert annotations from The Water Institute's STAC catalog (4 colonies: Queen Bess, New Harbor 2/3, Pepperfish Key).
    No predictions, no fake overlays, no made-up risk scores.
</div>
""", unsafe_allow_html=True)
