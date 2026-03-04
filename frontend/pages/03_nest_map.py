"""
NestMap — Geospatial Colony Intelligence
=========================================
Interactive map showing Gulf Coast bird colony locations with:
- Species breakdown per colony per year (2015–2021)
- Expert-annotated dot overlays from The Water Institute's STAC catalog
- COG mosaic previews (actual aerial survey imagery)
- Live NestVision inference on mosaic tiles
- Population trend charts across years

Data source: TWI Avian STAC Catalog (43,000+ expert-annotated bird locations)
"""

import streamlit as st
import pandas as pd
import base64
from io import BytesIO
import folium
from folium import plugins
import plotly.express as px
import plotly.graph_objects as go

from components import init_page, render_header, render_sidebar
from services import (
    get_stac_summary, get_stac_species, get_stac_dots,
    get_mosaic_preview, run_mosaic_inference
)

# ============================================================================
# PAGE CONFIGURATION
# ============================================================================

init_page(page_title="NestMap - NestScope", page_icon="🗺️", layout="wide")
render_header(page_name="NestMap")

# ============================================================================
# SESSION STATE
# ============================================================================

if "selected_colony" not in st.session_state:
    st.session_state.selected_colony = None
if "selected_year" not in st.session_state:
    st.session_state.selected_year = "2021"
if "show_dots_species" not in st.session_state:
    st.session_state.show_dots_species = []
if "mosaic_preview_b64" not in st.session_state:
    st.session_state.mosaic_preview_b64 = None
if "mosaic_inference_result" not in st.session_state:
    st.session_state.mosaic_inference_result = None

# ============================================================================
# SIDEBAR
# ============================================================================

with st.sidebar:
    render_sidebar(active_page="nestmap")

    st.markdown("---")
    st.markdown("### 🗺️ Map Controls")

    # Year filter in sidebar
    year_options = ["2015", "2018", "2021"]
    selected_year = st.select_slider(
        "Survey Year",
        options=year_options,
        value=st.session_state.selected_year,
        help="Filter map markers by survey year"
    )
    if selected_year != st.session_state.selected_year:
        st.session_state.selected_year = selected_year
        st.session_state.show_dots_species = []
        st.session_state.mosaic_preview_b64 = None
        st.session_state.mosaic_inference_result = None

    st.markdown("---")
    st.markdown("### ℹ️ About NestMap")
    st.markdown("""
    Data from The Water Institute's STAC catalog:
    - **43,000+** expert-annotated bird locations
    - **19 species** labeled by ornithologists
    - **4 colonies** across the Gulf Coast
    - **2015–2021** survey years

    Click a colony pin on the map to explore its data.
    """)

# ============================================================================
# PAGE HEADER
# ============================================================================

st.markdown("""
    <div class="title-card">
        <h3>🗺️ NestMap: Geospatial Colony Intelligence</h3>
        <p>
            Explore Gulf Coast bird colony locations from The Water Institute's aerial surveys.
            Expert-annotated species data, population trends, and live AI inference — all in one place.
        </p>
    </div>
""", unsafe_allow_html=True)

# ============================================================================
# LOAD STAC DATA
# ============================================================================

with st.spinner("Loading colony data from STAC catalog..."):
    stac_data = get_stac_summary()

if "error" in stac_data and not stac_data.get("colonies"):
    st.error("Could not load STAC data. Make sure the backend server is running.")
    st.code("python -m uvicorn server.main:app --host 0.0.0.0 --port 8000 --reload")
    st.stop()

colonies = stac_data.get("colonies", [])
species_info = stac_data.get("species_info", {})

# Build a lookup dict: colony_id → colony data
colonies_by_id = {c["id"]: c for c in colonies}

# ============================================================================
# HELPER: SPECIES CHART
# ============================================================================

def render_species_chart(species_list: list, title: str = ""):
    """Render a Plotly horizontal bar chart for species breakdown."""
    if not species_list:
        st.info("No species data available for this selection.")
        return

    names = [s["name"] for s in species_list]
    birds = [s["total_birds"] for s in species_list]
    nests = [s["total_nests"] for s in species_list]
    colors = [s.get("color", "#D97757") for s in species_list]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=names, x=birds, name="Birds",
        orientation="h",
        marker_color="#D97757",
        text=birds, textposition="outside",
    ))
    fig.add_trace(go.Bar(
        y=names, x=nests, name="Nests",
        orientation="h",
        marker_color="#555555",
        text=nests, textposition="outside",
    ))
    fig.update_layout(
        barmode="group",
        template="plotly_dark",
        paper_bgcolor="#1A1A1A",
        plot_bgcolor="#2D2D2D",
        height=max(250, len(species_list) * 35 + 80),
        margin=dict(l=10, r=60, t=30, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        yaxis=dict(categoryorder="total ascending", tickfont=dict(size=11)),
        xaxis=dict(title="Count"),
        title=dict(text=title, font=dict(size=13, color="#A0A0A0")) if title else None,
    )
    st.plotly_chart(fig, use_container_width=True)


def render_population_trend(colony_id: str, species_totals: dict):
    """Render a multi-year population trend chart for a colony."""
    colony_meta = colonies_by_id.get(colony_id)
    if not colony_meta:
        return

    region = colony_meta["region"]
    available_years = sorted(colony_meta.get("years", []))

    if len(available_years) < 2:
        st.info("Population trend requires data from at least 2 survey years.")
        return

    trend_data = []
    for species_code, regions in species_totals.items():
        region_data = regions.get(region, {})
        colony_data = region_data.get(colony_id, {})
        for year in available_years:
            year_data = colony_data.get(year, {})
            birds = year_data.get("total_birds", 0)
            if birds > 0:
                name = species_info.get(species_code, {}).get("name", species_code)
                trend_data.append({"Year": int(year), "Species": name, "Birds": birds, "Code": species_code})

    if not trend_data:
        st.info("No trend data available.")
        return

    df = pd.DataFrame(trend_data)
    # Only show species with data in multiple years
    multi_year = df.groupby("Code")["Year"].nunique()
    codes_to_show = multi_year[multi_year >= 2].index.tolist()
    if codes_to_show:
        df = df[df["Code"].isin(codes_to_show)]

    if df.empty:
        st.info("No multi-year trend data to display.")
        return

    fig = px.line(
        df, x="Year", y="Birds", color="Species",
        markers=True, template="plotly_dark",
        labels={"Birds": "Bird Count", "Year": "Survey Year"},
    )
    fig.update_layout(
        paper_bgcolor="#1A1A1A", plot_bgcolor="#2D2D2D",
        height=300, margin=dict(l=10, r=10, t=10, b=10),
        legend=dict(font=dict(size=10)),
        xaxis=dict(tickmode="array", tickvals=[int(y) for y in available_years]),
    )
    st.plotly_chart(fig, use_container_width=True)


# ============================================================================
# MAIN LAYOUT: Map (left) + Detail Panel (right)
# ============================================================================

map_col, detail_col = st.columns([1.3, 1], gap="large")

# ============================================================================
# LEFT COLUMN: FOLIUM MAP
# ============================================================================

with map_col:
    st.markdown("### 🌊 Gulf Coast Colony Map")
    st.caption(f"Showing colonies with data for year: **{st.session_state.selected_year}** — click a marker to explore")

    # Build Folium map centered on Gulf Coast
    m = folium.Map(
        location=[29.4, -88.5],
        zoom_start=7,
        tiles="CartoDB dark_matter",
    )

    # Add satellite layer option
    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attr="Esri",
        name="Satellite",
        overlay=False,
        control=True
    ).add_to(m)
    folium.LayerControl().add_to(m)

    # Colony marker size based on total birds (log scale)
    import math

    selected_year = st.session_state.selected_year

    for colony in colonies:
        colony_id = colony["id"]
        years = colony.get("years", [])

        # Only show colonies with data for selected year
        if selected_year not in years:
            color = "#555555"
            opacity = 0.4
            total = 0
        else:
            total = colony.get("total_birds_latest", 0)
            color = "#D97757"  # Claude orange
            opacity = 0.9

        # Scale radius: sqrt of total birds, clamped 8–30
        radius = max(8, min(30, int(math.sqrt(total / 10 + 1) * 4))) if total > 0 else 8

        dominant = colony.get("dominant_species_name", "Unknown")
        years_str = ", ".join(colony.get("years", []))

        popup_html = f"""
        <div style="font-family:sans-serif; min-width:180px">
            <b style="font-size:14px">{colony['display_name']}</b><br>
            <span style="color:#888; font-size:11px">{colony['description']}</span><br><br>
            <b>Dominant Species:</b> {dominant}<br>
            <b>Available Years:</b> {years_str}<br>
            <b>Total Birds (latest):</b> {total:,}<br>
            <br>
            <em style="color:#D97757">Click to select this colony</em>
        </div>
        """

        folium.CircleMarker(
            location=[colony["lat"], colony["lon"]],
            radius=radius,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=opacity,
            opacity=opacity,
            popup=folium.Popup(popup_html, max_width=250),
            tooltip=f"{'🔴' if selected_year in years else '⚫'} {colony['display_name']} — click to explore",
        ).add_to(m)

    # Overlay species dots if any are selected
    if st.session_state.selected_colony and st.session_state.show_dots_species:
        colony_id = st.session_state.selected_colony
        year = st.session_state.selected_year
        for species_code in st.session_state.show_dots_species:
            dots_data = get_stac_dots(colony_id, year, species_code)
            features = dots_data.get("features", [])
            sp_color = species_info.get(species_code, {}).get("color", "#2EC46A")
            sp_name = species_info.get(species_code, {}).get("name", species_code)
            for feat in features:
                coords = feat.get("geometry", {}).get("coordinates", [])
                if len(coords) == 2:
                    lon, lat = coords
                    folium.CircleMarker(
                        location=[lat, lon],
                        radius=4,
                        color=sp_color,
                        fill=True,
                        fill_color=sp_color,
                        fill_opacity=0.8,
                        opacity=0.9,
                        tooltip=f"{sp_name} — expert dot",
                    ).add_to(m)

    # Render map
    try:
        from streamlit_folium import st_folium
        map_output = st_folium(m, width=None, height=480, returned_objects=["last_object_clicked"])
        # Handle map click to select colony
        if map_output and map_output.get("last_object_clicked"):
            clicked = map_output["last_object_clicked"]
            click_lat = clicked.get("lat")
            click_lng = clicked.get("lng")
            if click_lat and click_lng:
                # Find nearest colony
                best_colony = None
                best_dist = float("inf")
                for colony in colonies:
                    dist = ((colony["lat"] - click_lat) ** 2 + (colony["lon"] - click_lng) ** 2) ** 0.5
                    if dist < best_dist:
                        best_dist = dist
                        best_colony = colony["id"]
                if best_colony and best_dist < 0.1:
                    if st.session_state.selected_colony != best_colony:
                        st.session_state.selected_colony = best_colony
                        st.session_state.show_dots_species = []
                        st.session_state.mosaic_preview_b64 = None
                        st.session_state.mosaic_inference_result = None
                        st.rerun()
    except ImportError:
        # Fallback: render as HTML component
        map_html = m._repr_html_()
        st.components.v1.html(map_html, height=480)
        st.info("Install `streamlit-folium` for interactive colony selection: `pip install streamlit-folium`")

    # Colony selector fallback (always available)
    st.markdown("**Select a colony:**")
    colony_options = {c["display_name"]: c["id"] for c in colonies}
    selected_display = st.selectbox(
        "Colony",
        options=list(colony_options.keys()),
        index=list(colony_options.values()).index(st.session_state.selected_colony)
              if st.session_state.selected_colony in colony_options.values() else 0,
        label_visibility="collapsed"
    )
    new_colony_id = colony_options[selected_display]
    if new_colony_id != st.session_state.selected_colony:
        st.session_state.selected_colony = new_colony_id
        st.session_state.show_dots_species = []
        st.session_state.mosaic_preview_b64 = None
        st.session_state.mosaic_inference_result = None
        st.rerun()

# ============================================================================
# RIGHT COLUMN: COLONY DETAIL PANEL
# ============================================================================

with detail_col:
    if not st.session_state.selected_colony:
        st.markdown("""
        <div style="text-align:center; padding:4rem 2rem; color:#666">
            <div style="font-size:3rem">🗺️</div>
            <h3 style="color:#888; margin-top:1rem">Select a Colony</h3>
            <p>Click a marker on the map or use the dropdown to explore colony data.</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        colony_id = st.session_state.selected_colony
        colony = colonies_by_id.get(colony_id, {})
        species_totals = stac_data.get("species_totals", {})

        # Colony header
        st.markdown(f"### {colony.get('display_name', colony_id)}")
        st.caption(colony.get("description", ""))

        col_a, col_b = st.columns(2)
        with col_a:
            st.metric("Region", colony.get("region", "—").replace("Bay", " Bay"))
        with col_b:
            st.metric("Lat/Lon", f"{colony.get('lat', 0):.3f}, {colony.get('lon', 0):.3f}")

        st.markdown("---")

        # Year tabs — only show available years for this colony
        available_years = colony.get("years", [])
        if not available_years:
            st.warning("No survey years available for this colony.")
        else:
            # Filter tabs to available years only
            year_tabs = st.tabs(available_years)

            for tab, year in zip(year_tabs, available_years):
                with tab:
                    # Update selected year when tab is active
                    # (Streamlit doesn't have tab.on_click, so we update on render)
                    if year != st.session_state.selected_year:
                        if st.button(f"📊 Load {year} Data", key=f"load_{year}_{colony_id}"):
                            st.session_state.selected_year = year
                            st.session_state.show_dots_species = []
                            st.session_state.mosaic_preview_b64 = None
                            st.session_state.mosaic_inference_result = None
                            st.rerun()

                    # Fetch species breakdown for this year
                    with st.spinner(f"Loading {year} species data..."):
                        species_resp = get_stac_species(colony_id, year)

                    species_list = species_resp.get("species", [])

                    if not species_list:
                        st.info(f"No species data available for {year}.")
                    else:
                        # Top metrics
                        total_birds = sum(s["total_birds"] for s in species_list)
                        total_nests = sum(s["total_nests"] for s in species_list)
                        num_species = len(species_list)

                        mc1, mc2, mc3 = st.columns(3)
                        with mc1:
                            st.metric("🐦 Total Birds", f"{total_birds:,}")
                        with mc2:
                            st.metric("🪺 Total Nests", f"{total_nests:,}")
                        with mc3:
                            st.metric("🔬 Species", num_species)

                        # Species bar chart
                        render_species_chart(species_list)

                        # Expert dots overlay section
                        st.markdown("**🔵 Show Expert Dots on Map**")
                        top_species = [s["code"] for s in species_list[:5]]  # top 5 by birds
                        show_dots = st.multiselect(
                            "Select species to overlay:",
                            options=top_species,
                            default=st.session_state.show_dots_species if year == st.session_state.selected_year else [],
                            format_func=lambda c: f"{c} — {species_info.get(c, {}).get('name', c)}",
                            key=f"dots_{colony_id}_{year}",
                            help="These are expert-annotated bird locations from The Water Institute's STAC catalog"
                        )
                        if show_dots != st.session_state.show_dots_species:
                            st.session_state.show_dots_species = show_dots
                            st.session_state.selected_year = year
                            st.rerun()

                        st.markdown("---")

                        # Mosaic preview and inference
                        col_mosaic, col_infer = st.columns(2)

                        with col_mosaic:
                            if st.button(f"📸 View {year} Mosaic", key=f"preview_{colony_id}_{year}", use_container_width=True):
                                with st.spinner("Loading mosaic preview..."):
                                    b64 = get_mosaic_preview(colony_id, year)
                                    st.session_state.mosaic_preview_b64 = b64
                                    st.session_state.selected_year = year

                        with col_infer:
                            if st.button(f"🔬 Run NestVision", key=f"infer_{colony_id}_{year}", use_container_width=True, type="primary"):
                                with st.spinner(f"Running AI detection on {year} mosaic..."):
                                    result = run_mosaic_inference(colony_id, year)
                                    st.session_state.mosaic_inference_result = result
                                    st.session_state.selected_year = year

            # Population trend chart (shown below tabs)
            if len(available_years) >= 2:
                st.markdown("---")
                st.markdown("**📈 Population Trend**")
                render_population_trend(colony_id, species_totals)

    # Mosaic preview display (outside tabs — persists across tab switches)
    if st.session_state.mosaic_preview_b64:
        st.markdown("---")
        st.markdown(f"#### 📸 Mosaic Preview — {st.session_state.selected_colony} {st.session_state.selected_year}")
        img_bytes = base64.b64decode(st.session_state.mosaic_preview_b64)
        from PIL import Image
        img = Image.open(BytesIO(img_bytes))
        st.image(img, caption=f"Center tile of {st.session_state.selected_year} survey mosaic (512×512px)", use_container_width=True)
        st.caption("Source: The Water Institute Cloud Optimized GeoTIFF (COG) mosaic via STAC catalog")

    # Inference result display
    if st.session_state.mosaic_inference_result:
        result = st.session_state.mosaic_inference_result
        if "error" in result:
            st.error(f"Inference failed: {result['error']}")
        else:
            st.markdown("---")
            st.markdown(f"#### 🔬 NestVision Results — {result.get('colony_id', '')} {result.get('year', '')}")
            bird_count = result.get("bird_count", 0)
            st.success(result.get("message", f"Detected {bird_count} birds"))

            # Species summary metrics
            species_summary = result.get("species_summary", {})
            if species_summary:
                display_summary = {k: v for k, v in species_summary.items() if k != "UNKNOWN"} or species_summary
                if display_summary:
                    sc = st.columns(min(len(display_summary), 4))
                    for i, (group, count) in enumerate(sorted(display_summary.items(), key=lambda x: -x[1])):
                        with sc[i % len(sc)]:
                            st.metric(group.replace("_", " ").title(), count)

            # Annotated image
            annotated_b64 = result.get("annotated_image_base64")
            if annotated_b64:
                ann_bytes = base64.b64decode(annotated_b64)
                ann_img = Image.open(BytesIO(ann_bytes))
                st.image(ann_img, caption="AI detection on mosaic tile", use_container_width=True)
                st.metric("⚡ Inference Time", f"{result.get('inference_time', 0):.2f}s")

# ============================================================================
# BOTTOM SECTION: DATA CREDITS
# ============================================================================

st.markdown("---")
st.markdown("""
<div style="text-align:center; color:#555; font-size:0.8rem; padding:0.5rem">
    Data provided by <strong style="color:#888">The Water Institute</strong> — Gulf Coast Avian Monitoring Program<br>
    STAC Catalog: Expert-annotated bird surveys 2015–2021 | CC-BY-4.0
</div>
""", unsafe_allow_html=True)
