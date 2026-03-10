# Avian Data Monitoring Portal - Future Directions

## LA-TIG Funding

The Louisiana Trustee Implementation Group (LA-TIG) is supporting advancement of this project over the **next 5 years**.

## Survey and Dotting Methods Upgrades (2024, 2026, 2028)

The Water Institute and Colibri have **revised** avian surveying data collection methods. This evolution aims to deliver imagery and species observations in a format for **direct integration into web-based GIS platforms**.

### Overview of Modifications

#### 1. High Altitude Overview Imagery

**New Approach:**
- Fixed camera mount ensuring **on-nadir (directly below)** imagery
- Parallel transects with **Ground Sampling Distance (GSD) of 3.5 cm**
- No changes to low altitude detail imagery collection

**Purpose:**
- Create high-resolution mosaics of colony locations
- Georeferenced to **NAIP (National Agricultural Imagery Program) orthoimagery**
- Serve as reference layers to **automate georeferencing** of low altitude detail imagery

#### 2. Desktop GIS-Based Dotting

**Major Shift:**
- Dotting conducted in **desktop GIS** (not standalone imaging program)
- Georeferenced detail imagery
- Output: **GIS dotting features** (not just pixel coordinates)
- Attribute schema mirrors original collection methods (species, observation categories)

#### 3. Web GIS Application Frontend

**User Interface:**
- Georeferenced imagery and dotting points ingested into **web GIS application**
- Interactive map interface
- Custom reports and data extracts
- Spatial and attribute queries

### Example: Queen Bess Island 2023

A pilot implementation is available for Queen Bess Island (Louisiana, 2023) demonstrating these new outputs.

## Historical Data Updates (2010-2021)

### Upgrading Legacy Data

**Goal:** Convert previously collected data (2010-2021) to geospatially enabled format

**Target Accuracy:**
- Dotting geolocation accuracy: **<1 meter**
- Enables direct spatial analysis (habitat types, weather, geomorphology, storm events)

**Benefits:**
- Increased data value and utility
- Dynamic data summaries for selected geographic areas and time periods
- Seamless linkage between web interface and source high-resolution images

## Web Interface Updates

### Enhanced User Experience

**Seamless Linkage:**
- Primary data (high-resolution photographs)
- ↔ Web-accessible geolocated data (nests)
- ↔ Associated metadata (species, etc.)

**Capabilities:**
1. **SMART Objectives Support:** Develop and report on Trustees' objectives
2. **Project Design Insights:** Inform restoration project design and implementation
3. **Enhanced Data Access:** Bird count data by species and year for any geographic extent
4. **Targeted End Users:**
   - Restoration practitioners
   - Managers
   - Planners
   - Researchers
   - **Emphasis on general public**
5. **Self-Service Analytics:** Create dynamic data summaries "on the fly" for selected areas/time periods

### Integration and Compliance

**Direct Linkage:**
- AWS server ↔ **NOAA DIVER** (Data Integration Visualization Exploration and Reporting)
- CPRA **CIMS** (Coastal Information Management System)

**Development Partnership:**
- All activities developed with NOAA DIVER and CPRA CIMS collaboration

---

## Critical Gap Analysis for NestScope

### What They're Building

 Better georeferencing workflow
 GIS-based dotting interface
 Web GIS frontend for data access
 Integration with NAIP orthoimagery
 Self-service query tools

### What They're NOT Building (But Need)

 **Automated bird detection** (still manual dotting in GIS)
 **Real-time processing** (still post-survey workflow)
 **AI-powered species classification**
 **Edge deployment** (in-field processing)
 **Batch processing of 350,000+ undotted images**
 **Quality control automation**
 **Anomaly detection** (unusual population changes)

---

## The Strategic Opening for NestScope

### Their 5-Year Roadmap

**2024-2028:** Upgrade workflows, create web GIS, improve data access

**Timeline:** Incremental improvements over 5 years

### NestScope's Disruptive Opportunity

**What if you could process the entire 350,000 image backlog in weeks, not decades?**

**What if surveyors could see bird counts in real-time during flights?**

**What if the system could flag concerning population declines automatically?**

This is where NestScope's AI capabilities create **10x value** over their planned improvements. They're building a better interface to manual processes. NestScope **eliminates the manual process entirely**.

---

## Alignment with Monitoring and Adaptive Management (MAM)

**Fundamental Objectives 1 and 2:**
- Restore, maintain, and enhance nesting, foraging, and loafing habitat
- Support shrub and ground-nesting birds across coastal Louisiana
- Sufficient elevation for supratidal habitat and vegetation above intertidal zone

**NestScope's Contribution:**
- Rapid baseline assessments for restoration sites
- Post-restoration monitoring automation
- Long-term trend detection
- Cost-effective monitoring enables MORE restoration projects (limited monitoring budgets can cover more sites)

---

**Key Takeaway:** The Water Institute is investing 5 years and significant funding to improve data workflows. They're focused on GIS integration but **not addressing the AI/ML automation opportunity**. This is NestScope's competitive advantage.
