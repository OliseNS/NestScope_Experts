# Avian Data Monitoring Portal - Data Management

## Data Processing Challenges

### Geolocation Problem

**Critical Requirement:** Every aerial survey image must be geolocated (defined position in time and space)

**2021+ Surveys (Modern):**
- Hardware acquisitions by Colibri ensured GPS coordinates in EXIF metadata
- Photos natively include location data

**2010-2018 Surveys (Historical):**
- Required **intensive data engineering** to match photos to locations
- Process: Match photo timestamp (EXIF) → GPS trackline from aircraft
- Called "geolocation" process
- Significant additional processing to unify survey periods into common format

### Data Unification

After geolocation, extensive processing required:
1. **Field schema mapping** to unify all survey periods
2. **Linking high-resolution images** with dotting screenshots and thumbnails
3. **Database merging** across multiple survey years
4. Additional fields added for image associations

**Data Model:**
- Merged database with common structure
- Links: high-res image ↔ dotting screenshot ↔ thumbnail ↔ database entry

## Data Analysis

**Important Note:** Data analysis (nest dotting) completed by **Colibri** prior to delivery to The Water Institute.

**Manual Dotting Workflow:**
- Highly labor-intensive
- Requires trained ornithologists
- Time-consuming per-image analysis
- Bottleneck in the entire pipeline

## Data Publication

**Integration Points:**
- **NOAA DIVER**: Principal project hosting site for Deepwater Horizon
- **CPRA Coastal Information Management System (CIMS)**
- Portal meets/exceeds NOAA DIVER requirements

**Available Downloads:**
- Summary Report (PDF)
- Data Management Plan (PDF)
- Current Avian Database (MS Access)
- Summary File (MS Excel)
- Database README

---

## Critical Pain Points Identified

### 1. **Manual Dotting Bottleneck**
Only ~3-5% of collected images are manually dotted. This is the **primary constraint** limiting data utility.

### 2. **Geolocation Complexity**
Historical data required intensive engineering. Modern surveys solved this with GPS-enabled cameras, but processing pipeline is still complex.

### 3. **Data Format Fragmentation**
Multiple survey periods required extensive unification work to create a consistent database.

### 4. **Processing Delays**
Images collected in field → sent to Colibri → manual dotting → sent to Water Institute → database integration → published to portal. This can take **months to years**.

---

**NestScope Opportunity:** Automated AI-based dotting could process the **96-97% of undotted images**, unlocking massive latent value in the existing dataset.
