"""
Automated Flood Intelligence Platform
Real-time multi-modal data fusion for coastal hazard monitoring
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
import os
from datetime import datetime

from components import init_page, render_header, render_sidebar, render_map

# ============================================================================
# PAGE CONFIGURATION
# ============================================================================

init_page(page_title="Flood Intelligence", page_icon="🌊", layout="wide")

# ============================================================================
# SIDEBAR
# ============================================================================

with st.sidebar:
    render_sidebar(active_page="coastal_risk")

    st.markdown("---")
    st.markdown("### System Status")
    st.success("All systems operational")
    st.caption(f"Updated {datetime.now().strftime('%H:%M:%S')}")

    st.markdown("---")
    st.markdown("### Data Sources")
    st.markdown("• NOAA Sea Level Rise  \n• USGS Coastal Erosion  \n• HURDAT2 Hurricanes  \n• Bird Survey Data  \n• Geospatial Analytics")

# ============================================================================
# API CLIENT
# ============================================================================

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

@st.cache_data(ttl=3600)
def get_risk_summary():
    response = requests.get(f"{API_BASE_URL}/api/risk/summary")
    return response.json()

@st.cache_data(ttl=3600)
def get_risk_zones():
    response = requests.get(f"{API_BASE_URL}/api/risk/map_zones")
    return response.json()

@st.cache_data(ttl=3600)
def get_priority_list(limit=10):
    response = requests.get(f"{API_BASE_URL}/api/risk/priority_list", params={"limit": limit})
    return response.json()

@st.cache_data(ttl=3600)
def get_data_fusion(colony_name):
    response = requests.get(f"{API_BASE_URL}/api/risk/data_sources/{colony_name}")
    return response.json()

@st.cache_data(ttl=3600)
def get_future_projection(year, scenario="intermediate"):
    response = requests.get(f"{API_BASE_URL}/api/risk/projection/{year}", params={"scenario": scenario})
    return response.json()

# ============================================================================
# HEADER
# ============================================================================

st.title("🌊 Automated Flood Intelligence")
st.caption("Real-time multi-modal data fusion for coastal hazard monitoring and prediction")
st.markdown("")

# Load data
try:
    summary = get_risk_summary()
    zones = get_risk_zones()
    priorities = get_priority_list(limit=10)
except Exception as e:
    st.error(f"Unable to load data: {str(e)}")
    st.stop()

# ============================================================================
# SECTION 1: KEY METRICS
# ============================================================================

st.subheader("Live System Metrics")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        "Critical Risk Colonies",
        summary['critical_colonies'],
        delta="Immediate action needed",
        delta_color="inverse",
        help="Colonies at risk within 0-10 years"
    )

with col2:
    st.metric(
        "High Risk Colonies",
        summary['high_risk_colonies'],
        help="Colonies at risk within 10-25 years"
    )

with col3:
    st.metric(
        "Hurricanes Since 2005",
        summary['total_hurricanes_since_2005'],
        help="Gulf Coast storms from NOAA HURDAT2"
    )

with col4:
    st.metric(
        "Active Data Sources",
        len(summary['data_sources']),
        help="Multi-modal data streams"
    )

st.markdown("---")

# ============================================================================
# SECTION 2: MULTI-MODAL DATA FUSION
# ============================================================================

st.subheader("Multi-Modal Data Fusion")
st.caption("How different data sources combine to assess risk")

# Get top priority colony
top_colony = priorities['priorities'][0]['colony_name']
fusion_data = get_data_fusion(top_colony)

col_left, col_right = st.columns([2, 1])

with col_left:
    st.markdown(f"**Example: {fusion_data['colony_name']}**")

    # Data sources table
    sources_data = []
    for key, source in fusion_data['data_sources'].items():
        sources_data.append({
            "Data Source": key.replace('_', ' ').title(),
            "Value": f"{source['value']} {source['unit']}",
            "Weight": f"{source['weight']*100:.0f}%",
            "Impact": source['impact'],
            "Origin": source['source']
        })

    sources_df = pd.DataFrame(sources_data)

    st.dataframe(
        sources_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Impact": st.column_config.TextColumn(
                "Impact",
                help="Severity of this factor"
            )
        }
    )

with col_right:
    st.metric("Final Risk Score", f"{fusion_data['combined_score']}/100")
    st.metric("Risk Level", fusion_data['risk_level'])

    st.info(f"**Recommendation:** {fusion_data['recommended_action']}")

st.markdown("")
st.caption("**How it works:** Each data source contributes to the overall risk score based on its assigned weight. High-impact factors like erosion rate and sea level rise carry more weight in the calculation.")

st.markdown("---")

# ============================================================================
# SECTION 3: INTERACTIVE RISK MAP
# ============================================================================

st.subheader("Gulf Coast Risk Zones")
st.caption("Red = Critical (0-10 years) • Orange = High (10-25 years) • Green = Stable")

render_map(
    pd.DataFrame(),
    key="risk_zones_map",
    height=500,
    risk_zones=zones['zones']
)

st.markdown("---")

# ============================================================================
# SECTION 4: PRIORITY RESTORATION QUEUE
# ============================================================================

st.subheader("Priority Restoration Sites")
st.caption("Ranked by urgency using multi-criteria decision analysis")

priority_df = pd.DataFrame(priorities['priorities'])

# Format for display
display_cols = ['rank', 'colony_name', 'years_until_critical', 'bird_population_2026', 'erosion_rate', 'estimated_cost_usd']
display_df = priority_df[display_cols].copy()
display_df.columns = ['Rank', 'Colony', 'Years Until Critical', 'Birds (2026)', 'Erosion (m/yr)', 'Est. Cost (USD)']

# Format numbers safely
display_df['Years Until Critical'] = display_df['Years Until Critical'].apply(
    lambda x: f"{int(x)}" if pd.notna(x) else "N/A"
)
display_df['Birds (2026)'] = display_df['Birds (2026)'].apply(
    lambda x: f"{int(x):,}" if pd.notna(x) else "N/A"
)
display_df['Erosion (m/yr)'] = display_df['Erosion (m/yr)'].apply(
    lambda x: f"{x:.1f}" if pd.notna(x) else "N/A"
)
display_df['Est. Cost (USD)'] = display_df['Est. Cost (USD)'].apply(
    lambda x: f"${int(x):,}" if pd.notna(x) else "N/A"
)

st.dataframe(
    display_df,
    use_container_width=True,
    hide_index=True,
    height=400
)

# Download
csv = priority_df.to_csv(index=False)
st.download_button(
    "📥 Download Complete Assessment",
    data=csv,
    file_name="coastal_restoration_priorities.csv",
    mime="text/csv"
)

# Show detailed cards for top 3
st.markdown("#### Top 3 Priority Details")

for idx, row in priority_df.head(3).iterrows():
    with st.expander(f"#{row['rank']} - {row['colony_name']}", expanded=idx==0):
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            years = row['years_until_critical']
            years_display = f"{int(years)} years" if pd.notna(years) else "N/A"
            st.metric("Years Until Critical", years_display)

        with col2:
            birds = row['bird_population_2026']
            birds_display = f"{int(birds):,}" if pd.notna(birds) else "N/A"
            st.metric("Birds at Risk", birds_display)

        with col3:
            erosion = row['erosion_rate']
            erosion_display = f"{erosion:.1f} m/yr" if pd.notna(erosion) else "N/A"
            st.metric("Erosion Rate", erosion_display)

        with col4:
            cost = row['estimated_cost_usd']
            cost_display = f"${int(cost):,}" if pd.notna(cost) else "N/A"
            st.metric("Estimated Cost", cost_display)

        st.info(f"**Recommended Action:** {row['recommended_action']}")

st.markdown("---")

# ============================================================================
# SECTION 5: FUTURE PROJECTIONS
# ============================================================================

st.subheader("Future Scenario Projections")
st.caption("Climate-informed projections using NOAA sea level rise models")

col_year, col_scenario = st.columns([3, 1])

with col_year:
    selected_year = st.select_slider(
        "Projection Year",
        options=[2030, 2050, 2070, 2100],
        value=2050
    )

with col_scenario:
    scenario = st.selectbox(
        "Climate Scenario",
        ["low", "intermediate", "high"],
        index=1
    )

projection = get_future_projection(selected_year, scenario)

# Metrics
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Submerged Colonies", projection['summary']['submerged'], delta="Uninhabitable", delta_color="inverse")

with col2:
    st.metric("At-Risk Colonies", projection['summary']['at_risk'], help="Vulnerable during storms")

with col3:
    st.metric("Viable Colonies", projection['summary']['viable'], delta="Above water", delta_color="normal")

with col4:
    loss_pct = projection['summary']['bird_population_loss_pct']
    st.metric("Population Loss", f"{loss_pct:.0f}%", delta="Est. decline", delta_color="inverse")

st.markdown(f"**Projection for {selected_year} ({scenario.title()} Scenario)**")

render_map(
    pd.DataFrame(),
    key=f"projection_map_{selected_year}_{scenario}",
    height=450,
    future_projections=projection['colonies'][:100]
)

# ============================================================================
# FOOTER
# ============================================================================

st.markdown("---")

st.info("""
**Data Sources:** NOAA Sea Level Rise Viewer • USGS Coastal Erosion Study (2017-1051) •
NOAA HURDAT2 Hurricane Database • Water Institute Bird Survey Data (2010-2021)

**Automated Capabilities:** Multi-modal data fusion • Probabilistic modeling •
Extreme value analysis • Geospatial analytics • Real-time hazard quantification

This platform demonstrates automated flood intelligence using physics-based and data-driven models,
eliminating manual research workflows described in traditional research positions.
""")
