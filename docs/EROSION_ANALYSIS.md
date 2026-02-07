# Erosion Analysis Guide

Using the Bird Colony Data Chatbot for coastal erosion and habitat change research.

---

## Overview

This database is **ideal for coastal erosion analysis** because it contains:
- 11+ years of longitudinal data (2010-2021)
- 67% colony loss documented (288 → 94 active colonies)
- Detailed field notes about habitat changes
- Geographic coordinates for spatial analysis
- Storm and flooding documentation

---

## Key Metrics

### Colony Loss Statistics

```
Total Colonies in 2010: 288
Active Colonies in 2021: 94
Colonies Lost: 194 (67% loss rate)
```

### Major Causes Documented
1. Storm damage and flooding
2. Habitat overwash
3. Vegetation loss
4. Island erosion
5. Hurricane impacts (Isaac, Ida)

---

## Erosion Analysis Queries

### 1. Identify Lost Colonies

**Question:**
```
Which colonies were active in 2010 but disappeared by 2021?
```

**SQL Pattern:**
```sql
SELECT DISTINCT o2010.colony_name, o2010.state, o2010.geo_region
FROM observations o2010
WHERE o2010.year = 2010
AND o2010.colony_name NOT IN (
    SELECT colony_name FROM observations WHERE year = 2021
)
ORDER BY o2010.state, o2010.colony_name;
```

**Analysis:**
- 194 colonies present in 2010 but absent in 2021
- Indicates complete habitat loss or abandonment
- Use with `colony_inventory.ActiveInventory` for verification

### 2. Habitat Degradation Over Time

**Question:**
```
Show colonies with notes mentioning erosion, flooding, or vegetation loss
```

**SQL Pattern:**
```sql
SELECT DISTINCT
    o.colony_name,
    o.year,
    o.habitat,
    o.notes
FROM observations o
WHERE o.combined_text LIKE '%erosion%'
   OR o.combined_text LIKE '%flood%'
   OR o.combined_text LIKE '%overwash%'
   OR o.combined_text LIKE '%vegetation%loss%'
   OR o.combined_text LIKE '%degradation%'
ORDER BY o.colony_name, o.year
LIMIT 50;
```

**Analysis:**
- Direct evidence of habitat change in field notes
- Track progression over multiple years
- Document specific environmental impacts

### 3. Hurricane Impact Assessment

**Question:**
```
Which colonies were affected by Hurricane Isaac?
```

**SQL Pattern:**
```sql
SELECT
    colony_name,
    year,
    notes
FROM observations
WHERE (notes LIKE '%Hurricane Isaac%' OR notes LIKE '%Isaac%')
   AND year BETWEEN 2012 AND 2013
ORDER BY year, colony_name;
```

**Example Results:**
- Cat Bay South Island: "land and vegetation likely reduced compared to prior years (related to Hurricane Isaac?)"
- Multiple colonies: "overwash", "flooding", "vegetation loss"

### 4. Regional Erosion Patterns

**Question:**
```
What percentage of colonies were lost in each state?
```

**SQL Pattern:**
```sql
SELECT
    state,
    COUNT(DISTINCT CASE WHEN year = 2010 THEN colony_name END) as colonies_2010,
    COUNT(DISTINCT CASE WHEN year = 2021 THEN colony_name END) as colonies_2021,
    ROUND(100.0 * (
        COUNT(DISTINCT CASE WHEN year = 2010 THEN colony_name END) -
        COUNT(DISTINCT CASE WHEN year = 2021 THEN colony_name END)
    ) / COUNT(DISTINCT CASE WHEN year = 2010 THEN colony_name END), 1) as percent_lost
FROM observations
WHERE state != '' AND state IS NOT NULL
GROUP BY state
ORDER BY percent_lost DESC;
```

### 5. Habitat Type Vulnerability

**Question:**
```
Which habitat types were most affected by erosion?
```

**SQL Pattern:**
```sql
SELECT
    ci.PrimaryHabitat,
    COUNT(*) as total_colonies,
    SUM(CASE WHEN ci.ActiveInventory = 'No' THEN 1 ELSE 0 END) as lost_colonies,
    ROUND(100.0 * SUM(CASE WHEN ci.ActiveInventory = 'No' THEN 1 ELSE 0 END) / COUNT(*), 1) as loss_rate
FROM colony_inventory ci
WHERE ci.PrimaryHabitat IS NOT NULL AND ci.PrimaryHabitat != ''
GROUP BY ci.PrimaryHabitat
ORDER BY loss_rate DESC;
```

---

## Case Study: Cat Bay South Island

### Documented Habitat Change (2010-2012)

**2010:** "marsh/grass island w. taller grass; some bare areas"
**2011:** "Grasses, bare ground, shrubs"
**2012:** "Bare ground, mud flat, grasses, shrubs" ← **MORE bare ground**

**Field Notes:**
- "Vastly more bare ground (less shrubs) and mud flat compared to 2011"
- "land and vegetation likely reduced compared to prior years (related to Hurricane Isaac?)"

### Query:
```
How did habitats change at Cat Bay South Island from 2010 to 2021?
```

**Analysis Steps:**
1. Query observations for specific colony
2. Group by year
3. Compare habitat descriptions
4. Review aggregated notes for patterns
5. Quantify changes (vegetation → bare ground)

---

## Spatial Analysis

### Ecoregion-Based Assessment

**Question:**
```
Which ecoregions experienced the most colony losses?
```

**SQL Pattern:**
```sql
SELECT
    ci.TerrestEcoRegion,
    COUNT(*) as total,
    SUM(CASE WHEN ci.ActiveInventory = 'No' THEN 1 ELSE 0 END) as lost,
    ROUND(100.0 * SUM(CASE WHEN ci.ActiveInventory = 'No' THEN 1 ELSE 0 END) / COUNT(*), 1) as percent
FROM colony_inventory ci
WHERE ci.TerrestEcoRegion IS NOT NULL
GROUP BY ci.TerrestEcoRegion
HAVING COUNT(*) >= 5
ORDER BY percent DESC;
```

### Geographic Clustering

Use coordinates to map:
- Clusters of lost colonies
- Shoreline erosion patterns
- Protected vs unprotected areas

**Export for GIS:**
```sql
SELECT
    ci.ColonyName,
    ci.Latitude,
    ci.Longitude,
    ci.ActiveInventory,
    ci.GeoRegion
FROM colony_inventory ci
WHERE ci.Latitude IS NOT NULL;
```

---

## Temporal Analysis

### Year-over-Year Changes

**Question:**
```
How many colonies were active each year?
```

**SQL Pattern:**
```sql
SELECT
    year,
    COUNT(DISTINCT colony_name) as active_colonies
FROM observations
GROUP BY year
ORDER BY year;
```

**Results:**
```
2010: 288 colonies
2011: 106 colonies (63% drop!)
2012: 105 colonies
2013: 130 colonies
2015: 148 colonies
2018: 117 colonies
2021: 265 colonies
```

**Analysis:**
- Massive drop 2010→2011 (likely sampling methodology change)
- Gradual recovery 2012-2015
- Continued challenges 2015-2021
- Compare with storm timelines

### Multi-Year Presence

**Question:**
```
Which colonies appeared consistently across multiple years?
```

**SQL Pattern:**
```sql
SELECT
    colony_name,
    COUNT(DISTINCT year) as years_present,
    MIN(year) as first_seen,
    MAX(year) as last_seen
FROM observations
GROUP BY colony_name
HAVING COUNT(DISTINCT year) >= 5
ORDER BY years_present DESC;
```

**Resilient Colonies:**
- Present 5+ years = likely more stable habitat
- May indicate protective features (elevation, vegetation, etc.)

---

## Research Applications

### 1. Quantify Coastal Land Loss

**Objective**: Measure barrier island erosion rates

**Method**:
1. Count colonies by year
2. Calculate loss rates
3. Correlate with storm events
4. Map geographic patterns

**Output**: Loss rate estimates, regional comparisons

### 2. Habitat Restoration Prioritization

**Objective**: Identify colonies for restoration efforts

**Method**:
1. Find colonies with partial degradation
2. Still have nesting birds
3. Show habitat loss in notes
4. Have historical importance

**Query Example**:
```
Show colonies with decreasing observations but still active
```

### 3. Storm Impact Assessment

**Objective**: Document hurricane effects on nesting habitat

**Method**:
1. Search notes for storm mentions
2. Compare pre/post storm observations
3. Track recovery timelines
4. Identify vulnerable locations

**Case Studies**:
- Hurricane Isaac (2012)
- Hurricane Ida (2021)
- Other tropical systems

### 4. Climate Change Indicators

**Objective**: Use bird colony data as proxy for sea level rise

**Indicators**:
- Overwash frequency increasing
- Vegetation loss patterns
- Colony abandonment rates
- Habitat type shifts (marsh → mud flat)

---

## Data Export for Advanced Analysis

### For Statistical Analysis (R/Python)

```python
import sqlite3
import pandas as pd

conn = sqlite3.connect('bird_data.db')

# Export colony status over time
query = """
SELECT
    o.colony_name,
    o.year,
    o.latitude,
    o.longitude,
    o.habitat,
    ci.ActiveInventory,
    ci.PrimaryHabitat,
    ci.TerrestEcoRegion
FROM observations o
LEFT JOIN colony_inventory ci ON o.colony_name = ci.ColonyName
WHERE o.year IN (2010, 2015, 2021)
ORDER BY o.colony_name, o.year
"""

df = pd.read_sql_query(query, conn)
df.to_csv('erosion_analysis.csv', index=False)
```

### For GIS Mapping (QGIS, ArcGIS)

```sql
-- Export colonies with status
.mode csv
.output colonies_spatial.csv
SELECT
    ci.ColonyName,
    ci.Latitude,
    ci.Longitude,
    ci.ActiveInventory,
    ci.State,
    ci.GeoRegion,
    ci.PrimaryHabitat,
    cp.total_observations,
    cp.years_observed
FROM colony_inventory ci
LEFT JOIN colony_profiles cp ON ci.ColonyName = cp.colony_name
WHERE ci.Latitude IS NOT NULL;
.output stdout
```

---

## Limitations & Considerations

### Data Gaps
- **Sampling Variation**: Not all colonies surveyed every year
- **Methodology Changes**: 2010→2011 shows large drop (likely survey design)
- **Missing Coordinates**: Some colonies lack precise locations

### Interpretation Caveats
- Colony "loss" may mean:
  - Physical erosion/disappearance
  - Abandonment by birds (still exists)
  - Not surveyed (false negative)
- Use `ActiveInventory` field for official status

### Recommended Validation
1. Cross-reference with satellite imagery
2. Verify with other erosion datasets
3. Consider multiple years of absence before confirming loss
4. Review field notes for context

---

## Example Research Questions

### Beginner Level
1. How many colonies were lost from 2010 to 2021?
2. Which states had the most colony losses?
3. What colonies had oil AND erosion documented?

### Intermediate Level
4. Which habitat types are most vulnerable to erosion?
5. How did Hurricane Isaac affect colony populations?
6. What's the average colony lifespan in the dataset?

### Advanced Level
7. Model erosion risk factors (habitat type, location, storm exposure)
8. Predict future colony losses based on historical patterns
9. Correlate erosion rates with sea level rise data
10. Assess effectiveness of restoration efforts (if applicable)

---

## Related Documentation

- **[DATA_SCHEMA.md](DATA_SCHEMA.md)** - Database structure
- **[EXAMPLES.md](EXAMPLES.md)** - More query examples
- **[USAGE.md](USAGE.md)** - How to ask questions

---

**This database provides unique longitudinal evidence of Gulf Coast erosion impacts on wildlife habitat. Use it to inform conservation policy and restoration priorities.**
