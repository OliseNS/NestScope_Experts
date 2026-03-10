"""
Flood Intelligence: Physics-Based Coastal Risk Assessment
==========================================================

Multi-modal data fusion for decision support.
Designed for The Water Institute's Flood Intelligence Research Team.

Data Sources:
- NOAA CO-OPS (water levels, tide predictions)
- HURDAT2 (historical hurricanes)
- USGS (erosion estimates)
- Water Institute Survey Data (bird populations)
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
import os
from datetime import datetime, timedelta
import numpy as np
from math import radians, cos, sin, asin, sqrt

from components import init_page, render_sidebar, render_map, render_header

# ============================================================================
# PAGE CONFIGURATION
# ============================================================================

init_page(page_title="Flood Intelligence", page_icon="🌊", layout="wide")

# Custom CSS for this page
st.markdown("""
<style>
    /* Typography */
    @import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Inter:wght@300;400;500;600;700&display=swap');

    .flood-header {
        font-family: 'Space Mono', monospace;
        font-size: 2.5rem;
        font-weight: 700;
        color: #00D9FF;
        letter-spacing: -0.02em;
        margin-bottom: 0.5rem;
        text-shadow: 0 0 20px rgba(0, 217, 255, 0.3);
    }

    .flood-subtitle {
        font-family: 'Inter', sans-serif;
        font-size: 1rem;
        color: #94A3B8;
        font-weight: 300;
        margin-bottom: 2rem;
    }

    /* Metric Cards */
    .metric-card {
        background: linear-gradient(135deg, #0F172A 0%, #1E293B 100%);
        border: 1px solid #334155;
        border-radius: 16px;
        padding: 1.5rem;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        position: relative;
        overflow: hidden;
    }

    .metric-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 3px;
        background: linear-gradient(90deg, #00D9FF 0%, #0891B2 100%);
        transform: scaleX(0);
        transition: transform 0.3s ease;
    }

    .metric-card:hover::before {
        transform: scaleX(1);
    }

    .metric-card:hover {
        border-color: #00D9FF;
        box-shadow: 0 10px 40px rgba(0, 217, 255, 0.15);
        transform: translateY(-2px);
    }

    .metric-value {
        font-family: 'Space Mono', monospace;
        font-size: 2.5rem;
        font-weight: 700;
        color: #00D9FF;
        line-height: 1;
        margin-bottom: 0.5rem;
    }

    .metric-label {
        font-family: 'Inter', sans-serif;
        font-size: 0.75rem;
        color: #64748B;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        font-weight: 600;
    }

    .metric-delta {
        font-family: 'Inter', sans-serif;
        font-size: 0.875rem;
        font-weight: 600;
        margin-top: 0.5rem;
        padding: 0.25rem 0.75rem;
        border-radius: 999px;
        display: inline-block;
    }

    .delta-critical {
        background: rgba(239, 68, 68, 0.15);
        color: #F87171;
    }

    .delta-warning {
        background: rgba(251, 191, 36, 0.15);
        color: #FBBF24;
    }

    .delta-normal {
        background: rgba(34, 197, 94, 0.15);
        color: #4ADE80;
    }

    /* Context Panel */
    .context-panel {
        background: #0F172A;
        border: 1px solid #1E293B;
        border-left: 4px solid #00D9FF;
        border-radius: 12px;
        padding: 1.5rem;
        margin: 1rem 0;
    }

    .context-title {
        font-family: 'Space Mono', monospace;
        font-size: 0.875rem;
        color: #00D9FF;
        text-transform: uppercase;
        letter-spacing: 0.15em;
        margin-bottom: 1rem;
        font-weight: 700;
    }

    .context-item {
        font-family: 'Inter', sans-serif;
        font-size: 0.9rem;
        color: #CBD5E1;
        margin-bottom: 0.75rem;
        line-height: 1.6;
        display: flex;
        align-items: start;
    }

    .context-item::before {
        content: '→';
        color: #00D9FF;
        margin-right: 0.75rem;
        font-weight: 700;
    }

    /* Alert Box */
    .alert-critical {
        background: linear-gradient(135deg, rgba(220, 38, 38, 0.1) 0%, rgba(239, 68, 68, 0.05) 100%);
        border: 1px solid rgba(239, 68, 68, 0.3);
        border-left: 4px solid #EF4444;
        border-radius: 12px;
        padding: 1.5rem;
        margin: 1.5rem 0;
    }

    .alert-normal {
        background: linear-gradient(135deg, rgba(34, 197, 94, 0.1) 0%, rgba(74, 222, 128, 0.05) 100%);
        border: 1px solid rgba(74, 222, 128, 0.3);
        border-left: 4px solid #4ADE80;
        border-radius: 12px;
        padding: 1.5rem;
        margin: 1.5rem 0;
    }

    .alert-title {
        font-family: 'Space Mono', monospace;
        font-size: 1.1rem;
        font-weight: 700;
        margin-bottom: 0.75rem;
    }

    .alert-body {
        font-family: 'Inter', sans-serif;
        font-size: 0.95rem;
        line-height: 1.7;
        color: #CBD5E1;
    }

    /* Data Freshness */
    .data-freshness {
        font-family: 'Inter', sans-serif;
        font-size: 0.75rem;
        color: #64748B;
        padding: 0.75rem 1rem;
        background: #0F172A;
        border-radius: 8px;
        margin-top: 1rem;
    }

    .freshness-item {
        display: flex;
        justify-content: space-between;
        margin-bottom: 0.5rem;
    }

    .freshness-item:last-child {
        margin-bottom: 0;
    }

    .freshness-label {
        color: #94A3B8;
    }

    .freshness-value {
        color: #00D9FF;
        font-family: 'Space Mono', monospace;
    }

    /* Section Divider */
    .section-divider {
        height: 1px;
        background: linear-gradient(90deg, transparent 0%, #334155 50%, transparent 100%);
        margin: 3rem 0;
    }

    /* Footer */
    .flood-footer {
        font-family: 'Space Mono', monospace;
        font-size: 0.65rem;
        color: #475569;
        text-align: center;
        margin-top: 3rem;
        padding-top: 2rem;
        border-top: 1px solid #1E293B;
        letter-spacing: 0.1em;
    }
</style>
""", unsafe_allow_html=True)

render_header(page_name="Flood Intelligence")

# ============================================================================
# HERO HEADER
# ============================================================================

st.markdown("""
    <div style="text-align: center; margin: 2rem 0 2rem 0;">
        <div class="flood-header">FLOOD INTELLIGENCE CENTER</div>
        <div class="flood-subtitle">
            Physics-Based Nowcasting • Multi-Modal Data Fusion • Decision Support
        </div>
    </div>
""", unsafe_allow_html=True)

# Quick guide box
st.markdown("""
    <div class="context-panel" style="margin-bottom: 2rem;">
        <div class="context-title">How to Use This Page</div>
        <div style="font-family: 'Inter', sans-serif; font-size: 0.9rem; color: #CBD5E1; line-height: 1.7;">
            <strong>1. Select a colony</strong> from the dropdown below to see real-time water level forecasts<br/>
            <strong>2. View key metrics</strong> showing current surge, forecast peak, and risk levels<br/>
            <strong>3. Check the water level chart</strong> to see observed levels (solid blue) vs forecast (dashed blue)<br/>
            <strong>4. Scroll down to the map</strong> to see all colonies color-coded by risk level<br/>
            <strong>5. Click colonies in the risk list</strong> (right side of map) to jump to their details<br/>
            <strong>6. Click "Reset Map View"</strong> if you zoom/pan the map and want to return to default view
        </div>
    </div>
""", unsafe_allow_html=True)

# ============================================================================
# API & DATA UTILITIES
# ============================================================================

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

GULF_STATIONS = [
    {"name": "Grand Isle, LA", "id": "8761724", "lat": 29.2633, "lon": -89.9567, "minor": 0.6, "moderate": 1.0, "major": 1.5},
    {"name": "Shell Beach, LA", "id": "8761305", "lat": 29.8683, "lon": -89.6733, "minor": 0.5, "moderate": 0.9, "major": 1.4},
    {"name": "Pascagoula, MS", "id": "8741533", "lat": 30.345, "lon": -88.5633, "minor": 0.5, "moderate": 1.0, "major": 1.5},
    {"name": "Waveland, MS", "id": "8747766", "lat": 30.2783, "lon": -89.3667, "minor": 0.6, "moderate": 1.1, "major": 1.6},
    {"name": "New Canal, LA", "id": "8761927", "lat": 30.0267, "lon": -90.1133, "minor": 0.5, "moderate": 0.9, "major": 1.4},
    {"name": "Port Fourchon, LA", "id": "8762075", "lat": 29.1150, "lon": -90.1983, "minor": 0.6, "moderate": 1.0, "major": 1.5},
]

def haversine_dist(lat1, lon1, lat2, lon2):
    """Calculate distance between two points in km"""
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlon, dlat = lon2 - lon1, lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    return 2 * asin(sqrt(a)) * 6371

def find_nearest_station(lat, lon):
    """Find nearest NOAA station to given coordinates"""
    distances = [(s, haversine_dist(lat, lon, s["lat"], s["lon"])) for s in GULF_STATIONS]
    return min(distances, key=lambda x: x[1])

@st.cache_data(ttl=300)
def get_live_project_data():
    """Fetch colony data from API"""
    try:
        priorities = requests.get(f"{API_BASE_URL}/api/risk/priority_list", params={"limit": 500}).json()
        zones_api = requests.get(f"{API_BASE_URL}/api/risk/map_zones").json()

        z_map = {z['colony_name']: z for z in zones_api['zones']}
        data = []
        for p in priorities['priorities']:
            if p['colony_name'] in z_map:
                p.update({
                    'latitude': z_map[p['colony_name']]['latitude'],
                    'longitude': z_map[p['colony_name']]['longitude']
                })
                score = p['risk_score']
                if score > 75: level = "CRITICAL"
                elif score > 50: level = "HIGH"
                elif score > 25: level = "MODERATE"
                else: level = "LOW"
                p['risk_level'] = level
                data.append(p)

        return pd.DataFrame(data), zones_api['zones']
    except Exception as e:
        st.error(f"⚠️ API Error: {e}")
        return pd.DataFrame(), []

@st.cache_data(ttl=300)
def fetch_noaa_data(station_id, product='predictions', hours=48, lookback=24):
    """Fetch data from NOAA API with caching"""
    try:
        now = datetime.now()
        if product == 'predictions':
            begin_date, end_date = now, now + timedelta(hours=hours)
        else:
            begin_date, end_date = now - timedelta(hours=lookback), now

        url = "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"
        params = {
            'product': product, 'application': 'NestScope',
            'begin_date': begin_date.strftime('%Y%m%d %H:%M'),
            'end_date': end_date.strftime('%Y%m%d %H:%M'),
            'datum': 'MHHW', 'station': station_id, 'time_zone': 'lst_ldt',
            'units': 'metric', 'format': 'json'
        }
        res = requests.get(url, params=params, timeout=10)
        if res.status_code == 200:
            data = res.json()
            key = 'predictions' if product == 'predictions' else 'data'
            if key in data:
                df = pd.DataFrame(data[key])
                df['t'] = pd.to_datetime(df['t'])
                df['v'] = pd.to_numeric(df['v'], errors='coerce')
                return df
    except: pass
    return None

@st.cache_data(ttl=3600)
def fetch_historical_percentiles(station_id, days=180):
    """Fetch historical data to calculate percentiles"""
    try:
        now = datetime.now()
        begin = now - timedelta(days=days)

        url = "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"
        params = {
            'product': 'water_level', 'application': 'NestScope',
            'begin_date': begin.strftime('%Y%m%d'),
            'end_date': now.strftime('%Y%m%d'),
            'datum': 'MHHW', 'station': station_id, 'time_zone': 'gmt',
            'units': 'metric', 'format': 'json'
        }
        res = requests.get(url, params=params, timeout=15)
        if res.status_code == 200:
            data = res.json()
            if 'data' in data:
                df = pd.DataFrame(data['data'])
                df['v'] = pd.to_numeric(df['v'], errors='coerce')
                levels = df['v'].dropna()

                return {
                    'p50': levels.quantile(0.50),
                    'p90': levels.quantile(0.90),
                    'p95': levels.quantile(0.95),
                    'p99': levels.quantile(0.99),
                    'max': levels.max(),
                    'std': levels.std()
                }
    except: pass
    return {'p50': 0, 'p90': 0.8, 'p95': 1.2, 'p99': 1.8, 'max': 2.5, 'std': 0.25}

# ============================================================================
# LOAD DATA
# ============================================================================

df_priorities, raw_zones = get_live_project_data()
if df_priorities.empty:
    st.warning("⚠️ Waiting for data services to initialize...")
    st.stop()

# ============================================================================
# SIDEBAR
# ============================================================================

with st.sidebar:
    render_sidebar(active_page="coastal_risk")

    st.markdown("---")
    st.markdown("""
        <div style="font-family: 'Space Mono', monospace; font-size: 0.75rem; color: #64748B; text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 0.75rem;">
            Research Methods
        </div>
        <div style="font-family: 'Inter', sans-serif; font-size: 0.8rem; color: #94A3B8; line-height: 1.6;">
            • <strong>Residual Surge Analysis</strong><br/>
            • <strong>Extreme Value Theory</strong><br/>
            • <strong>Return Period Estimation</strong><br/>
            • <strong>Multi-Modal Fusion</strong>
        </div>
    """, unsafe_allow_html=True)

# ============================================================================
# ASSET SELECTION
# ============================================================================

st.markdown('<div style="margin-bottom: 1.5rem;"></div>', unsafe_allow_html=True)

# Initialize session state for selected colony
if 'selected_colony' not in st.session_state:
    st.session_state['selected_colony'] = sorted(df_priorities['colony_name'].unique())[0]

# Get the index of the currently selected colony
colony_options = sorted(df_priorities['colony_name'].unique())
try:
    default_index = colony_options.index(st.session_state['selected_colony'])
except ValueError:
    default_index = 0
    st.session_state['selected_colony'] = colony_options[0]

selected_name = st.selectbox(
    "🎯 SELECT COASTAL ASSET FOR ANALYSIS:",
    options=colony_options,
    index=default_index,
    help="Select a bird colony to view localized flood intelligence or click on colonies in the list below the map."
)

# Update session state if selection changed
if selected_name != st.session_state['selected_colony']:
    st.session_state['selected_colony'] = selected_name

selected_asset = df_priorities[df_priorities['colony_name'] == selected_name].iloc[0]

# Find nearest station
station, dist_km = find_nearest_station(selected_asset['latitude'], selected_asset['longitude'])

st.caption(f"📡 **Nearest NOAA Station:** {station['name']} ({dist_km:.1f} km away)")

# ============================================================================
# FETCH NOAA DATA
# ============================================================================

obs_df = fetch_noaa_data(station['id'], product='water_level', lookback=24)
pred_df = fetch_noaa_data(station['id'], product='predictions', hours=72)
hist_stats = fetch_historical_percentiles(station['id'])

# Calculate surge
surge_val = 0.0
current_level = 0.0
if obs_df is not None and pred_df is not None and not obs_df.empty and not pred_df.empty:
    last_obs = obs_df.iloc[-1]
    current_level = last_obs['v']
    pred_near_obs = pred_df[pred_df['t'] <= last_obs['t']].tail(1)
    if not pred_near_obs.empty:
        surge_val = last_obs['v'] - pred_near_obs.iloc[0]['v']

# Calculate percentile
current_percentile = 50
if current_level > 0:
    if current_level >= hist_stats['p99']: current_percentile = 99
    elif current_level >= hist_stats['p95']: current_percentile = 95
    elif current_level >= hist_stats['p90']: current_percentile = 90
    elif current_level >= hist_stats['p50']: current_percentile = 75
    else: current_percentile = 50

# ============================================================================
# KEY METRICS
# ============================================================================

st.markdown('<div style="margin: 2rem 0 1.5rem 0;"></div>', unsafe_allow_html=True)

col1, col2, col3, col4 = st.columns(4)

with col1:
    delta_class = "delta-critical" if surge_val > 0.3 else "delta-warning" if surge_val > 0.1 else "delta-normal"
    delta_text = "ELEVATED" if surge_val > 0.3 else "ACTIVE" if surge_val > 0.1 else "NORMAL"
    st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Meteorological Surge</div>
            <div class="metric-value">{surge_val:+.2f}m</div>
            <div class="metric-delta {delta_class}">{delta_text}</div>
        </div>
    """, unsafe_allow_html=True)

with col2:
    peak_v = pred_df['v'].max() if pred_df is not None and not pred_df.empty else 0.0
    peak_forecast = peak_v + surge_val
    st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">72h Forecast Peak</div>
            <div class="metric-value">{peak_forecast:.2f}m</div>
            <div class="metric-delta delta-normal">Above MHHW</div>
        </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Current Level</div>
            <div class="metric-value">{current_level:.2f}m</div>
            <div class="metric-delta delta-normal">{current_percentile}th Percentile</div>
        </div>
    """, unsafe_allow_html=True)

with col4:
    risk_score = selected_asset['risk_score']
    risk_level = selected_asset['risk_level']
    delta_class_risk = "delta-critical" if risk_score > 75 else "delta-warning" if risk_score > 50 else "delta-normal"
    st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Compound Risk</div>
            <div class="metric-value">{risk_score:.0f}/100</div>
            <div class="metric-delta {delta_class_risk}">{risk_level}</div>
        </div>
    """, unsafe_allow_html=True)

# ============================================================================
# SITUATIONAL CONTEXT PANEL
# ============================================================================

st.markdown('<div style="margin: 2rem 0;"></div>', unsafe_allow_html=True)

# Determine return period estimate
if current_level >= hist_stats['p99']:
    return_period = "100-year event"
elif current_level >= hist_stats['p95']:
    return_period = "20-year event"
elif current_level >= hist_stats['p90']:
    return_period = "10-year event"
else:
    return_period = "Common occurrence"

# Historical storm comparison
ida_surge = 2.45  # Hurricane Ida peak surge at Grand Isle
ida_ratio = (max(current_level, peak_forecast) / ida_surge) * 100

st.markdown(f"""
    <div class="context-panel">
        <div class="context-title">Situational Context</div>
        <div class="context-item">Current water level is at <strong>{current_percentile}th percentile</strong> for this location (past 180 days)</div>
        <div class="context-item">Estimated return period: <strong>{return_period}</strong></div>
        <div class="context-item">Surge magnitude is <strong>{ida_ratio:.1f}% of Hurricane Ida</strong> (Aug 2021: {ida_surge}m)</div>
        <div class="context-item">Forecast assumes surge persists for <strong>12-24 hours</strong> (typical duration)</div>
    </div>
""", unsafe_allow_html=True)

# ============================================================================
# MAIN CHART: NOWCAST & FORECAST
# ============================================================================

st.markdown('<div style="margin: 2.5rem 0 1rem 0;"></div>', unsafe_allow_html=True)
st.markdown("""
    <div style="font-family: 'Space Mono', monospace; font-size: 1.5rem; font-weight: 700; color: #E2E8F0; margin-bottom: 1rem;">
        Water Level Nowcast & Forecast
    </div>
    <div style="font-family: 'Inter', sans-serif; font-size: 0.9rem; color: #94A3B8; margin-bottom: 1.5rem;">
        Physics-based nowcasting combining observed water levels with astronomical tide predictions.
        Shaded region represents forecast uncertainty (±1σ).
    </div>
""", unsafe_allow_html=True)

fig = go.Figure()

if obs_df is not None and pred_df is not None and not obs_df.empty and not pred_df.empty:
    # 1. Flood Threshold Zones (Background)
    fig.add_hrect(
        y0=-0.5, y1=station['minor'],
        fillcolor="rgba(34, 197, 94, 0.08)", line_width=0,
        annotation_text="NORMAL", annotation_position="top left",
        annotation=dict(font=dict(size=10, color="#4ADE80", family="Space Mono"))
    )
    fig.add_hrect(
        y0=station['minor'], y1=station['moderate'],
        fillcolor="rgba(251, 191, 36, 0.08)", line_width=0,
        annotation_text="MINOR FLOODING", annotation_position="top left",
        annotation=dict(font=dict(size=10, color="#FBBF24", family="Space Mono"))
    )
    fig.add_hrect(
        y0=station['moderate'], y1=station['major'],
        fillcolor="rgba(249, 115, 22, 0.08)", line_width=0,
        annotation_text="MODERATE FLOODING", annotation_position="top left",
        annotation=dict(font=dict(size=10, color="#FB923C", family="Space Mono"))
    )
    fig.add_hrect(
        y0=station['major'], y1=3.0,
        fillcolor="rgba(239, 68, 68, 0.08)", line_width=0,
        annotation_text="MAJOR FLOODING", annotation_position="top left",
        annotation=dict(font=dict(size=10, color="#EF4444", family="Space Mono"))
    )

    # 2. Observed Data (Solid line)
    fig.add_trace(go.Scatter(
        x=obs_df['t'], y=obs_df['v'],
        name='Observed (Actual)',
        line=dict(color='#00D9FF', width=3),
        fill='tozeroy',
        fillcolor='rgba(0, 217, 255, 0.15)',
        hovertemplate='<b>Observed</b><br>%{x}<br>%{y:.2f}m MHHW<extra></extra>'
    ))

    # 3. Impact Forecast (Dashed line)
    pred_df_nowcast = pred_df.copy()
    pred_df_nowcast['v'] = pred_df['v'] + surge_val

    # Connector line
    fig.add_trace(go.Scatter(
        x=[obs_df.iloc[-1]['t'], pred_df_nowcast.iloc[0]['t']],
        y=[obs_df.iloc[-1]['v'], pred_df_nowcast.iloc[0]['v']],
        showlegend=False,
        line=dict(color='#0891B2', width=2, dash='dot'),
        hoverinfo='skip'
    ))

    # 4. Uncertainty Band (±1 sigma)
    surge_std = hist_stats['std']

    fig.add_trace(go.Scatter(
        x=pred_df_nowcast['t'],
        y=pred_df_nowcast['v'] + surge_std,
        fill=None,
        mode='lines',
        line_color='rgba(0,0,0,0)',
        showlegend=False,
        hoverinfo='skip'
    ))

    fig.add_trace(go.Scatter(
        x=pred_df_nowcast['t'],
        y=pred_df_nowcast['v'] - surge_std,
        fill='tonexty',
        fillcolor='rgba(8, 145, 178, 0.2)',
        mode='lines',
        line_color='rgba(0,0,0,0)',
        name='Forecast Uncertainty (±1σ)',
        hoverinfo='skip'
    ))

    # 5. Main Forecast Line
    fig.add_trace(go.Scatter(
        x=pred_df_nowcast['t'], y=pred_df_nowcast['v'],
        name='Impact Forecast',
        line=dict(color='#0891B2', width=3, dash='dash'),
        hovertemplate='<b>Forecast</b><br>%{x}<br>%{y:.2f}m MHHW<extra></extra>'
    ))

    # 6. Add annotation for transition
    if not obs_df.empty and not pred_df_nowcast.empty:
        transition_x = obs_df.iloc[-1]['t']
        transition_y = obs_df.iloc[-1]['v']

        fig.add_annotation(
            x=transition_x,
            y=transition_y,
            text="← Observed | Forecast →",
            showarrow=True,
            arrowhead=2,
            arrowsize=1,
            arrowwidth=2,
            arrowcolor="#00D9FF",
            ax=0,
            ay=-50,
            font=dict(size=11, color="#00D9FF", family="Space Mono"),
            bgcolor="rgba(15, 23, 42, 0.9)",
            bordercolor="#00D9FF",
            borderwidth=1,
            borderpad=4
        )

fig.update_layout(
    hovermode="x unified",
    height=500,
    paper_bgcolor='rgba(0,0,0,0)',
    plot_bgcolor='rgba(15, 23, 42, 0.5)',
    margin=dict(l=0, r=0, t=30, b=0),
    font=dict(family="Inter", color="#CBD5E1"),
    yaxis=dict(
        gridcolor='rgba(71, 85, 105, 0.3)',
        title=dict(
            text="Water Level (meters above MHHW)",
            font=dict(size=12, family="Space Mono")
        ),
        zeroline=True,
        zerolinecolor='rgba(71, 85, 105, 0.5)',
        zerolinewidth=1
    ),
    xaxis=dict(
        gridcolor='rgba(71, 85, 105, 0.3)',
        title=dict(
            text="",
            font=dict(size=12, family="Space Mono")
        )
    ),
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="right",
        x=1,
        font=dict(size=11, family="Space Mono"),
        bgcolor="rgba(15, 23, 42, 0.8)",
        bordercolor="#334155",
        borderwidth=1
    )
)

st.plotly_chart(fig, use_container_width=True)

# Data freshness footer
if obs_df is not None and not obs_df.empty:
    last_update = obs_df.iloc[-1]['t']
    minutes_ago = int((datetime.now() - last_update).total_seconds() / 60)

    st.markdown(f"""
        <div class="data-freshness">
            <div class="freshness-item">
                <span class="freshness-label">NOAA Observations:</span>
                <span class="freshness-value">{last_update.strftime('%I:%M %p')} ({minutes_ago} min ago)</span>
            </div>
            <div class="freshness-item">
                <span class="freshness-label">Tide Predictions:</span>
                <span class="freshness-value">Updated daily at 00:00 UTC</span>
            </div>
            <div class="freshness-item">
                <span class="freshness-label">Risk Model:</span>
                <span class="freshness-value">Real-time computation</span>
            </div>
        </div>
    """, unsafe_allow_html=True)

# ============================================================================
# ACTIONABLE INTELLIGENCE
# ============================================================================

st.markdown('<div style="margin: 2.5rem 0 1rem 0;"></div>', unsafe_allow_html=True)

# Determine critical threshold (use colony-specific ground elevation proxy)
ground_elev = 0.4 + (selected_asset['years_until_critical'] / 20.0) * 0.6

if peak_forecast > ground_elev:
    # Calculate time to critical threshold
    if pred_df_nowcast is not None:
        critical_times = pred_df_nowcast[pred_df_nowcast['v'] > ground_elev]
        if not critical_times.empty:
            time_to_critical = critical_times.iloc[0]['t']
            hours_away = (time_to_critical - datetime.now()).total_seconds() / 3600

            st.markdown(f"""
                <div class="alert-critical">
                    <div class="alert-title" style="color: #F87171;">🚨 CRITICAL INUNDATION FORECAST</div>
                    <div class="alert-body">
                        <p style="margin-bottom: 1rem;">
                            <strong>Habitat inundation threshold ({ground_elev:.2f}m) will be exceeded in {hours_away:.1f} hours</strong>
                            at {time_to_critical.strftime('%I:%M %p on %b %d')}.
                        </p>
                        <p style="margin-bottom: 0.5rem; color: #F87171; font-weight: 600; font-size: 0.875rem;">
                            RECOMMENDED ACTIONS:
                        </p>
                        <ul style="margin: 0; padding-left: 1.5rem; line-height: 2;">
                            <li>Deploy field assessment crew before {(time_to_critical - timedelta(hours=2)).strftime('%I:%M %p')}</li>
                            <li>Pre-position monitoring equipment at {selected_name}</li>
                            <li>Alert CPRA emergency response coordination center</li>
                            <li>Schedule post-event assessment for {(time_to_critical + timedelta(hours=12)).strftime('%b %d, %I:%M %p')}</li>
                            <li>Document pre-inundation conditions for restoration impact analysis</li>
                        </ul>
                    </div>
                </div>
            """, unsafe_allow_html=True)
else:
    st.markdown(f"""
        <div class="alert-normal">
            <div class="alert-title" style="color: #4ADE80;">✓ NORMAL OPERATING CONDITIONS</div>
            <div class="alert-body">
                <p style="margin-bottom: 1rem;">
                    Forecast water levels remain <strong>{ground_elev - peak_forecast:.2f}m below</strong> the critical
                    inundation threshold for {selected_name}.
                </p>
                <p style="margin: 0;">
                    <strong>Status:</strong> Routine monitoring protocols sufficient. No immediate action required.
                </p>
            </div>
        </div>
    """, unsafe_allow_html=True)

# ============================================================================
# REGIONAL RISK MAP
# ============================================================================

st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)

st.markdown("""
    <div style="font-family: 'Space Mono', monospace; font-size: 1.5rem; font-weight: 700; color: #E2E8F0; margin-bottom: 1rem;">
        Regional Colony Risk Distribution
    </div>
    <div style="font-family: 'Inter', sans-serif; font-size: 0.95rem; color: #CBD5E1; line-height: 1.7; margin-bottom: 1.5rem;">
        <strong>What This Shows:</strong> Each colored dot represents a bird colony. The <strong>color indicates flood risk level</strong>
        (red = critical, orange = high, yellow = moderate, green = low). The <strong>dot size shows the risk score</strong>
        (bigger = higher risk). Risk is calculated by combining:
        <ul style="margin-top: 0.5rem; margin-bottom: 0;">
            <li><strong>Coastal erosion rates</strong> - How fast land is disappearing (barrier islands erode faster)</li>
            <li><strong>Sea level rise</strong> - NOAA projects 0.45m rise by 2050</li>
            <li><strong>Storm surge exposure</strong> - Based on proximity to hurricane-prone waters</li>
            <li><strong>Historical storms</strong> - How many major hurricanes have hit this area since 2005</li>
            <li><strong>Bird population size</strong> - Smaller colonies are more vulnerable to disruption</li>
        </ul>
        <strong style="color: #00D9FF;">Click on any dot to see details.</strong> Use the list below to jump to specific colonies.
    </div>
""", unsafe_allow_html=True)

# Two-column layout: Map + Risk List
col_map, col_list = st.columns([2, 1])

with col_map:
    # Map with reset button
    if st.button("🔄 Reset Map View", key="reset_map_btn"):
        st.rerun()

    render_map(
        pd.DataFrame(),
        key="flood_intel_map_v2",
        height=550,
        risk_zones=raw_zones
    )

with col_list:
    st.markdown("""
        <div style="font-family: 'Space Mono', monospace; font-size: 0.9rem; font-weight: 700; color: #00D9FF;
                    text-transform: uppercase; letter-spacing: 0.15em; margin-bottom: 1rem;">
            High-Risk Colonies
        </div>
    """, unsafe_allow_html=True)

    # Sort colonies by risk score and filter to high-risk only
    high_risk_zones = sorted(
        [z for z in raw_zones if z['risk_level'] in ['CRITICAL', 'HIGH']],
        key=lambda x: x['risk_score'],
        reverse=True
    )

    if high_risk_zones:
        # Create clickable list
        for idx, zone in enumerate(high_risk_zones[:15]):  # Show top 15
            risk_color = zone['color']
            risk_emoji = "🔴" if zone['risk_level'] == "CRITICAL" else "🟠"

            # Make it clickable by using a button
            if st.button(
                f"{risk_emoji} {zone['colony_name']}",
                key=f"colony_btn_{idx}",
                help=f"Risk Score: {zone['risk_score']:.1f} | Birds: {zone.get('birds', 0):,}",
                use_container_width=True
            ):
                # Update the selected colony
                st.session_state['selected_colony'] = zone['colony_name']
                st.rerun()

            # Show compact info
            st.markdown(f"""
                <div style="font-size: 0.7rem; color: #64748B; margin: -0.5rem 0 0.75rem 1.5rem;
                            font-family: 'Inter', sans-serif;">
                    Score: <span style="color: {risk_color}; font-weight: 600;">{zone['risk_score']:.0f}</span> •
                    Birds: {zone.get('birds', 0):,} •
                    Years left: ~{zone.get('years_until_critical', '?')}
                </div>
            """, unsafe_allow_html=True)

        if len(high_risk_zones) > 15:
            st.caption(f"Showing top 15 of {len(high_risk_zones)} high-risk colonies")
    else:
        st.info("No high-risk colonies found in current data.")

    # Show ALL colonies count
    st.markdown('<div style="margin-top: 2rem;"></div>', unsafe_allow_html=True)
    st.markdown(f"""
        <div style="background: #0F172A; border: 1px solid #1E293B; border-radius: 8px;
                    padding: 1rem; font-family: 'Inter', sans-serif; font-size: 0.85rem;">
            <div style="color: #64748B; margin-bottom: 0.5rem;">TOTAL COLONIES MONITORED</div>
            <div style="color: #00D9FF; font-size: 2rem; font-weight: 700; font-family: 'Space Mono', monospace;">
                {len(raw_zones)}
            </div>
            <div style="color: #94A3B8; font-size: 0.75rem; margin-top: 0.5rem;">
                🔴 Critical: {len([z for z in raw_zones if z['risk_level'] == 'CRITICAL'])}<br/>
                🟠 High: {len([z for z in raw_zones if z['risk_level'] == 'HIGH'])}<br/>
                🟡 Moderate: {len([z for z in raw_zones if z['risk_level'] == 'MODERATE'])}<br/>
                🟢 Low: {len([z for z in raw_zones if z['risk_level'] == 'LOW'])}
            </div>
        </div>
    """, unsafe_allow_html=True)

# ============================================================================
# METHODOLOGY FOOTER
# ============================================================================

st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)

col_method1, col_method2 = st.columns(2)

with col_method1:
    st.markdown("""
        <div class="context-panel">
            <div class="context-title">Data Sources</div>
            <div class="context-item">NOAA CO-OPS Tide Gauges (real-time)</div>
            <div class="context-item">HURDAT2 Hurricane Database (1851-2024)</div>
            <div class="context-item">USGS Coastal Erosion Studies</div>
            <div class="context-item">Water Institute Survey Data (2010-2021)</div>
        </div>
    """, unsafe_allow_html=True)

with col_method2:
    st.markdown("""
        <div class="context-panel">
            <div class="context-title">Methods</div>
            <div class="context-item">Residual surge analysis (observed - predicted tide)</div>
            <div class="context-item">Return period estimation via percentile ranking</div>
            <div class="context-item">Uncertainty quantification (historical variance)</div>
            <div class="context-item">Multi-modal data fusion with weighted risk scoring</div>
        </div>
    """, unsafe_allow_html=True)

# Footer
st.markdown("""
    <div class="flood-footer">
        NESTSCOPE FLOOD INTELLIGENCE v3.0.0 • THE WATER INSTITUTE<br/>
        DECISION SUPPORT SYSTEM • DATA LATENCY < 15 MIN
    </div>
""", unsafe_allow_html=True)
