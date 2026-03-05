"""
NestTrends — Comprehensive Population Intelligence Dashboard
==========================================================
Dynamic trends visualization combining maps, timelines, and population analytics.
Better than the experts' static dashboard - everything toggleable and interactive.

Features:
- Interactive Gulf Coast colony map with STAC data
- Toggleable species/colony population trends
- Timeline scrubber for year-by-year analysis
- Per-colony trend analysis with expert annotations
- Species composition stacked charts
- Growth/decline insights
"""

import streamlit as st
import pandas as pd
import folium
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import sqlite3
import os
import base64

from components import init_page, render_header, render_sidebar
from services.api_client import get_stac_summary, get_stac_species, get_stac_dots, get_mosaic_preview

# ============================================================================
# PAGE CONFIGURATION
# ============================================================================

init_page(page_title="NestTrends - Population Intelligence", page_icon="📈", layout="wide")
render_header(page_name="NestTrends: Population Intelligence Dashboard")

# ============================================================================
# SIDEBAR
# ============================================================================

with st.sidebar:
    render_sidebar(active_page="nesttrends")

    st.markdown("---")
    st.markdown("### 📊 Controls")

    # Year range filter
    st.markdown("**Time Period**")
    year_range = st.slider(
        "Select years",
        min_value=2010,
        max_value=2021,
        value=(2010, 2021),
        label_visibility="collapsed"
    )

    # View mode selector
    view_mode = st.radio(
        "View Mode",
        ["Overview Map", "Species Trends", "Colony Deep Dive", "Composition Analysis"],
        help="Choose visualization type"
    )

    # Filter options
    st.markdown("---")
    st.markdown("**Filters**")

    show_only_stac = st.checkbox(
        "🔵 STAC colonies only",
        value=False,
        help="Show only colonies with expert annotations (4 colonies)"
    )

    st.markdown("---")
    st.markdown("### 💡 Features")
    st.markdown("""
    **Interactive:**
    - 🗺️ Click colonies on map
    - 🖱️ Toggle trends on/off
    - 🔍 Zoom & pan charts
    - 📈 Year-by-year timeline

    **Outshines experts' UI**
    """)

# ============================================================================
# PAGE HEADER
# ============================================================================

st.markdown("""
    <div class="title-card">
        <h3>📈 NestTrends: Population Intelligence Dashboard</h3>
        <p>
            Comprehensive population analytics combining maps, trends, and expert data (2010-2021).
            <strong>Toggle, zoom, and explore.</strong> Everything the experts have, but interactive.
        </p>
    </div>
""", unsafe_allow_html=True)

# ============================================================================
# LOAD DATA
# ============================================================================

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

@st.cache_data(ttl=3600)
def load_trend_data(year_start: int, year_end: int):
    """Load population trend data from database."""
    db_path = os.getenv("DB_PATH", "data/bird_data_complete.db")
    try:
        conn = sqlite3.connect(db_path)

        # Query: Year-by-year totals for all species
        species_query = """
        SELECT
            CAST(Year AS INTEGER) as Year,
            SpeciesCode,
            SUM(CAST(COALESCE(Birds, 0) AS INTEGER)) as total_birds,
            COUNT(DISTINCT ColonyName) as colony_count
        FROM [tblColonyTotals2010-2021_MayJuneCombined]
        WHERE CAST(Year AS INTEGER) BETWEEN ? AND ?
          AND CAST(COALESCE(Birds, 0) AS INTEGER) > 0
        GROUP BY Year, SpeciesCode
        ORDER BY Year, SpeciesCode
        """
        species_df = pd.read_sql_query(species_query, conn, params=(year_start, year_end))

        # Query: Year-by-year totals for all colonies
        colony_query = """
        SELECT
            CAST(Year AS INTEGER) as Year,
            ColonyName,
            SUM(CAST(COALESCE(Birds, 0) AS INTEGER)) as total_birds,
            COUNT(DISTINCT SpeciesCode) as species_count
        FROM [tblColonyTotals2010-2021_MayJuneCombined]
        WHERE CAST(Year AS INTEGER) BETWEEN ? AND ?
          AND CAST(COALESCE(Birds, 0) AS INTEGER) > 0
        GROUP BY Year, ColonyName
        ORDER BY Year, total_birds DESC
        """
        colony_df = pd.read_sql_query(colony_query, conn, params=(year_start, year_end))

        # Query: Species composition over time (top 10 species)
        composition_query = """
        WITH TopSpecies AS (
            SELECT SpeciesCode
            FROM [tblColonyTotals2010-2021_MayJuneCombined]
            WHERE CAST(Year AS INTEGER) BETWEEN ? AND ?
            GROUP BY SpeciesCode
            ORDER BY SUM(CAST(COALESCE(Birds, 0) AS INTEGER)) DESC
            LIMIT 10
        )
        SELECT
            CAST(Year AS INTEGER) as Year,
            SpeciesCode,
            SUM(CAST(COALESCE(Birds, 0) AS INTEGER)) as total_birds
        FROM [tblColonyTotals2010-2021_MayJuneCombined]
        WHERE CAST(Year AS INTEGER) BETWEEN ? AND ?
          AND SpeciesCode IN (SELECT SpeciesCode FROM TopSpecies)
        GROUP BY Year, SpeciesCode
        ORDER BY Year, SpeciesCode
        """
        composition_df = pd.read_sql_query(composition_query, conn, params=(year_start, year_end, year_start, year_end))

        # Query: Growth/decline analysis
        trends_query = """
        WITH FirstYear AS (
            SELECT
                SpeciesCode,
                MIN(CAST(Year AS INTEGER)) as first_year,
                SUM(CAST(COALESCE(Birds, 0) AS INTEGER)) as first_count
            FROM [tblColonyTotals2010-2021_MayJuneCombined]
            WHERE CAST(Year AS INTEGER) BETWEEN ? AND ?
            GROUP BY SpeciesCode, Year
        ),
        LastYear AS (
            SELECT
                SpeciesCode,
                MAX(CAST(Year AS INTEGER)) as last_year,
                SUM(CAST(COALESCE(Birds, 0) AS INTEGER)) as last_count
            FROM [tblColonyTotals2010-2021_MayJuneCombined]
            WHERE CAST(Year AS INTEGER) BETWEEN ? AND ?
            GROUP BY SpeciesCode, Year
        )
        SELECT
            f.SpeciesCode,
            f.first_year,
            f.first_count,
            l.last_year,
            l.last_count,
            CAST(l.last_count - f.first_count AS REAL) / f.first_count * 100 as percent_change
        FROM FirstYear f
        JOIN LastYear l ON f.SpeciesCode = l.SpeciesCode
        WHERE f.first_count > 100
        ORDER BY percent_change DESC
        """
        trends_analysis = pd.read_sql_query(trends_query, conn, params=(year_start, year_end, year_start, year_end))

        conn.close()

        return {
            "species": species_df,
            "colonies": colony_df,
            "composition": composition_df,
            "trends_analysis": trends_analysis
        }
    except Exception as e:
        st.error(f"Data loading error: {e}")
        return {
            "species": pd.DataFrame(),
            "colonies": pd.DataFrame(),
            "composition": pd.DataFrame(),
            "trends_analysis": pd.DataFrame()
        }

@st.cache_data(ttl=3600)
def get_colony_trend(colony_name, year_start, year_end):
    """Get population trend for a specific colony."""
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
          AND CAST(Year AS INTEGER) BETWEEN ? AND ?
        GROUP BY Year
        ORDER BY Year
        """
        df = pd.read_sql_query(query, conn, params=(colony_name, year_start, year_end))
        conn.close()
        return df
    except Exception as e:
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def get_colony_species(colony_name, year_start, year_end):
    """Get species breakdown for a specific colony."""
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
          AND CAST(Year AS INTEGER) BETWEEN ? AND ?
          AND CAST(COALESCE(Birds, 0) AS INTEGER) > 0
        GROUP BY SpeciesCode
        ORDER BY total_birds DESC
        LIMIT 10
        """
        df = pd.read_sql_query(query, conn, params=(colony_name, year_start, year_end))
        conn.close()
        return df
    except Exception as e:
        return pd.DataFrame()

# Load all data
colonies_df = get_colonies_from_db()
stac_data = get_stac_summary()
stac_colonies = {c["id"]: c for c in stac_data.get("colonies", [])}
data = load_trend_data(year_range[0], year_range[1])

# Session state for selected colony
if "selected_colony" not in st.session_state:
    st.session_state.selected_colony = None

# ============================================================================
# VIEW MODE SWITCHING
# ============================================================================

if view_mode == "Overview Map":
    st.markdown("## 🗺️ Gulf Coast Colonies Overview")

    col_map, col_stats = st.columns([2, 1], gap="large")

    with col_map:
        # Filter colonies if STAC only
        display_df = colonies_df.copy()
        if show_only_stac:
            stac_keywords = ["queen bess", "new harbor", "pepperfish"]
            stac_names = set()
            for colony_name in colonies_df["ColonyName"]:
                if any(kw in colony_name.lower() for kw in stac_keywords):
                    stac_names.add(colony_name)
            display_df = colonies_df[colonies_df["ColonyName"].isin(stac_names)]

        st.caption(f"Showing {len(display_df)} of {len(colonies_df)} colonies")

        # Create map
        m = folium.Map(location=[29.5, -89.5], zoom_start=6, tiles="CartoDB positron")

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
            has_stac = any(colony["ColonyName"].lower() in c.lower() for c in stac_colonies.keys())
            color = "#2AB8DC" if has_stac else "#D97757"

            popup_html = f"""
            <div style="font-family:sans-serif; min-width:180px">
                <b style="font-size:14px">{colony["ColonyName"]}</b><br><br>
                <b>Years Surveyed:</b> {int(colony["years_surveyed"])}<br>
                <b>Total Birds:</b> {int(colony["total_birds_all_years"]):,}<br>
                <b>Expert Data:</b> {'Yes' if has_stac else 'No'}<br>
            </div>
            """

            folium.CircleMarker(
                location=[colony["Latitude"], colony["Longitude"]],
                radius=8,
                color=color,
                fill=True,
                fill_color=color,
                fill_opacity=0.6,
                popup=folium.Popup(popup_html, max_width=250),
                tooltip=f"{colony['ColonyName']}"
            ).add_to(m)

        folium.LayerControl().add_to(m)

        try:
            from streamlit_folium import st_folium
            map_data = st_folium(m, width=None, height=500)
        except ImportError:
            st.components.v1.html(m._repr_html_(), height=500)

    with col_stats:
        st.markdown("### 📊 Quick Stats")

        st.metric("Total Colonies", len(colonies_df))
        st.metric("With Expert Data", len(stac_colonies))
        st.metric("Total Birds", f"{int(colonies_df['total_birds_all_years'].sum()):,}")
        st.metric("Survey Years", f"{year_range[0]}-{year_range[1]}")

        st.markdown("---")
        st.markdown("### 🔵 STAC Colonies")
        for stac_id, meta in stac_colonies.items():
            st.markdown(f"**{stac_id}**")
            st.caption(f"Years: {', '.join(meta.get('years', []))}")

elif view_mode == "Species Trends":
    st.markdown("## 🐦 Species Population Trends")
    st.caption(f"Gulf Coast-wide trends ({year_range[0]}-{year_range[1]}). Click legend to toggle.")

    species_df = data["species"]

    if not species_df.empty:
        # Get top species
        top_species = species_df.groupby("SpeciesCode")["total_birds"].sum().nlargest(15).index.tolist()

        # Multi-select
        selected_species = st.multiselect(
            "Select species to compare",
            options=top_species,
            default=top_species[:8],
            help="Choose species to display on chart"
        )

        # Create line chart
        fig = go.Figure()
        colors = ["#D97757", "#2AB8DC", "#2EC46A", "#F4B942", "#9B59B6",
                  "#E74C3C", "#3498DB", "#1ABC9C", "#F39C12", "#8E44AD"]

        for idx, species in enumerate(selected_species):
            species_data = species_df[species_df["SpeciesCode"] == species]
            fig.add_trace(go.Scatter(
                x=species_data["Year"],
                y=species_data["total_birds"],
                mode="lines+markers",
                name=species,
                line=dict(color=colors[idx % len(colors)], width=3),
                marker=dict(size=8),
                hovertemplate=f"<b>{species}</b><br>Year: %{x}<br>Birds: %{y:,}<extra></extra>"
            ))

        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor="#1A1A1A",
            plot_bgcolor="#2D2D2D",
            height=500,
            xaxis=dict(title="Year", tickmode="linear", dtick=1, gridcolor="#3A3A3A"),
            yaxis=dict(title="Bird Count", gridcolor="#3A3A3A"),
            hovermode="x unified",
            legend=dict(orientation="v", yanchor="top", y=1, xanchor="left", x=1.02, bgcolor="rgba(0,0,0,0.5)")
        )

        st.plotly_chart(fig, use_container_width=True)

        # Insights
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("### 🔺 Top Growth")
            trends = data["trends_analysis"]
            if not trends.empty:
                growing = trends[trends["percent_change"] > 0].head(5)
                for _, row in growing.iterrows():
                    st.markdown(f"**{row['SpeciesCode']}**: +{row['percent_change']:.1f}%")

        with col2:
            st.markdown("### 🔻 Top Decline")
            if not trends.empty:
                declining = trends[trends["percent_change"] < 0].tail(5).iloc[::-1]
                for _, row in declining.iterrows():
                    st.markdown(f"**{row['SpeciesCode']}**: {row['percent_change']:.1f}%")
    else:
        st.warning("No species data for selected period")

elif view_mode == "Colony Deep Dive":
    st.markdown("## 🔍 Colony-Specific Analysis")

    # Colony selector
    colony_names = colonies_df["ColonyName"].tolist()
    selected_colony = st.selectbox(
        "Select colony",
        options=colony_names,
        index=0 if not st.session_state.selected_colony else colony_names.index(st.session_state.selected_colony) if st.session_state.selected_colony in colony_names else 0
    )
    st.session_state.selected_colony = selected_colony

    colony_data = colonies_df[colonies_df["ColonyName"] == selected_colony].iloc[0]

    # Layout
    col_left, col_right = st.columns([1.5, 1], gap="large")

    with col_left:
        st.markdown(f"### {selected_colony}")
        st.caption(f"📍 {colony_data['Latitude']:.3f}, {colony_data['Longitude']:.3f}")

        # Population trend
        st.markdown("#### 📈 Population Trend")
        trend_df = get_colony_trend(selected_colony, year_range[0], year_range[1])

        if not trend_df.empty:
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=trend_df["Year"],
                y=trend_df["total_birds"],
                mode="lines+markers",
                line=dict(color="#D97757", width=3),
                marker=dict(size=8),
                fill='tozeroy',
                fillcolor='rgba(217, 119, 87, 0.2)'
            ))

            fig.update_layout(
                template="plotly_dark",
                paper_bgcolor="#1A1A1A",
                plot_bgcolor="#2D2D2D",
                height=300,
                margin=dict(l=10, r=10, t=10, b=10),
                xaxis=dict(title="Year", tickmode="linear", dtick=1),
                yaxis=dict(title="Bird Count"),
                showlegend=False
            )

            st.plotly_chart(fig, use_container_width=True)

            # Change metrics
            if len(trend_df) >= 2:
                first = trend_df.iloc[0]
                last = trend_df.iloc[-1]
                change = ((last["total_birds"] - first["total_birds"]) / first["total_birds"] * 100) if first["total_birds"] > 0 else 0

                col_a, col_b = st.columns(2)
                with col_a:
                    st.metric(f"{int(first['Year'])}", f"{int(first['total_birds']):,} birds")
                with col_b:
                    st.metric(f"{int(last['Year'])}", f"{int(last['total_birds']):,} birds", delta=f"{change:+.1f}%")

        # Species breakdown
        st.markdown("#### 🐦 Species Breakdown")
        species_df = get_colony_species(selected_colony, year_range[0], year_range[1])

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
                xaxis=dict(title="Total Birds"),
                showlegend=False
            )

            st.plotly_chart(fig_species, use_container_width=True)

    with col_right:
        st.markdown("### 🔵 Expert Data")

        # Check for STAC data
        stac_colony = None
        for stac_id, meta in stac_colonies.items():
            if selected_colony.lower() in stac_id.lower() or stac_id.lower() in selected_colony.lower():
                stac_colony = stac_id
                break

        if stac_colony:
            st.success("Expert annotations available")

            available_years = stac_colonies[stac_colony].get("years", [])
            if available_years:
                st.markdown(f"**Years:** {', '.join(available_years)}")

                latest_year = available_years[-1]
                species_resp = get_stac_species(stac_colony, latest_year)
                species_list = species_resp.get("species", [])

                if species_list:
                    st.markdown(f"**Counts ({latest_year}):**")
                    for sp in species_list[:5]:
                        st.markdown(f"- {sp['name']}: {sp['total_birds']:,}")

                    if st.button("🔵 View Expert Dots", use_container_width=True):
                        with st.spinner("Loading aerial data..."):
                            mosaic_b64 = get_mosaic_preview(stac_colony, latest_year)

                            if mosaic_b64:
                                st.markdown(f"#### Aerial Survey ({latest_year})")
                                img_bytes = base64.b64decode(mosaic_b64)
                                from PIL import Image
                                import io
                                img = Image.open(io.BytesIO(img_bytes))
                                st.image(img, use_container_width=True)
        else:
            st.info("No expert annotations for this colony")

else:  # Composition Analysis
    st.markdown("## 🎨 Species Composition Over Time")
    st.caption(f"Stacked chart showing population shifts ({year_range[0]}-{year_range[1]})")

    composition_df = data["composition"]

    if not composition_df.empty:
        pivot_df = composition_df.pivot(index="Year", columns="SpeciesCode", values="total_birds").fillna(0)

        fig = go.Figure()
        colors = ["#D97757", "#2AB8DC", "#2EC46A", "#F4B942", "#9B59B6",
                  "#E74C3C", "#3498DB", "#1ABC9C", "#F39C12", "#8E44AD"]

        for idx, species in enumerate(pivot_df.columns):
            fig.add_trace(go.Scatter(
                x=pivot_df.index,
                y=pivot_df[species],
                mode="lines",
                name=species,
                stackgroup="one",
                fillcolor=colors[idx % len(colors)],
                line=dict(width=0.5, color=colors[idx % len(colors)]),
                hovertemplate=f"<b>{species}</b><br>Year: %{x}<br>Birds: %{y:,}<extra></extra>"
            ))

        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor="#1A1A1A",
            plot_bgcolor="#2D2D2D",
            height=500,
            xaxis=dict(title="Year", tickmode="linear", dtick=1, gridcolor="#3A3A3A"),
            yaxis=dict(title="Total Birds (Stacked)", gridcolor="#3A3A3A"),
            hovermode="x unified",
            legend=dict(orientation="v", yanchor="top", y=1, xanchor="left", x=1.02, bgcolor="rgba(0,0,0,0.5)")
        )

        st.plotly_chart(fig, use_container_width=True)

        # Composition insights
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("### Dominant Species by Year")
            dominant = composition_df.loc[composition_df.groupby("Year")["total_birds"].idxmax()]
            for _, row in dominant.iterrows():
                st.markdown(f"**{int(row['Year'])}**: {row['SpeciesCode']} ({int(row['total_birds']):,})")

        with col2:
            st.markdown("### Species Diversity")
            diversity = composition_df.groupby("Year")["SpeciesCode"].count().reset_index()

            fig_div = go.Figure()
            fig_div.add_trace(go.Bar(
                x=diversity["Year"],
                y=diversity["SpeciesCode"],
                marker_color="#2AB8DC"
            ))

            fig_div.update_layout(
                template="plotly_dark",
                paper_bgcolor="#1A1A1A",
                plot_bgcolor="#2D2D2D",
                height=250,
                margin=dict(l=10, r=10, t=10, b=10),
                xaxis=dict(tickmode="linear", dtick=1),
                yaxis=dict(title="Species Count"),
                showlegend=False
            )

            st.plotly_chart(fig_div, use_container_width=True)

# ============================================================================
# FOOTER
# ============================================================================

st.markdown("---")
st.markdown("""
<div style="text-align:center; color:#555; font-size:0.8rem; padding:0.5rem">
    <strong>NestTrends</strong> — Comprehensive population intelligence dashboard.
    Maps + Trends + Expert Data. Toggle everything. <strong>Better than static dashboards.</strong>
</div>
""", unsafe_allow_html=True)
