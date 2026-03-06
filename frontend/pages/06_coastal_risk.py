"""
Coastal Risk Intelligence Dashboard
Clean, professional, data-driven decision support
"""

import streamlit as st
import pandas as pd
import folium
from folium import Circle
import plotly.graph_objects as go
import requests
import os

from components import init_page, render_header, render_sidebar

# ============================================================================
# PAGE CONFIGURATION
# ============================================================================

init_page(page_title="Coastal Risk Intelligence", page_icon="🌊", layout="wide")

# ============================================================================
# SIDEBAR
# ============================================================================

with st.sidebar:
    render_sidebar(active_page="coastal_risk")

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
# MAIN DASHBOARD
# ============================================================================

# Header
st.markdown("""
    <div style="background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); padding: 2rem; border-radius: 10px; margin-bottom: 2rem;">
        <h1 style="color: white; margin: 0;">🌊 Coastal Risk Intelligence</h1>
        <p style="color: #e0e0e0; margin-top: 0.5rem; font-size: 1.1rem;">
            Louisiana Gulf Coast Bird Colony Risk Assessment & Restoration Priorities
        </p>
    </div>
""", unsafe_allow_html=True)

# Get data
summary = get_risk_summary()
zones = get_risk_zones()
priorities = get_priority_list(limit=10)

# ============================================================================
# SECTION 1: KEY METRICS
# ============================================================================

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        label="🔴 CRITICAL RISK",
        value=summary['critical_colonies'],
        delta=f"{summary['average_years_until_critical']:.0f} years avg until loss",
        delta_color="inverse"
    )

with col2:
    st.metric(
        label="🟡 HIGH RISK",
        value=summary['high_risk_colonies'],
        help="Colonies at high risk within 10-25 years"
    )

with col3:
    st.metric(
        label="🌪️ HURRICANES",
        value=summary['total_hurricanes_since_2005'],
        delta="Since 2005",
        help="Gulf Coast storms from NOAA HURDAT2"
    )

with col4:
    st.metric(
        label="📊 DATA SOURCES",
        value=len(summary['data_sources']),
        help="Multi-modal data fusion"
    )

st.markdown("---")

# ============================================================================
# SECTION 2: RISK MAP
# ============================================================================

st.markdown("### 🗺️ Gulf Coast Risk Zones")
st.caption("Red = Critical (0-10 years), Orange = High (10-25 years), Green = Stable. Click zones for details.")

# Create map
m = folium.Map(
    location=[29.5, -89.5],
    zoom_start=6,
    tiles="CartoDB positron",
    control_scale=True
)

# Add satellite layer
folium.TileLayer(
    tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    attr="Esri",
    name="Satellite",
    overlay=False,
    control=True
).add_to(m)

# Add risk zones
for zone in zones['zones']:
    # Determine color and opacity
    if zone['risk_level'] == 'CRITICAL':
        color = '#FF4444'
        fill_opacity = 0.4
    elif zone['risk_level'] == 'HIGH':
        color = '#FF8C00'
        fill_opacity = 0.3
    else:
        color = '#4CAF50'
        fill_opacity = 0.2

    # Create popup
    popup_html = f"""
        <div style="font-family: sans-serif; min-width: 250px;">
            <h4 style="margin: 0; color: {color};">{zone['colony_name']}</h4>
            <hr style="margin: 8px 0;">
            <p><strong>Risk Score:</strong> {zone['risk_score']}/100</p>
            <p><strong>Status:</strong> <span style="color: {color}; font-weight: bold;">{zone['risk_level']}</span></p>
            <p><strong>Years Until Critical:</strong> {zone['years_until_critical'] if zone['years_until_critical'] else 'N/A'}</p>
            <p><strong>Bird Population:</strong> {zone['birds']:,}</p>
            <p><strong>Species:</strong> {zone['species']}</p>
            <hr style="margin: 8px 0;">
            <p style="font-style: italic; font-size: 0.9em;">{zone['action']}</p>
        </div>
    """

    # Add circle zone
    Circle(
        location=[zone['latitude'], zone['longitude']],
        radius=zone['radius_km'] * 1000,  # Convert km to meters
        color=color,
        fill=True,
        fill_color=color,
        fill_opacity=fill_opacity,
        weight=2,
        popup=folium.Popup(popup_html, max_width=300),
        tooltip=f"{zone['colony_name']} - {zone['risk_level']}"
    ).add_to(m)

folium.LayerControl().add_to(m)

# Display map
try:
    from streamlit_folium import st_folium
    map_data = st_folium(m, width=None, height=600)
except ImportError:
    st.components.v1.html(m._repr_html_(), height=600)

st.markdown("---")

# ============================================================================
# SECTION 3: PRIORITY ACTIONS
# ============================================================================

st.markdown("### 🎯 Top 10 Restoration Priorities")
st.caption("Ranked by urgency: years until uninhabitable + risk score")

# Create priority table
priority_df = pd.DataFrame(priorities['priorities'])

# Format for display
display_df = priority_df[['rank', 'colony_name', 'years_until_critical', 'bird_population', 'erosion_rate', 'estimated_cost_usd', 'recommended_action']]
display_df.columns = ['#', 'Colony', 'Years Until Loss', 'Birds', 'Erosion (m/yr)', 'Est. Cost ($)', 'Action']

# Color-code by rank
def color_rank(val):
    if val <= 3:
        return 'background-color: #ffcccc'
    elif val <= 6:
        return 'background-color: #ffe6cc'
    else:
        return ''

styled_df = display_df.style.applymap(color_rank, subset=['#']).format({
    'Birds': '{:,}',
    'Est. Cost ($)': '${:,}',
    'Erosion (m/yr)': '{:.1f}'
})

st.dataframe(styled_df, use_container_width=True, height=400)

# Download button
csv = priority_df.to_csv(index=False)
st.download_button(
    label="📥 Download Full Assessment (CSV)",
    data=csv,
    file_name="coastal_restoration_priorities.csv",
    mime="text/csv"
)

st.markdown("---")

# ============================================================================
# SECTION 4: DATA FUSION EXAMPLE
# ============================================================================

st.markdown("### 📊 How We Calculate Risk: Multi-Modal Data Fusion")
st.caption("Example: Top priority colony showing how different data sources combine")

# Get data fusion for top priority
top_colony = priorities['priorities'][0]['colony_name']
fusion_data = get_data_fusion(top_colony)

col_left, col_right = st.columns([2, 1])

with col_left:
    st.markdown(f"#### {fusion_data['colony_name']}")
    st.markdown(f"**Risk Score:** {fusion_data['combined_score']}/100")
    st.markdown(f"**Status:** <span style='color: #FF4444; font-weight: bold;'>{fusion_data['risk_level']}</span>", unsafe_allow_html=True)

    # Data sources breakdown
    st.markdown("**Data Sources:**")

    sources = fusion_data['data_sources']

    for key, source in sources.items():
        with st.expander(f"**{key.replace('_', ' ').title()}**: {source['value']} {source['unit']}", expanded=False):
            st.write(f"**Source:** {source['source']}")
            st.write(f"**Weight in Algorithm:** {source['weight']*100}%")
            st.write(f"**Impact Level:** {source['impact']}")

with col_right:
    # Visual flowchart
    st.markdown("**Risk Calculation:**")

    fig = go.Figure()

    fig.add_trace(go.Funnel(
        name='Data Sources',
        y=list(fusion_data['data_sources'].keys()),
        x=[source['weight'] for source in fusion_data['data_sources'].values()],
        textinfo="value+percent initial"
    ))

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#1A1A1A",
        height=400,
        showlegend=False
    )

    st.plotly_chart(fig, use_container_width=True)

    st.markdown(f"**Final Score:** {fusion_data['combined_score']}/100")
    st.markdown(f"**Action Required:** {fusion_data['recommended_action']}")

st.markdown("---")

# ============================================================================
# SECTION 5: FUTURE PROJECTIONS
# ============================================================================

st.markdown("### 🔮 Future Scenarios: What Happens Next")
st.caption("Select a year to see projected colony status under NOAA sea level rise scenarios")

col_year, col_scenario = st.columns([2, 1])

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
        index=1,
        help="NOAA sea level rise scenarios"
    )

# Get projection
projection = get_future_projection(selected_year, scenario)

# Show summary
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        "Submerged",
        f"{projection['summary']['submerged']} colonies",
        delta=f"{(projection['summary']['submerged']/projection['summary']['total_colonies']*100):.0f}%",
        delta_color="inverse"
    )

with col2:
    st.metric(
        "At Risk",
        f"{projection['summary']['at_risk']} colonies",
        help="Flooded during typical storms"
    )

with col3:
    st.metric(
        "Viable",
        f"{projection['summary']['viable']} colonies",
        delta_color="normal"
    )

with col4:
    st.metric(
        "Bird Loss",
        f"{projection['summary']['bird_population_loss_pct']:.0f}%",
        delta="Population decline",
        delta_color="inverse"
    )

# Create projection map
st.markdown(f"**Map: {selected_year} Projection ({scenario.title()} Scenario)**")

m2 = folium.Map(
    location=[29.5, -89.5],
    zoom_start=6,
    tiles="CartoDB positron"
)

# Add colonies with status colors
for colony in projection['colonies'][:100]:  # Limit for performance
    if colony['status'] == 'submerged':
        color = '#666666'
        icon = 'remove'
    elif colony['status'] == 'at_risk':
        color = '#FFA500'
        icon = 'warning'
    else:
        color = '#4CAF50'
        icon = 'ok'

    folium.Marker(
        location=[colony['latitude'], colony['longitude']],
        icon=folium.Icon(color='gray' if colony['status'] == 'submerged' else 'orange' if colony['status'] == 'at_risk' else 'green', icon=icon),
        popup=f"{colony['colony_name']}<br>Status: {colony['status'].title()}<br>Area: {colony['projected_area_m2']:.0f}m²",
        tooltip=colony['colony_name']
    ).add_to(m2)

try:
    from streamlit_folium import st_folium
    st_folium(m2, width=None, height=500)
except ImportError:
    st.components.v1.html(m2._repr_html_(), height=500)

# ============================================================================
# FOOTER
# ============================================================================

st.markdown("---")
st.markdown("""
    <div style="text-align: center; color: #666; padding: 1rem;">
        <strong>Data Sources:</strong> NOAA Sea Level Rise Viewer | USGS Coastal Erosion Study (2017-1051) |
        NOAA HURDAT2 Hurricane Database | Water Institute Bird Survey Data (2010-2021)
        <br><br>
        <em>This tool provides decision support for coastal restoration prioritization.
        All projections based on peer-reviewed scientific models.</em>
    </div>
""", unsafe_allow_html=True)
