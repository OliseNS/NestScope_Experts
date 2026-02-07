# Database Schema

Complete reference for the Bird Colony Data database structure.

---

## Overview

The database contains **4 tables** with a total of **26,234 rows**:

| Table | Rows | Purpose |
|-------|------|---------|
| `observations` | 13,075 | Individual field observations |
| `colony_profiles` | 492 | Aggregated colony-level data |
| `colony_inventory` | 592 | Master colony list with metadata |
| `species` | 73 | Species code lookup |

---

## Tables

### 1. observations

**Purpose**: Individual field observation records with detailed notes

**Row Count**: 13,075

**Columns** (20 fields):

| Column | Type | Description |
|--------|------|-------------|
| `source_file` | TEXT | Source CSV file name |
| `record_id` | TEXT | Unique record identifier |
| `year` | INTEGER | Year of observation (2010-2021) |
| `date` | TEXT | Observation date (if available) |
| `colony_name` | TEXT | Name of bird colony |
| `latitude` | REAL | Latitude coordinate |
| `longitude` | REAL | Longitude coordinate |
| `dotter` | TEXT | Observer initials |
| `habitat` | TEXT | Habitat description |
| `oil_present` | TEXT | Oil presence ('Y', 'N', or NULL) |
| `notes` | TEXT | Detailed field notes |
| `additional_notes` | TEXT | Additional observations |
| `species_code` | TEXT | 4-letter species code (e.g., LAGU) |
| `state` | TEXT | State code (TX, LA, MS, AL, FL) |
| `geo_region` | TEXT | Geographic region name |
| `combined_text` | TEXT | Full text (habitat + notes) |
| `nests` | REAL | Number of nests counted |
| `birds` | REAL | Number of birds counted |
| `text_length` | INTEGER | Length of combined text |
| `has_coordinates` | INTEGER | 1 if lat/long available, 0 otherwise |

**Indexes**:
- `idx_year` ON `year`
- `idx_colony` ON `colony_name`
- `idx_species` ON `species_code`
- `idx_state` ON `state`
- `idx_oil` ON `oil_present`

**Example Row**:
```sql
SELECT * FROM observations LIMIT 1;
```
```
source_file: colony_notes_2010
record_id: CN2010_0
year: 2010
colony_name: Biloxi South 1
latitude: 29.6873
longitude: -89.4646
species_code: NULL
oil_present: N
notes: BLSK colony in early stages; roosting FOTE; birds detected/counted...
```

---

### 2. colony_profiles

**Purpose**: Aggregated data summarizing each colony across all years

**Row Count**: 492

**Columns** (11 fields):

| Column | Type | Description |
|--------|------|-------------|
| `colony_name` | TEXT | Colony name |
| `total_observations` | INTEGER | Total observation count |
| `years_observed` | TEXT | JSON array of years observed |
| `states` | TEXT | JSON array of states |
| `geo_regions` | TEXT | JSON array of geographic regions |
| `habitats` | TEXT | JSON array of habitat types |
| `species_observed` | TEXT | JSON array of species codes |
| `oil_observations` | TEXT | JSON dict of oil presence counts |
| `aggregated_notes` | TEXT | All notes combined with \|\| separator |
| `note_count` | INTEGER | Number of notes |
| `latitude` | REAL | Colony latitude |
| `longitude` | REAL | Colony longitude |

**Example Row**:
```sql
SELECT colony_name, total_observations, years_observed
FROM colony_profiles LIMIT 1;
```
```
colony_name: Long Bay Island
total_observations: 106
years_observed: [2010, 2011, 2012, 2013, 2015, 2018, 2021]
```

---

### 3. colony_inventory

**Purpose**: Master list of all known colonies with habitat classifications

**Row Count**: 592

**Columns** (16 fields):

| Column | Type | Description |
|--------|------|-------------|
| `ColonyID` | TEXT | Unique colony identifier |
| `ActiveInventory` | TEXT | 'Yes' if active, 'No' if inactive/lost |
| `ColonyGroupBuffer` | TEXT | Colony group name |
| `ColonyName` | TEXT | Colony name |
| `State` | TEXT | State code |
| `Longitude` | REAL | Longitude |
| `Latitude` | REAL | Latitude |
| `PrimaryHabitat` | TEXT | Primary habitat type |
| `LandForm` | TEXT | Land form classification |
| `GeoRegion` | TEXT | Geographic region |
| `ExtrapArea` | TEXT | Extrapolation area |
| `TerrestEcoRegion` | TEXT | Terrestrial ecoregion |
| `MarineEcoRegion` | TEXT | Marine ecoregion |
| `FormerNames` | TEXT | Previous colony names |
| `OrigDotterID` | TEXT | Original observer ID |
| `NOTES August 2022` | TEXT | Admin notes |

**Key Field**: `ActiveInventory`
- Use this to identify colonies lost to erosion
- 'No' indicates colony no longer active

**Example Row**:
```sql
SELECT ColonyName, ActiveInventory, PrimaryHabitat, GeoRegion
FROM colony_inventory WHERE ActiveInventory = 'No' LIMIT 1;
```
```
ColonyName: 3 Rooker Key
ActiveInventory: No
PrimaryHabitat: NULL
GeoRegion: Tampa Bay
```

---

### 4. species

**Purpose**: Species code to full name lookup

**Row Count**: 73

**Columns** (2 fields):

| Column | Type | Description |
|--------|------|-------------|
| `species_code` | TEXT | 4-letter species code |
| `species_name` | TEXT | Full species common name |

**Example Rows**:
```sql
SELECT * FROM species WHERE species_code IN ('LAGU', 'BRPE', 'TRHE')
ORDER BY species_code;
```
```
BRPE | Brown Pelican
LAGU | Laughing Gull
TRHE | Tricolored Heron
```

**Full Species List**: See Appendix below

---

## Relationships

### Primary Keys
- `observations`: No formal primary key (use `record_id`)
- `colony_profiles`: `colony_name`
- `colony_inventory`: `ColonyID`
- `species`: `species_code`

### Foreign Key Relationships

```
observations.colony_name → colony_profiles.colony_name
observations.colony_name → colony_inventory.ColonyName
observations.species_code → species.species_code
```

**Note**: Foreign keys not enforced in SQLite, but logical relationships exist.

### Example JOIN Query

```sql
-- Get observations with species names
SELECT
    o.year,
    o.colony_name,
    s.species_name,
    o.nests,
    o.birds
FROM observations o
LEFT JOIN species s ON o.species_code = s.species_code
WHERE o.year = 2010
LIMIT 10;
```

```sql
-- Get colony status with observations
SELECT
    ci.ColonyName,
    ci.ActiveInventory,
    ci.PrimaryHabitat,
    cp.total_observations,
    cp.years_observed
FROM colony_inventory ci
LEFT JOIN colony_profiles cp ON ci.ColonyName = cp.colony_name
WHERE ci.ActiveInventory = 'No'
LIMIT 10;
```

---

## Data Types & Formats

### Text Fields
- **Case-sensitive**: Colony names, species codes
- **NULL values**: Represented as empty strings or NULL
- **Encoding**: UTF-8

### Numeric Fields
- **Integers**: `year`, `total_observations`, `note_count`
- **Floats**: `latitude`, `longitude`, `nests`, `birds`
- **Range checks**: year (2010-2021), lat/long (Gulf Coast bounds)

### JSON Fields
- **Format**: Valid JSON arrays/objects stored as TEXT
- **Parse in Python**: `json.loads(row['years_observed'])`

### Coordinate System
- **Format**: Decimal degrees (WGS84)
- **Latitude range**: ~25-31°N (Gulf Coast)
- **Longitude range**: ~-98 to -80°W

---

## Appendix: Complete Species List

| Code | Species Name |
|------|--------------|
| ALL | All breeding species occurring at this colony |
| AMAV | American Avocet |
| AMCO | American Coot |
| AMOY | American Oystercatcher |
| ANHI | Anhinga |
| AWPE | American White Pelican |
| BCNH | Black-crowned Night Heron |
| BLSK | Black Skimmer |
| BLTE | Black Tern |
| BNST | Black-necked Stilt |
| BRNO | Brown Noddy |
| BRPE | Brown Pelican |
| CAEG | Cattle Egret |
| CANG | Canada Goose |
| CARO | Caspian/Royal Tern |
| CATE | Caspian Tern |
| COGA | Common Gallinule |
| COTE | Common Tern |
| CRCA | Crested Caracara |
| DAIB | Glossy/White-faced Ibis |
| DCCO | Double-crested Cormorant |
| FOCO | Forster's/Common Tern |
| FOTE | Forster's Tern |
| FUWD | Fulvous Whistling-Duck |
| GBHE | Great Blue Heron |
| GBTE | Gull-billed Tern |
| GREG | Great Egret |
| HERG | Herring Gull |
| LAGU | Laughing Gull |
| LBHE | Little Blue Heron |
| LETE | Least Tern |
| LIBH | Little Blue Heron |
| MAFR | Magnificent Frigatebird |
| MODU | Mottled Duck |
| NECO | Neotropic Cormorant |
| OSPR | Osprey |
| REEG | Reddish Egret |
| ROSA | Royal or Sandwich Tern |
| ROSP | Roseate Spoonbill |
| ROST | Roseate Tern |
| ROYT | Royal Tern |
| RUTU | Ruddy Turnstone |
| SATE | Sandwich Tern |
| SDHE | Small Dark Heron/Egret |
| SNEG | Snowy Egret |
| SONO | Sooty Tern or Brown Noddy |
| SOTE | Sooty Tern |
| TRHE | Tricolored Heron |
| TRSN | Tricolored Heron or Snowy Egret |
| ULGU | Unknown Large Gull |
| ULTE | Unknown Large Tern |
| UNCO | Neotropic or Double-crested Cormorant |
| UNCR | Crow sp. |
| UNDU | Unknown Duck |
| UNEG | Unknown Egret |
| UNGT | Unknown Gull or Tern |
| UNGU | Unknown Gull |
| UNHG | Unknown Heron or Egret |
| UNIB | Unidentified Ibis |
| UNNH | Unidentified Night Heron |
| UNRA | Unknown Rail |
| UNSB | Unknown Shorebird |
| UNTE | Unknown Tern sp. |
| UNWA | Unknown Waterbird |
| USTE | Forster's and/or Gull-billed Tern |
| WADE | Wader sp. |
| WFIB | White-faced Ibis |
| WHEG | Great/Snowy Egret |
| WHIB | White Ibis |
| WOST | Wood Stork |
| YCNH | Yellow-crowned Night Heron |

---

## Query Patterns

### Count Observations by Year
```sql
SELECT year, COUNT(*) as total
FROM observations
GROUP BY year
ORDER BY year;
```

### Find Most Observed Colonies
```sql
SELECT colony_name, COUNT(*) as obs_count
FROM observations
WHERE colony_name != ''
GROUP BY colony_name
ORDER BY obs_count DESC
LIMIT 10;
```

### Get Species Diversity per Colony
```sql
SELECT
    colony_name,
    COUNT(DISTINCT species_code) as species_count
FROM observations
WHERE species_code != '' AND species_code IS NOT NULL
GROUP BY colony_name
ORDER BY species_count DESC
LIMIT 10;
```

### Find Colonies Lost to Erosion
```sql
SELECT
    ci.ColonyName,
    ci.State,
    ci.GeoRegion,
    cp.total_observations,
    cp.years_observed
FROM colony_inventory ci
LEFT JOIN colony_profiles cp ON ci.ColonyName = cp.colony_name
WHERE ci.ActiveInventory = 'No'
ORDER BY ci.State, ci.ColonyName;
```

---

**For more query examples, see [EXAMPLES.md](EXAMPLES.md)**
