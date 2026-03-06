# Expert Dotting Data Reconstruction Plan

##  Project Overview

**Goal**: Reconstruct expert bird annotations from screenshot images and create a YOLO detection dataset

**Data Sources**:
- **High-res images**: ~15,000-20,000 aerial photos (2010-2021) at `twi-aviandata.s3.amazonaws.com/HighResolutionImages/`
- **Dotted screenshots**: ~22,108 expert-annotated images at `twi-aviandata.s3.amazonaws.com/DottedImages/`
- **Metadata**: 3.2M line GeoJSON with GPS coordinates and EXIF data for source images

## 🧩 The Challenge

Dotted screenshots show **expert-placed dots** marking individual birds on aerial photos. We need to:
1. **Match** dotted screenshots to original high-res source images
2. **Extract** dot coordinates from screenshots
3. **Transform** screen coordinates → high-res image coordinates
4. **Convert** to YOLO format (normalized bounding boxes)

##  Phase-by-Phase Approach

### Phase 1: Data Discovery & Matching ( EXPLORATORY)

**What**: Build a mapping between dotted screenshots and source high-res images

**How**:
1. Parse metadata.geojson.gz to create lookup table: `filename → {date, camera, GPS, EXIF}`
2. Crawl DottedImages S3 bucket to catalog all screenshots with naming patterns
3. Use date/colony/area codes to match screenshots to source images
4. Handle naming variations across years (2010: "7May10DLJ1Area1", 2018: "21May18_CookeIsl_Area1", etc.)

**Outputs**:
- `image_mapping.json`: Maps dotted screenshot → source high-res image
- `unmatched_screenshots.json`: Screenshots without source matches
- `coverage_report.json`: Statistics on matched vs unmatched data

**Key Pattern Examples**:
```
Dotted: "7May10DLJ1Area1.JPG"
   ↓ (extract: date=7May10, colony=DLJ1, area=1)
Source: "7 May 2010 Camera 1 Card 1 [NNN].JPG"
   ↓ (match on date + camera metadata)
Match: Found in /2010/May 2010/7 May 2010/7 May 2010 Camera 1 Card 1/
```

### Phase 2: Dot Extraction ( COMPUTER VISION)

**What**: Extract dot coordinates from annotated screenshots using image processing

**How**:
1. Download sample dotted screenshots (20-50 images from different years)
2. Analyze dot characteristics:
   - Color (likely bright colors: red, yellow, green for different species)
   - Size (typically small circles, 3-10px diameter)
   - Contrast against background
3. Implement dot detection pipeline:
   - Color filtering (HSV color space)
   - Morphological operations (erosion/dilation)
   - Contour detection
   - Circle/blob detection (cv2.HoughCircles or SimpleBlobDetector)
4. Validate on 20 test images manually

**Outputs**:
- `dot_extractor.py`: OpenCV-based dot detection module
- `dot_colors.json`: Color ranges for different species/annotators
- `extraction_test_results/`: 20 test images with detected dots overlaid

**Validation Metrics**:
- Precision: % of detected dots that are real annotations
- Recall: % of real annotations detected
- Target: >95% precision, >90% recall

### Phase 3: Coordinate Transformation ( GEOMETRY)

**What**: Map screenshot coordinates to original high-res image coordinates

**Challenge**: Screenshots are often:
- **Cropped** regions of full images
- **Scaled down** for display (e.g., 1920x1080 screenshot of 5472x3648 image)
- **Windowed** with toolbars/UI elements

**Approaches** (in order of preference):

#### Approach A: Template Matching (PREFERRED)
1. Extract visible image region from screenshot (remove UI)
2. Use template matching to find position in source high-res image
3. Calculate scale factor: `scale = source_width / screenshot_visible_width`
4. Transform dot coordinates:
   ```python
   source_x = (dot_x - screenshot_offset_x) * scale
   source_y = (dot_y - screenshot_offset_y) * scale
   ```

#### Approach B: EXIF/Metadata Matching
1. If screenshots contain EXIF data → direct match to source
2. Extract GPS coordinates from both → match spatially
3. Use timestamp correlation for ambiguous matches

#### Approach C: Feature Matching (FALLBACK)
1. Extract SIFT/ORB keypoints from both images
2. Match features using FLANN/BFMatcher
3. Compute homography transformation matrix
4. Apply transformation to dot coordinates

**Outputs**:
- `coordinate_transformer.py`: Handles all 3 approaches with fallback logic
- `transformation_validation/`: 20 images showing source + transformed dots
- `transformation_accuracy.json`: Measured error metrics (pixel distance)

### Phase 4: YOLO Dataset Generation (📦 DATA PIPELINE)

**What**: Convert dot coordinates to YOLO bounding boxes and create training dataset

**How**:
1. For each dot coordinate `(x, y)`:
   - Generate bounding box centered on dot
   - Box size: estimated from bird size (start with 32x32px, make configurable)
   - Normalize to [0, 1] range: `x_norm = x / image_width`
2. Create YOLO format labels:
   ```
   <class_id> <x_center_norm> <y_center_norm> <width_norm> <height_norm>
   ```
3. Organize dataset:
   ```
   dataset/
   ├── images/
   │   ├── train/
   │   ├── val/
   │   └── test/
   ├── labels/
   │   ├── train/
   │   ├── val/
   │   └── test/
   ├── classes.txt
   └── data.yaml
   ```
4. Apply train/val/test split (70/20/10)
5. Generate species-specific labels if database info available

**Outputs**:
- `dataset/`: Full YOLO detection dataset
- `dataset_statistics.json`: Class distribution, image sizes, box size distribution
- `visualization_samples/`: 50 sample images with boxes drawn for QA

### Phase 5: Database Mining ( GOLD STANDARD)

**What**: Extract structured annotation data from Access database files

**Why**: Database files (.mdb, .accdb) likely contain:
- Exact bird counts per area
- Species classifications
- Quality control flags
- Annotator IDs
- Possibly even coordinate data!

**How**:
1. Download sample database files from DottedImages bucket
2. Use `mdb-tools` or `pyodbc` to read Access databases
3. Explore schema: tables, relationships, field names
4. Extract relevant annotation data
5. Cross-reference with image data

**Potential Schema**:
```sql
-- Hypothetical structure
TABLE Observations
  - ObservationID
  - ImageName
  - SpeciesCode
  - Count
  - DotX, DotY (if we're lucky!)
  - AnnotatorID
  - QualityFlag
```

**Outputs**:
- `database_schema.json`: Documented structure of all database files
- `extracted_annotations.csv`: Structured annotation data
- `database_to_yolo.py`: Pipeline to convert database records to YOLO format

**High-Value Outcome**: If databases contain coordinates, this becomes the PRIMARY data source (most accurate!)

##  Test Plan: 20 Image Validation

**Before full pipeline run**, validate with 20 diverse test images:

### Test Image Selection Criteria:
- **5 images** from 2010-2013 (early naming pattern)
- **5 images** from 2015 (transition period)
- **5 images** from 2018 (flat structure year)
- **5 images** from 2021 (recent data)

- Mix of colonies (DLJ, KMR, PJC, etc.)
- Various bird densities (sparse, medium, dense)
- Different image qualities/conditions

### Validation Process:
1. Run full pipeline on 20 test images
2. Generate visualizations in `vis/` folder:
   ```
   vis/
   ├── 001_7May10DLJ1Area1_original.jpg       (source high-res image)
   ├── 001_7May10DLJ1Area1_dotted.jpg         (dotted screenshot)
   ├── 001_7May10DLJ1Area1_extracted.jpg      (detected dots overlay)
   ├── 001_7May10DLJ1Area1_transformed.jpg    (dots mapped to source)
   ├── 001_7May10DLJ1Area1_yolo.jpg           (YOLO boxes drawn)
   └── 001_7May10DLJ1Area1_report.json        (metrics)
   ```
3. Manual QA: Inspect each set of 5 images
4. Measure:
   - Match rate (screenshot → source)
   - Dot extraction accuracy
   - Coordinate transformation error
   - Box placement quality

**Success Criteria**:
-  18/20 images successfully matched to source
-  >90% dot extraction recall
-  <5px average transformation error
-  Boxes centered on birds (visual inspection)

## 🛠 Technical Implementation

### Tools & Libraries:
```python
# Core
import cv2                    # Image processing, dot detection
import numpy as np            # Numerical operations
import pandas as pd           # Data manipulation
from PIL import Image         # Image I/O

# S3 Access
import boto3                  # AWS S3 client
import requests               # HTTP downloads

# Data Formats
import json                   # Metadata handling
import gzip                   # Decompress metadata.geojson.gz
import pyodbc                 # Access database reading

# Geospatial (if needed)
import geojson               # Parse GeoJSON
from shapely.geometry import Point  # GPS calculations
```

### Key Scripts:
1. `s3_crawler.py` - Download and catalog S3 bucket contents
2. `image_matcher.py` - Match dotted screenshots to source images
3. `dot_extractor.py` - Extract dot coordinates from screenshots
4. `coordinate_transformer.py` - Transform screenshot → source coordinates
5. `yolo_generator.py` - Generate YOLO dataset from coordinates
6. `database_extractor.py` - Mine Access databases for annotations
7. `pipeline_runner.py` - Orchestrate full end-to-end pipeline
8. `validation_report.py` - Generate QA visualizations and metrics

### Configuration:
```yaml
# config.yaml
s3:
  bucket: twi-aviandata
  high_res_prefix: HighResolutionImages/
  dotted_prefix: DottedImages/

dot_detection:
  colors:
    red: [[0, 100, 100], [10, 255, 255]]    # HSV ranges
    yellow: [[20, 100, 100], [30, 255, 255]]
    green: [[40, 100, 100], [80, 255, 255]]
  min_dot_size: 3
  max_dot_size: 15

yolo:
  box_size: 32  # pixels
  classes:
    0: bird_generic
    # Add species classes from database
  train_split: 0.7
  val_split: 0.2
  test_split: 0.1
```

##  Expected Outcomes

### Dataset Size (Conservative Estimate):
- **Matched images**: ~15,000 (assuming 70% match rate from 22K dotted screenshots)
- **Estimated annotations**: ~500,000 - 2,000,000 birds (based on typical colony sizes)
- **Dataset quality**: Gold standard (expert-annotated)

### Use Cases:
1. **Train bird detection models** (better than current models)
2. **Train species classification models** (if database has species data)
3. **Validate existing NestVision models** against expert ground truth
4. **Historical analysis** of colony population changes (2010-2021)

## 🚧 Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Dotted screenshots don't match source images | High | Use multiple matching strategies (name, EXIF, features) |
| Dot colors vary across years/annotators | Medium | Adaptive color detection, manual calibration per year |
| Screenshots are highly cropped/transformed | Medium | Template matching + feature-based fallback |
| Database files are corrupted/unreadable | Low | Multiple database file versions available |
| S3 bucket access limits/costs | Low | Cache downloads, process incrementally |

##  Success Metrics

**Phase 1**:
- Match rate >70% (dotted → source)
- Complete catalog of all S3 data

**Phase 2**:
- Dot extraction precision >95%, recall >90%
- Works across different years/annotation styles

**Phase 3**:
- Transformation error <5px average
- Visual validation on 100 random images

**Phase 4**:
- Valid YOLO dataset with train/val/test splits
- Documentation and data.yaml file

**Phase 5**:
- Successfully extract data from >50% of database files
- Find coordinate data (if exists)

## 🗓 Timeline Estimate

- **Phase 1** (Discovery): 2-3 days
- **Phase 2** (Dot Extraction): 3-4 days
- **Phase 3** (Transformation): 2-3 days
- **Phase 4** (YOLO Generation): 1-2 days
- **Phase 5** (Database Mining): 2-3 days
- **Testing & Validation**: 2 days throughout

**Total**: ~12-17 days for full pipeline

##  Learning Opportunities

This project teaches:
1. **Data archaeology**: Mining existing datasets for ML training
2. **Computer vision pipelines**: Image processing, coordinate transformations
3. **Dataset engineering**: Creating high-quality training data
4. **Geospatial data**: GPS coordinates, image georeferencing
5. **Legacy data formats**: Working with Access databases, various naming conventions
6. **Scale challenges**: Processing 15K+ images efficiently
7. **Quality assurance**: Building validation into every pipeline stage

---

**Next Steps**:
1. Review this plan
2. Start with Phase 1 (Discovery) + Phase 5 (Database Mining) in parallel
3. Test with 20 images before scaling up
