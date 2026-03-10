# FEMA Flood Zone Integration

## Overview

Added comprehensive FEMA (Federal Emergency Management Agency) flood zone data to the Flood Intelligence page with interactive map visualization and educational context.

## What Changed

### Backend Updates (`server/main.py`)

**Modified:** `/api/risk/map_zones` endpoint to include FEMA data
- Added `fema_zone` field (zone code: A, AE, V, VE, X500, X, etc.)
- Added `fema_description` field (human-readable explanation)
- Added `fema_category` field (HIGH, MODERATE, LOW, MINIMAL)

**FEMA Category Mapping:**
```python
- HIGH: Zones A, AE, V, VE (1% annual flood chance - 100-year floodplain)
- MODERATE: Zones AO, AH, A99 (special considerations)
- LOW: Zone X500 (0.2% annual flood chance - 500-year floodplain)
- MINIMAL: Zone X (outside mapped flood hazard areas)
```

### Frontend Updates (`frontend/pages/06_coastal_risk.py`)

**New Section: FEMA Flood Hazard Classification**

1. **Summary Metrics (4 cards)**
   - Selected colony's FEMA zone classification
   - Number of colonies in 100-year floodplain
   - Moderate flood risk zone count
   - Minimal risk zone count

2. **Context Panel for Selected Colony**
   - FEMA zone code and description
   - Flood insurance requirements
   - Special Flood Hazard Area (SFHA) status

3. **Interactive FEMA Zone Map**
   - Color-coded by flood risk category:
     - 🔴 Red = High Risk (Zone A/AE/V/VE)
     - 🟠 Orange = Moderate (Zone AO/AH)
     - 🟡 Yellow = Low Risk (Zone X500)
     - 🟢 Green = Minimal (Zone X)
   - Hover tooltips show zone details
   - Uses Plotly for smooth interaction

4. **FEMA Zone Reference Guide**
   - Two-column layout explaining each zone type
   - Insurance requirements
   - Annual flood probability percentages

### Configuration Changes (`.env`)

**Enabled FEMA Integration:**
```bash
ENABLE_FEMA=true
```

This allows the backend to query FEMA's National Flood Hazard Layer (NFHL) REST API for official flood zone classifications.

## Why FEMA Data Matters

### For Coastal Restoration Planning

FEMA flood zones are the **official federal standard** for flood risk assessment. They:

1. **Determine Insurance Requirements**
   - Zones A, AE, V, VE: Mandatory flood insurance for federally-backed mortgages
   - Other zones: Insurance recommended but not required

2. **Inform Construction Standards**
   - High-risk zones have strict building elevation requirements
   - Base Flood Elevation (BFE) data guides foundation design

3. **Guide Emergency Planning**
   - FEMA zones define evacuation priorities
   - Critical for disaster response coordination

4. **Support Grant Applications**
   - Federal restoration funding considers FEMA designations
   - Higher priority for projects in Special Flood Hazard Areas (SFHA)

### For Bird Colony Risk Assessment

Combining FEMA zones with other data sources gives a complete picture:

- **FEMA zones** = official flood probability (based on historical data + hydrology)
- **NOAA water levels** = real-time conditions
- **Erosion rates** = long-term land loss
- **Hurricane tracks** = storm frequency
- **Bird populations** = ecological impact

## Technical Implementation

### Data Flow

```
1. Backend fetches colony coordinates from SQLite
2. RiskIntelligenceService queries FEMA NFHL API for each colony
3. FEMA responses cached (LRU cache prevents redundant API calls)
4. Zone classifications mapped to risk categories
5. Data exposed via /api/risk/map_zones endpoint
6. Frontend fetches and visualizes on Flood Intelligence page
```

### Performance Optimizations

- **LRU Caching:** FEMA API calls cached to prevent rate limiting
- **Graceful Fallback:** If FEMA API is unavailable, uses geographic proxy (coastal vs inland)
- **Async Loading:** Map renders while FEMA data loads in background
- **Timeout Protection:** 1.5-second timeout per API call to prevent blocking

### API Integration

**FEMA NFHL REST API:**
- Endpoint: `https://hazards.fema.gov/gis/nfhl/rest/services/public/NFHL/MapServer`
- Layer 28: Special Flood Hazard Areas (SFHA)
- Spatial Reference: EPSG:3857 (Web Mercator)
- Returns: Flood zone code, subtype, Base Flood Elevation (if available)

## User Experience

### Before (Without FEMA Data)
- Risk scores based on multiple factors but no official federal classification
- No clear indication of flood insurance requirements
- Missing authoritative flood hazard designation

### After (With FEMA Data)
- ✅ Official FEMA zone displayed for each colony
- ✅ Clear visual map showing flood zone distribution
- ✅ Educational context explaining zone meanings
- ✅ Insurance requirement guidance
- ✅ Authoritative federal data backing risk assessments

## Educational Design (Following FloodIntelligence.txt Principles)

### Clear Visual Hierarchy
- Color-coded metrics with status indicators
- Progressive disclosure: metrics → context → detailed map
- Consistent design language with existing page sections

### Self-Explanatory Interface
- Tooltips explain technical terms
- Reference guide provides zone definitions
- No jargon without explanation

### Actionable Information
- Insurance requirements clearly stated
- Risk categories directly linked to colony selection
- Map click-to-select workflow preserved

### Professional Presentation
- Matches Water Institute's research-grade standards
- Authoritative data sources cited
- Technical accuracy maintained throughout

## Testing Checklist

- [ ] Backend server starts successfully with FEMA enabled
- [ ] `/api/risk/map_zones` returns FEMA data fields
- [ ] Frontend displays FEMA metrics without errors
- [ ] Map renders with color-coded zones
- [ ] Colony selection updates FEMA context panel
- [ ] Hover tooltips show correct zone information
- [ ] Page loads within 2-3 seconds (with caching)
- [ ] Graceful fallback if FEMA API is slow/unavailable

## Future Enhancements

1. **Base Flood Elevation (BFE) Data**
   - Show BFE values where available
   - Compare colony elevation to BFE
   - Calculate flood depth predictions

2. **Historical Flood Events**
   - Overlay past flood extents on map
   - Show which colonies were inundated
   - Link to FEMA Disaster Declarations

3. **Flood Insurance Rate Map (FIRM) Integration**
   - Display official FIRM panels
   - Link to community FIRM effective dates
   - Show upcoming map revisions

4. **Multi-Scenario Projections**
   - Sea level rise impacts on FEMA zones
   - Future flood zone predictions (2050, 2100)
   - Climate change adaptation scenarios

## References

- FEMA NFHL API Documentation: https://hazards.fema.gov/gis/nfhl/rest/services/
- Flood Zone Definitions: https://www.fema.gov/flood-zones
- National Flood Insurance Program: https://www.fema.gov/flood-insurance
- Base Flood Elevation: https://www.fema.gov/glossary/base-flood-elevation-bfe
