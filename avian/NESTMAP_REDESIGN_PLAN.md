# NestMap Redesign: Erosion & Species Risk Assessment Tool

## Mission
Transform NestMap into a comprehensive tool for The Water Institute to:
1. **Predict erosion patterns** and their impact on bird colonies
2. **Determine species most at risk** of endangerment
3. **Guide restoration priorities** with data-driven insights

## Core Features

### 1. Erosion Risk Mapping
**Data Sources:**
- NOAA sea level rise projections (1-6 ft scenarios)
- USGS coastal change hazards (historical shoreline positions)
- Louisiana Coastal Master Plan erosion forecasts
- NAIP orthoimagery for visual change detection

**Visualizations:**
- Overlay colony locations with erosion risk zones (high/medium/low)
- Historical shoreline change (1850-2024)
- Future shoreline projections (2030, 2050, 2070)
- Colony vulnerability scores based on elevation and erosion rates

### 2. Species Risk Assessment
**Metrics:**
- Population trend (2010-2021): declining/stable/increasing
- Habitat vulnerability: % of nesting colonies in high-erosion zones
- Nesting success rate trends
- Range contraction/expansion analysis
- Conservation status integration (IUCN, state/federal listings)

**Risk Categories:**
- **Critical**: Declining population + high erosion risk + limited habitat
- **Endangered**: Steep decline or severe habitat loss
- **Vulnerable**: Moderate decline or erosion exposure
- **Stable**: Increasing or stable populations in secure habitat

### 3. Temporal Analysis Dashboard
**Components:**
- Multi-species population trends (2010-2021) with 2030/2050 projections
- Colony persistence analysis (which colonies disappeared? when?)
- Correlation with major storms (Katrina, Rita, Isaac, Harvey, Ida)
- Seasonal breeding success by year
- Climate correlation (sea level, temperature, precipitation)

### 4. Predictive Analytics
**Models:**
- Population projections using exponential/logistic growth models
- Habitat loss forecasting based on erosion rates
- Colony viability assessment (will it still exist in 10/20/50 years?)
- Species distribution modeling under climate scenarios
- Restoration ROI calculator (birds gained per $ invested)

### 5. Restoration Priority Mapping
**Features:**
- Heatmap of restoration value (species diversity × population × risk)
- Optimal restoration site identification (low erosion + high connectivity)
- Cost-benefit analysis integration
- Success probability scoring
- Funding allocation optimizer

## Technical Architecture

### Backend Extensions

#### New Module: `server/erosion_tools/`
```
erosion_tools/
├── __init__.py
├── noaa_slr.py          # NOAA sea level rise API
├── usgs_shoreline.py    # USGS coastal change data
├── species_risk.py      # Risk scoring algorithms
├── predictive_models.py # Population projections
└── restoration_roi.py   # Restoration priority scoring
```

#### New Endpoints (server/main.py)
```python
GET  /erosion/risk_zones              # Erosion risk GeoJSON
GET  /erosion/shoreline_history       # Historical shoreline positions
GET  /erosion/slr_projections         # Sea level rise scenarios

GET  /species/risk_assessment         # Species-level risk scores
GET  /species/population_projections  # Future population forecasts
GET  /species/habitat_vulnerability   # Habitat loss analysis

GET  /colonies/viability              # Colony persistence scores
GET  /colonies/disappeared            # Historical colony losses
GET  /colonies/temporal_analysis      # Multi-year comparisons

GET  /restoration/priority_map        # Restoration heatmap
GET  /restoration/site_recommendations # Optimal sites
```

### Frontend Redesign

#### New Layout (frontend/pages/03_nest_map.py)
```
┌─────────────────────────────────────────────────────────────────┐
│  Header: NestMap - Erosion Risk & Species Conservation Tool    │
├────────────────────┬────────────────────────────────────────────┤
│  Sidebar           │  Main Map Panel                            │
│  ----------------  │  - Multi-layer toggle:                     │
│  Layer Controls:   │    ☑ Colony markers (sized by risk)       │
│  ☑ Erosion zones   │    ☑ Erosion risk zones                   │
│  ☑ SLR scenarios   │    ☑ Sea level rise (1ft/3ft/6ft)        │
│  ☑ Storm tracks    │    ☑ Historical shorelines                │
│  ☑ Disappeared     │    ☑ Storm tracks (2005-2024)            │
│      colonies      │    ☑ Disappeared colonies (ghosts)        │
│                    │  - Interactive tooltips with risk scores   │
│  Time Slider:      │  - Click colony → detailed panel           │
│  ━━●━━━━━━━━━━━    │                                            │
│  2010 ──→ 2070     │                                            │
│                    │                                            │
│  Species Filter:   │                                            │
│  [All Species ▼]   │                                            │
│                    │                                            │
│  Risk Filter:      │                                            │
│  ☑ Critical        │                                            │
│  ☑ Endangered      │                                            │
│  ☐ Vulnerable      │                                            │
│  ☐ Stable          │                                            │
├────────────────────┴────────────────────────────────────────────┤
│  Species Risk Dashboard                                         │
│  ┌────────────┬────────────┬────────────┬────────────┐         │
│  │ CRITICAL   │ ENDANGERED │ VULNERABLE │ STABLE     │         │
│  │ 2 species  │ 5 species  │ 8 species  │ 4 species  │         │
│  └────────────┴────────────┴────────────┴────────────┘         │
├─────────────────────────────────────────────────────────────────┤
│  Temporal Trends & Projections                                  │
│  [Interactive Plotly chart: population by year with forecasts]  │
├─────────────────────────────────────────────────────────────────┤
│  Restoration Priority Heatmap                                   │
│  [Geographic heatmap showing optimal restoration sites]         │
└─────────────────────────────────────────────────────────────────┘
```

### Data Integration Strategy

#### Phase 1: Local Static Data (Immediate)
**Source:** Pre-downloaded datasets stored in `data/erosion/`
- NOAA SLR viewer shapefiles (publicly available)
- USGS shoreline change data (DSAS outputs)
- Louisiana Coastal Master Plan GIS layers
- Storm track data (NOAA IBTrACS)

**Pros:** Fast, no API dependencies
**Cons:** Requires manual updates

#### Phase 2: API Integration (Production)
**APIs to integrate:**
- NOAA Digital Coast Data Access Viewer
- USGS Coastal Change Hazards Portal
- NASA JPL Sea Level Change Portal
- CPRA Coastal Information Management System (CIMS)

**Implementation:** Cached responses (24hr TTL) with fallback to local data

#### Phase 3: Real-time Sensor Data (Future)
- NOAA tide gauge stations (real-time water levels)
- Weather station data (wind, temperature)
- Camera trap networks (breeding activity)

## Species Risk Scoring Algorithm

### Input Variables
1. **Population Trend Score** (40% weight)
   - Linear regression slope of 2010-2021 counts
   - Scaled: -1 (steep decline) to +1 (steep increase)

2. **Habitat Vulnerability Score** (30% weight)
   - % of colonies in high-erosion zones
   - Average colony elevation (< 2m = high risk)
   - Proximity to eroding shoreline (< 500m = high risk)

3. **Range Diversity Score** (20% weight)
   - Number of colonies occupied
   - Geographic spread (single bay vs. Gulf-wide)
   - Habitat type diversity (island vs. marsh vs. key)

4. **Conservation Status** (10% weight)
   - Federal/state listings (Endangered = 1.0, Threatened = 0.5)
   - IUCN Red List category

### Output Risk Categories
- **Critical**: Score > 0.75 (immediate intervention needed)
- **Endangered**: Score 0.50-0.75 (high priority)
- **Vulnerable**: Score 0.25-0.50 (monitor closely)
- **Stable**: Score < 0.25 (routine monitoring)

### Example Calculation: Brown Pelican (BRPE)
```
Population Trend: +2,500 birds/year → +0.6 (stable/increasing)
Habitat Vulnerability: 45% colonies in high-erosion → 0.45
Range Diversity: 12 colonies across 4 bays → 0.2 (good)
Conservation Status: Delisted (recovered) → 0.0

Overall Score: 0.6×0.4 + 0.45×0.3 + 0.2×0.2 + 0.0×0.1 = 0.415
Risk Category: VULNERABLE (due to habitat loss despite population recovery)
```

## Restoration Priority Scoring

### Algorithm
```python
priority_score = (
    species_diversity_score × 0.3 +  # More species = higher value
    total_population_score × 0.25 +   # Larger colonies = higher value
    species_risk_score × 0.25 +       # At-risk species = higher value
    site_viability_score × 0.15 +     # Low erosion = higher success
    connectivity_score × 0.05         # Near other colonies = spillover
)
```

### Output
- GeoJSON heatmap (1km grid cells) with priority scores
- Top 10 recommended restoration sites with justifications
- Cost-benefit analysis (estimated birds gained per $1M invested)

## Implementation Timeline

### Week 1: Backend Foundation
- [ ] Create `server/erosion_tools/` module
- [ ] Download and process NOAA/USGS datasets
- [ ] Implement erosion risk zone calculation
- [ ] Build species risk scoring engine
- [ ] Add backend API endpoints

### Week 2: Frontend Redesign
- [ ] Rewrite `frontend/pages/03_nest_map.py`
- [ ] Multi-layer Folium map with toggles
- [ ] Species risk dashboard component
- [ ] Temporal trend charts with projections
- [ ] Restoration priority heatmap

### Week 3: Integration & Polish
- [ ] Connect frontend to new backend endpoints
- [ ] Add interactive filters and controls
- [ ] Performance optimization (lazy loading layers)
- [ ] Mobile responsiveness
- [ ] Documentation and tooltips

## Success Metrics

### For The Water Institute
- **Actionable Insights**: Clear list of at-risk species with justifications
- **Restoration Guidance**: Prioritized site recommendations
- **Stakeholder Communication**: Visual tool for presenting to trustees/public
- **Long-term Monitoring**: Automated alerts when species cross risk thresholds

### For DevDays Demo
- **Wow Factor**: Live erosion overlay + disappearing colonies
- **Technical Depth**: Predictive models + multi-source data integration
- **Real-world Impact**: Direct link to $1.2B Deepwater Horizon restoration
- **Scalability Story**: Template for other coastal monitoring programs

## Key Messages for Judges

### Derek Dohler (TWI - 50/100)
"Derek, you asked if NestScope can be reliable enough for real-world use. Here's our answer: **decision-support, not just data**. NestMap doesn't just show where colonies are—it predicts which ones will disappear and why. You can use this to justify restoration investments to trustees with quantitative risk scores."

### Jessica Henkel (TWI - 58/100)
"Jessica, we heard your feedback about building out expert features. NestMap now includes a **restoration priority engine** that combines expert dotting data with erosion forecasts to recommend where to invest. Every manually dotted image improves the risk model."

### Conservation Impact
"Louisiana is losing a football field of land every 100 minutes. Bird colonies are disappearing with it. NestMap identifies **which species are most vulnerable** and **where restoration will have the greatest impact**—turning $1.2 billion in Deepwater Horizon funding into measurable conservation outcomes."

## References & Data Sources

### Publicly Available Datasets
1. **NOAA Sea Level Rise Viewer**: https://coast.noaa.gov/slr/
2. **USGS Coastal Change Hazards**: https://www.usgs.gov/programs/cmhrp
3. **Louisiana Coastal Master Plan**: https://coastal.la.gov/our-plan/2023-coastal-master-plan/
4. **NAIP Imagery**: https://naip-usdaonline.hub.arcgis.com/
5. **NOAA Storm Tracks (IBTrACS)**: https://www.ncei.noaa.gov/products/international-best-track-archive
6. **IUCN Red List API**: https://apiv3.iucnredlist.org/

### Scientific Literature
- Coastal Louisiana habitat loss rates (Couvillion et al. 2017)
- Brown Pelican recovery post-DDT (USFWS 2009)
- Climate change impacts on Gulf seabirds (Wilkinson et al. 2018)
- Barrier island migration models (FitzGerald et al. 2008)

---

**Status**: Ready to implement
**Priority**: HIGH - Critical for DevDays competitive edge
**Risk**: MEDIUM - Requires external data integration
**Impact**: VERY HIGH - Directly addresses Water Institute's research goals
