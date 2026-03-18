# Avian Data Monitoring Portal - Survey and Dotting Protocols

## Survey Period: 2010-2021

**Note:** Protocols below are for 2010-2021. Subsequent efforts (2022-current) have been upgraded (see Future Directions).

## Target Species

### Colonial-Breeding Shrub and Ground-Nesting Birds

**Target Species:**
- Brown Pelican (Pelecanus occidentalis)
- Laughing Gull (Leucophaeus atricilla)
- Royal Tern (Thalasseus maximus)
- Sandwich Tern (Thalasseus sandvicensis)
- Caspian Tern (Hydroprogne caspia)
- Forster's Tern (Sterna forsteri)
- Gull-billed Tern (Gelochelidon nilotica)
- Black Skimmer (Rynchops niger)
- Least Tern (Sternula antillarum) - mostly incidental, but targeted in 2021 for MS/FL beaches

**Target Wading Birds:**
- White Ibis (Eudocimus albus)
- Tricolored Heron (Egretta tricolor)
- Great Egret (Ardea alba)
- Snowy Egret (Egretta thula)
- Reddish Egret (Egretta rufescens)
- Roseate Spoonbill (Platalea ajaja)

**Solitary Breeding Shorebirds:**
- American Oystercatcher (Haematopus palliatus) - regularly observed
- Wilson's Plover (Charadrius wilsonia) - typically NOT detectable
- Ruddy Turnstone (Arenaria interpres) - migrant species, conspicuous plumage, consistently identified

## Colony Inventory (GIS-Based)

**2010:** Colibri compiled initial inventory of known/former bird colony locations
- Data from state and federal agencies
- Built into GIS system
- Continuously updated since 2010

**Geographic Organization:**
- **34 Geographic Regions** created (Texas → Florida Keys)
- Based on Level IV Terrestrial Ecoregion
- Based on Level 12 HUC Watershed layers
- Database field: `GeoRegion`

## Aerial Photography Methodology

### Aircraft Configuration

**Aircraft:** Fixed-wing, twin engine, high-wing Partenavia (PN68)
- Belly port for vertical/nadir photography
- Two photographers working simultaneously

**Crew:**
- Pilot
- Navigator/data recorder (co-pilot seat)
- Two photographers (rear)

**Survey Flight Parameters:**
- **Altitude:** 700-1000 feet (700 ft for small birds like terns, 1000 ft for pelicans)
- **Ground speed:** <90 knots (103 mph)
- **Minimum altitude:** 700 ft (to avoid disturbing breeding birds)
- **Optimal lighting:** 3 hours after sunrise to 3 hours before sunset (solar altitude ≥35°)

### Photography Approach

**Photographer Roles:**
- **Context photographer:** Wide-area view of colonies, also zooms for mid-focal shots
- **Detail photographer:** Close-up detailed shots

**Flight Strategy:**
- Multiple approaches from different directions/altitudes often necessary
- Determined by: colony extent, species present, wind, vegetation, sun angle

**Camera Equipment (as of 2021):**
- Full frame digital single-lens reflex (Canon EOS-1D X Mark III®)
- Zoom and telephoto lenses (16–300mm focal length)
- Aircraft location and time recorded automatically (≤5 second intervals)

## Nest and Bird Enumeration (Dotting)

### Image Selection

**Peak Breeding Period Selection:**
- May vs June photographs evaluated per species
- Brown Pelican, Great Egret: May photos often used
- Black Skimmer: June photos often used
- Sometimes May + June counts summed for complete totals

### Analysis Software

**Tool:** Image-Pro (Media Cybernetics®)
- Manual "dotting" of nests and birds
- Automatic tallying of counts per category
- Symbol-color combinations for species and nest categories

### Brown Pelican Nest Categories (Detailed)

1. **Well Built Nest** (attending adult in incubation posture)
2. **Poorly Built Nest** (pre egg-laying, breeding pair)
3. **Nest with Chicks, with attending adults**
4. **Nest with Chicks, without attending adults**
5. **Brood** (dependent chicks away from nest, not attended)
6. **Abandoned Nest** (with eggs, unattended)
7. **Empty Nest** (unattended, no eggs/chicks)
8. **Territory** (breeding habitat, territorial spacing, not breeding pair)

**Excluded from colony totals:** Empty Nests and Territories (not considered active breeding sites)

### Other Species Categories

**Nest Categories:**
- Due to small size and scrape-nesting habits, fewer categories used
- **"Site":** Bird in incubation posture (lack of visible nest structure)
- As of 2021: Three "chicks present" categories standardized for all species

**Other Birds Counted:**
- Mates at nests (second adult)
- Birds along shoreline
- Birds in colony areas not associated with breeding territory
- Exceptions: Roosting birds in non-breeding habitat (inconsistently dotted due to time constraints)

### Dotting Workflow

1. Inspect all colony images for clarity, location, colony coverage
2. Select best images for nest counts covering all breeding areas
3. Analyze using Image-Pro software
4. Manually dot nests and birds
5. Software tallies counts
6. Draw boundary lines on overlapping images to avoid double-counting
7. Continue until colony fully counted

---

## Key Insights for AI/ML

### Complexity Categories for Automated Detection

**Easy (High Detection Confidence):**
- Brown Pelicans (large, distinct nests)
- Royal Terns (clustered on open ground)
- American Oystercatchers (large, distinct)

**Medium Difficulty:**
- Laughing Gulls (smaller, more vegetation)
- Sandwich Terns (similar to Royal Terns)
- Wading birds in open areas

**Challenging:**
- Least Terns (very small)
- Wilson's Plovers (too small)
- Birds in dense vegetation
- Partially concealed nests

### Classification Tasks for AI

**Detection:** Identify bird presence and location (bounding box)
**Species Classification:** Identify which species (Brown Pelican, Royal Tern, etc.)
**Behavior Classification:** Identify breeding stage (incubating, with chicks, roosting)
**Counting:** Total birds, total nests, by category

### Time Investment

**Manual dotting is extremely labor-intensive:**
- Requires trained ornithologist (expensive expertise)
- One image can take 15-60 minutes depending on colony density
- 350,000 images collected, but only 3-5% dotted
- **This is the critical bottleneck NestScope addresses**

---

**NestScope Advantage:** Our YOLOv8 model can process an image in seconds vs. 15-60 minutes for manual dotting. This represents a **100-1000x speedup**.
