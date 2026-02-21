# NestScope Technical Deep Dive

## Project Overview

**NestScope** is a comprehensive AI-powered Gulf Coast avian monitoring platform that combines natural language database queries, computer vision bird detection, and manual annotation tools. The platform analyzes 10+ years of bird colony observation data (2010-2021) across Texas, Louisiana, Mississippi, Alabama, and Florida.

## Technology Stack & Architecture

### Core Components

#### 1. Backend (FastAPI Server)
- **Framework**: FastAPI (Python async web framework)
- **Language**: Python 3.8+
- **Database**: SQLite with pandas for data manipulation
- **AI Integration**: OpenRouter API (OpenAI-compatible) for LLM-powered SQL generation
- **Computer Vision**: ONNX Runtime, YOLO models, SAHI (Slicing Aided Hyper Inference)
- **Key Dependencies**:
  - `fastapi==0.109.0`
  - `uvicorn[standard]==0.27.0`
  - `pandas==2.1.4`
  - `openai==1.10.0`
  - `python-dotenv==1.0.0`
  - `pydantic==2.5.3`
  - `ultralytics`
  - `opencv-python`
  - `python-multipart`

#### 2. Frontend (Streamlit Application)
- **Framework**: Streamlit (Python web app framework)
- **Architecture**: Multi-page application with component-based structure
- **Features**: Interactive data visualizations (Plotly), maps (Folium), file uploads
- **Pages**:
  - NestChat (natural language queries)
  - NestVision (bird detection interface)
- **Key Dependencies**:
  - `streamlit>=1.28.0`
  - `plotly>=5.18.0`
  - `folium>=0.15.0`
  - `streamlit-folium>=0.15.0`
  - `Pillow>=10.0.0`

#### 3. Labeller (Annotation Tool)
- **Framework**: Flask (Python web framework)
- **Purpose**: Data annotation and labeling interface for training ML models
- **Features**: Image annotation, MobileSAM integration, dataset management
- **Key Dependencies**:
  - `flask`
  - `torch`
  - `opencv-python`
  - `numpy`
  - `pyyaml`

### Machine Learning & Data Pipeline

#### Models & Training
- **Detection Models**: YOLOv8, custom ONNX models
- **Segmentation**: MobileSAM (Ultralytics)
- **Training Framework**: Ultralytics YOLO ecosystem
- **Data Processing**: Custom scripts for dataset preparation, augmentation, and validation

#### Pre-trained Models
- `models/seconditer.onnx` - YOLOv8 bird detection model (1024x1024 input)
- `models/mobile_sam.pt` - MobileSAM segmentation model
- `models/best.pt` - Best trained model checkpoint

## Database Schema & Data Structure

### SQLite Database: `data/bird_data_complete.db`

**Database Size**: ~10.5 MB
**Total Records**: 49,759 across 6 tables
**Created**: 2026-02-07T21:49:08.457636

### Table Schemas

#### 1. `species_codes` (73 rows)
Species lookup table mapping codes to names.
```sql
Columns:
- SpeciesCode (TEXT) - Species abbreviation code
- SpeciesName (TEXT) - Full species name
```

#### 2. `colony_coordinates` (87 rows)
Geographic coordinates for bird colonies.
```sql
Columns:
- ColonyID (TEXT)
- ActiveInventory (TEXT)
- ColonyGroupBuffer (TEXT)
- ColonyName (TEXT)
- State (TEXT)
- Year_ChandeleursOnly (REAL)
- Longitude (REAL)
- Latitude (REAL)
- GeoRegion (TEXT)
- ExtrapArea (TEXT)
- TerrestEcoRegion (TEXT)
- MarineEcoRegion (TEXT)
- FormerNames (TEXT)
- OrigDotterID (TEXT)
- NOTES August 2022 (TEXT)
- Colony Years Within 500 m (TEXT)
```

#### 3. `colony_inventory` (592 rows)
Comprehensive colony inventory data.
```sql
Columns:
- ColonyID (TEXT)
- ActiveInventory (TEXT)
- ColonyGroupBuffer (TEXT)
- ColonyName (TEXT)
- State (TEXT)
- Longitude (REAL)
- Latitude (REAL)
- PrimaryHabitat (TEXT)
- LandForm (TEXT)
- GeoRegion (TEXT)
- ExtrapArea (TEXT)
- TerrestEcoRegion (TEXT)
- MarineEcoRegion (TEXT)
- FormerNames (TEXT)
- OrigDotterID (TEXT)
- NOTES August 2022 (TEXT)
```

#### 4. `colony_site_notes` (4,035 rows)
Field observation notes and site-specific data.
```sql
Columns:
- ActiveMayJune? (TEXT)
- AdditionalNotes (TEXT)
- ColonyName (TEXT)
- CombineMayJuneData? (TEXT)
- Date (TEXT)
- Dotter (TEXT)
- Dotter'sColonyNumber (TEXT)
- Habitat (TEXT)
- ID (REAL)
- Latitude (REAL)
- Longitude (REAL)
- Notes (TEXT)
- Oil (TEXT)
- SpeciesCode (TEXT)
- Year (REAL)
```

#### 5. `colony_totals` (5,931 rows)
Aggregated colony data with nest/bird counts.
```sql
Columns:
- ID (REAL)
- Year (REAL)
- Date (TEXT)
- State (TEXT)
- GeoRegion (TEXT)
- ColonyName (TEXT)
- Latitude (REAL)
- Longitude (REAL)
- SpeciesCode (TEXT)
- Nests (REAL)
- Birds (REAL)
- Notes (TEXT)
- BestForBPE (TEXT)
- CombinedMayJuneTotal (TEXT)
```

#### 6. `species_data_2010` (9,557 rows)
Detailed species observations for 2010.
```sql
Columns:
- AutoID (REAL)
- Year (REAL)
- Date (TEXT)
- ColonyName (TEXT)
- Latitude (REAL)
- Longitude (REAL)
- DottingAreaNumber (REAL)
- CameraNumber (REAL)
- CardNumber (REAL)
- PhotoNumber (REAL)
- PQ (TEXT)
- SpeciesCode (TEXT)
- WBN (REAL) - White Birds Nesting
- ChickNestw/outAdult (REAL)
- AbandNest (REAL) - Abandoned Nests
- EmptyNest (REAL)
- PBN (REAL) - Probable Breeding Nests
- Site (REAL)
- Brood (REAL)
- OtherAdultsInColony (REAL)
- OtherImmInColony (REAL)
- Chicks/Nestlings (REAL)
- RoostingBirds (REAL)
- RoostingAdults (REAL)
- RoostingImmatures (REAL)
- UnknownAge (REAL)
- Dotter (TEXT)
- Dotter'sColonyNumber (TEXT)
- DateDotted (TEXT)
- Notes (TEXT)
```

#### 7. `species_data_2011_2013` (15,920 rows)
Detailed species observations for 2011-2013.
```sql
Columns:
- AutoID (REAL)
- Year (REAL)
- Date (TEXT)
- ColonyName (TEXT)
- DottingAreaNumber (REAL)
- CameraNumber (REAL)
- CardNumber (REAL)
- PhotoNumber (REAL)
- PQ (TEXT)
- SpeciesCode (TEXT)
- WBN (REAL)
- ChickNest (REAL)
- ChickNestw/outAdult (REAL)
- Brood (REAL)
- AbandNest (REAL)
- EmptyNest (REAL)
- PBN (REAL)
- Site (REAL)
- OtherAdultsInColony (REAL)
- OtherImmInColony (REAL)
- Chicks/Nestlings (REAL)
- RoostingBirds (REAL)
- RoostingAdults (REAL)
- RoostingImmatures (REAL)
- UnknownAge (REAL)
- Dotter (TEXT)
- DateDotted (TEXT)
- BestForBPE (TEXT)
- Notes (TEXT)
- AdditionalNotes (TEXT)
```

#### 8. `species_data_2015_2021` (23,747 rows)
Detailed species observations for 2015-2021.
```sql
Columns:
- AutoID (REAL)
- Year (REAL)
- Date (TEXT)
- ColonyName (TEXT)
- Subcolony (TEXT)
- DottingAreaNumber (REAL)
- CameraNumber (REAL)
- CardNumber (REAL)
- PhotoNumber (REAL)
- PQ (TEXT)
- SpeciesCode (TEXT)
- WBN (REAL)
- ChickNest (REAL)
- ChickNestw/outAdult (REAL)
- Brood (REAL)
- AbandNest (REAL)
- EmptyNest (REAL)
- PBN (REAL)
- Territory (REAL)
- Site (REAL)
- OtherBirds (REAL)
- Dotter (TEXT)
- DateDotted (TEXT)
- BestForBPE (TEXT)
- Notes (TEXT)
- AdditionalNotes (TEXT)
```

### Database Indexes
```sql
-- Performance optimization indexes
CREATE INDEX IF NOT EXISTS idx_species_code ON species_codes(SpeciesCode);
CREATE INDEX IF NOT EXISTS idx_colony_id ON colony_coordinates(ColonyID);
CREATE INDEX IF NOT EXISTS idx_colony_name ON colony_coordinates(ColonyName);
CREATE INDEX IF NOT EXISTS idx_inventory_colony ON colony_inventory(ColonyName);
CREATE INDEX IF NOT EXISTS idx_inventory_state ON colony_inventory(State);
CREATE INDEX IF NOT EXISTS idx_inventory_georegion ON colony_inventory(GeoRegion);
CREATE INDEX IF NOT EXISTS idx_notes_colony ON colony_site_notes(ColonyName);
CREATE INDEX IF NOT EXISTS idx_notes_year ON colony_site_notes(Year);
CREATE INDEX IF NOT EXISTS idx_notes_species ON colony_site_notes(SpeciesCode);
CREATE INDEX IF NOT EXISTS idx_totals_year ON colony_totals(Year);
CREATE INDEX IF NOT EXISTS idx_totals_colony ON colony_totals(ColonyName);
CREATE INDEX IF NOT EXISTS idx_totals_species ON colony_totals(SpeciesCode);
CREATE INDEX IF NOT EXISTS idx_totals_state ON colony_totals(State);
-- Species data indexes for all three tables
CREATE INDEX IF NOT EXISTS idx_[table]_year ON [table](Year);
CREATE INDEX IF NOT EXISTS idx_[table]_colony ON [table](ColonyName);
CREATE INDEX IF NOT EXISTS idx_[table]_species ON [table](SpeciesCode);
CREATE INDEX IF NOT EXISTS idx_[table]_dotter ON [table](Dotter);
```

## Why SQLite?

### Advantages for This Project

1. **Zero Configuration**: No server setup required - single file database
2. **ACID Compliance**: Reliable transactions and data integrity
3. **Cross-Platform**: Works identically on Windows, macOS, Linux
4. **Small Footprint**: ~10.5MB database file for 50K+ records
5. **SQL Standard**: Full SQL support for complex queries
6. **Embedded**: No separate database server process needed
7. **Backup Simplicity**: Single file copy for complete backup
8. **Performance**: Excellent for read-heavy analytical workloads
9. **Python Integration**: Native support via sqlite3 module
10. **Concurrent Access**: Multiple readers, single writer model works for this use case

### SQLite Limitations & Mitigations

1. **Single Writer**: Only one process can write at a time
   - **Mitigation**: Read-heavy workload fits perfectly
   - **Mitigation**: FastAPI handles concurrent requests appropriately

2. **No Built-in Replication**: Not designed for high availability
   - **Mitigation**: Single-user analytical tool, not enterprise system
   - **Mitigation**: Easy to backup and restore

3. **Limited Concurrent Connections**: Default limit of 1000
   - **Mitigation**: Web application with moderate traffic
   - **Mitigation**: Connection pooling not needed

## SQLite Versioning & Schema Evolution

### Current Approach: Complete Rebuild
The project currently uses a "nuclear rebuild" approach:
```bash
python scripts/data_management/import_all_to_sqlite.py
```
This completely rebuilds the database from CSV sources.

### Future Versioning Strategies

#### Option 1: Alembic Migration System
Implement proper database migrations using Alembic (SQLAlchemy's migration tool):

**Setup**:
```bash
pip install alembic
alembic init alembic
```

**Migration Structure**:
```
migrations/
├── versions/
│   ├── 001_initial_schema.py
│   ├── 002_add_new_columns.py
│   ├── 003_create_indexes.py
│   └── 004_data_transforms.py
├── alembic.ini
└── env.py
```

**Benefits**:
- Incremental schema changes
- Rollback capability
- Version history
- Automated migration scripts

#### Option 2: Schema Version Table
Add a simple versioning table to track schema versions:

```sql
CREATE TABLE schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    description TEXT
);
```

**Migration Logic**:
```python
def apply_migrations(db_path):
    current_version = get_current_version(db_path)
    migrations = [
        (1, "Initial schema", apply_v1_migrations),
        (2, "Add new columns", apply_v2_migrations),
        (3, "Create performance indexes", apply_v3_migrations),
    ]
    
    for version, desc, migration_func in migrations:
        if version > current_version:
            migration_func(db_path)
            update_version(db_path, version, desc)
```

#### Option 3: Git-Based Schema Tracking
Store schema SQL files in Git with semantic versioning:

```
schemas/
├── v1.0.0/
│   ├── create_tables.sql
│   ├── indexes.sql
│   └── seed_data.sql
├── v1.1.0/
│   └── add_new_table.sql
└── v2.0.0/
    └── schema_restructure.sql
```

**Migration Script**:
```bash
#!/bin/bash
TARGET_VERSION=$1
CURRENT_VERSION=$(get_current_db_version)

if [ "$TARGET_VERSION" != "$CURRENT_VERSION" ]; then
    echo "Migrating from $CURRENT_VERSION to $TARGET_VERSION"
    apply_schema_changes $CURRENT_VERSION $TARGET_VERSION
    update_db_version $TARGET_VERSION
fi
```

#### Recommended Approach: Hybrid System
Combine multiple strategies for robustness:

1. **Alembic** for schema migrations
2. **Version table** for tracking
3. **CSV backups** for data safety
4. **Git tagging** for releases

**Implementation Plan**:
```python
# migrations/env.py
from alembic import context
from sqlalchemy import create_engine
import sqlite3

def run_migrations_online():
    connectable = create_engine(f"sqlite:///{db_path}")
    
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            version_table='alembic_version'
        )
        
        with context.begin_transaction():
            context.run_migrations()
```

## SAHI (Slicing Aided Hyper Inference)

### What is SAHI?

**SAHI** (Slicing Aided Hyper Inference) is a library that enables running object detection models on large images by intelligently slicing them into smaller, overlapping patches. This solves the common problem where detection models are trained on smaller images (e.g., 1024x1024) but need to process much larger aerial or satellite imagery.

### How SAHI Works

#### Core Algorithm
1. **Image Slicing**: Large input image divided into smaller patches with overlap
2. **Inference**: Each patch processed independently by the detection model
3. **Detection Merging**: Results combined using Non-Maximum Suppression (NMS)
4. **Coordinate Transformation**: Patch-relative coordinates converted to full-image coordinates

#### Key Parameters in NestScope
```python
# SAHI configuration in inference.py
slice_height = 1024  # Patch height
slice_width = 1024   # Patch width
overlap_height_ratio = 0.2  # 20% vertical overlap
overlap_width_ratio = 0.2   # 20% horizontal overlap
```

#### Benefits
1. **Large Image Support**: Process images of any size
2. **Small Object Detection**: Better detection of small birds in large aerial photos
3. **Memory Efficiency**: Smaller patches fit in GPU memory
4. **Accuracy Preservation**: Overlap prevents missed detections at patch boundaries

### SAHI vs Fast Mode Comparison

| Aspect | Fast Mode | SAHI Mode |
|--------|-----------|-----------|
| **Speed** | Very Fast | Slower (20-50x) |
| **Accuracy** | Good for large objects | Better for small objects |
| **Memory Usage** | Low | Moderate |
| **Use Case** | Preview, real-time | High-precision analysis |
| **Implementation** | Downsampling + single inference | Intelligent slicing + NMS |

### SAHI Integration in NestScope

```python
# From server/cv_tools/inference.py
def _predict_with_sahi(self, image_path: str, conf_threshold: float = 0.25):
    """Use SAHI for smart sliced prediction on large images"""
    
    # Load image
    image = cv2.imread(image_path)
    height, width = image.shape[:2]
    
    # SAHI parameters
    slice_size = self.imgsz
    overlap_ratio = 0.2  # 20% overlap
    
    # Create slices with overlap
    slices = slice_image(
        image=image,
        slice_height=slice_size,
        slice_width=slice_size,
        overlap_height_ratio=overlap_ratio,
        overlap_width_ratio=overlap_ratio
    )
    
    all_detections = []
    
    # Process each slice
    for slice_data in slices:
        slice_image = slice_data["image"]
        slice_bbox = slice_data["bbox"]
        
        # Run inference on slice
        detections = self._run_inference(slice_image, conf_threshold)
        
        # Transform coordinates back to full image
        for detection in detections:
            detection["bbox"] = transform_bbox_to_original(
                detection["bbox"], slice_bbox
            )
        
        all_detections.extend(detections)
    
    # Apply NMS across all detections
    final_detections = apply_nms(all_detections)
    
    return final_detections
```

## Training a Smart Classifier Model

### Current Training Pipeline

#### Dataset: `labeller/nestvision/`
- **Images**: 500 aerial images (1024x1024px)
- **Format**: YOLO annotation format (normalized coordinates)
- **Classes**: Single class (bird) with background images
- **Split**: 85% train / 15% validation (stratified)

#### Training Script: `VisionTrain/train_improved_model.py`

**Key Features**:
1. **Multiscale Training**: Variable input sizes (512-1536px)
2. **Heavy Augmentation**: 10,000+ variations per epoch
3. **Early Stopping**: Patience=20 to prevent overfitting
4. **Balanced Loss**: Precision + Recall optimization

#### Training Configuration
```python
# From train_improved_model.py
model = YOLO('yolov8n.pt')  # Start from pretrained

results = model.train(
    data='nestvision/data.yaml',
    epochs=80,
    patience=20,  # Early stopping
    imgsz=1024,
    batch=8,
    lr0=0.003,  # Learning rate
    weight_decay=0.0005,  # Regularization
    multi_scale=True,  # Variable input sizes
    rect=False,  # Allow size variation
    mosaic=1.0,  # Always use mosaic
    mixup=0.1,  # Blend images
    # Heavy augmentation
    hsv_h=0.015,  # Hue variation
    hsv_s=0.7,    # Saturation
    hsv_v=0.4,    # Brightness
    degrees=10,   # Rotation
    translate=0.1, # Translation
    scale=0.5,    # Scaling
    shear=0.0,    # No shear
    flipud=0.5,   # Vertical flip
    fliplr=0.5,   # Horizontal flip
)
```

### Advanced Training Strategies

#### 1. Curriculum Learning
Train on easy examples first, gradually increase difficulty:

```python
# Phase 1: Easy examples (large, clear birds)
# Phase 2: Medium difficulty
# Phase 3: Hard examples (small, occluded birds)

def curriculum_training():
    phases = [
        {"epochs": 20, "imgsz": 640, "difficulty": "easy"},
        {"epochs": 30, "imgsz": 1024, "difficulty": "medium"},
        {"epochs": 30, "imgsz": 1280, "difficulty": "hard"},
    ]
    
    for phase in phases:
        # Filter dataset by difficulty
        train_data = filter_by_difficulty(phase["difficulty"])
        
        # Train with phase-specific settings
        model.train(
            data=train_data,
            epochs=phase["epochs"],
            imgsz=phase["imgsz"],
            resume=True  # Continue from previous phase
        )
```

#### 2. Hard Negative Mining
Focus training on false positive examples:

```python
def hard_negative_mining(model, dataset):
    """Identify and add hard negative examples"""
    
    hard_negatives = []
    
    for image in dataset:
        predictions = model.predict(image)
        
        # Find false positives (predictions on background)
        for pred in predictions:
            if pred["confidence"] > 0.5 and not is_true_positive(pred, image):
                hard_negatives.append({
                    "image": image,
                    "bbox": pred["bbox"],
                    "label": "hard_negative"
                })
    
    # Add hard negatives to training set
    augment_dataset_with_hard_negatives(hard_negatives)
```

#### 3. Ensemble Training
Train multiple models and combine predictions:

```python
def train_ensemble(num_models=3):
    models = []
    
    for i in range(num_models):
        # Different random seeds for diversity
        model = YOLO('yolov8n.pt')
        
        results = model.train(
            data='nestvision/data.yaml',
            epochs=60,
            seed=i,  # Different seed
            # Vary hyperparameters slightly
            lr0=0.003 + random.uniform(-0.001, 0.001),
            weight_decay=0.0005 + random.uniform(-0.0001, 0.0001),
        )
        
        models.append(model)
    
    return models

def ensemble_predict(models, image):
    """Combine predictions from multiple models"""
    all_predictions = []
    
    for model in models:
        preds = model.predict(image)
        all_predictions.extend(preds)
    
    # Weighted NMS
    final_predictions = weighted_nms(all_predictions)
    return final_predictions
```

#### 4. Domain Adaptation
Adapt model for different environments:

```python
def domain_adaptation(source_domain, target_domain):
    """Adapt model from source to target domain"""
    
    # Source: Training images
    # Target: Deployment environment
    
    # Method 1: Fine-tuning
    model = YOLO('models/best.pt')
    model.train(
        data=target_domain,  # Target environment data
        epochs=20,
        lr0=0.0001,  # Lower learning rate
        freeze=10,   # Freeze early layers
    )
    
    # Method 2: Adversarial training
    # Train domain classifier to confuse source/target
    # This makes features domain-invariant
```

#### 5. Active Learning
Select most informative samples for labeling:

```python
def active_learning_selection(model, unlabeled_pool, budget=100):
    """Select most informative samples for human labeling"""
    
    uncertainties = []
    
    for image in unlabeled_pool:
        predictions = model.predict(image)
        
        # Calculate uncertainty (least confident predictions)
        if predictions:
            max_conf = max(pred["confidence"] for pred in predictions)
            uncertainty = 1.0 - max_conf
        else:
            uncertainty = 1.0  # No predictions = high uncertainty
        
        uncertainties.append((image, uncertainty))
    
    # Select most uncertain samples
    uncertainties.sort(key=lambda x: x[1], reverse=True)
    selected_samples = uncertainties[:budget]
    
    return [sample for sample, _ in selected_samples]
```

### Model Evaluation & Metrics

#### Comprehensive Evaluation Script
```python
def evaluate_model(model_path, test_data):
    """Comprehensive model evaluation"""
    
    model = YOLO(model_path)
    
    # Standard metrics
    results = model.val(data=test_data)
    
    # Custom metrics for bird detection
    metrics = {
        "precision": results.box.p,
        "recall": results.box.r,
        "mAP50": results.box.map50,
        "mAP50-95": results.box.map,
    }
    
    # Size-based analysis
    size_analysis = analyze_by_object_size(model, test_data)
    metrics.update(size_analysis)
    
    # Environmental analysis
    env_analysis = analyze_by_environment(model, test_data)
    metrics.update(env_analysis)
    
    return metrics

def analyze_by_object_size(model, test_data):
    """Analyze performance by bird size"""
    
    size_bins = {
        "tiny": (0, 32),      # Very small birds
        "small": (32, 96),    # Small birds
        "medium": (96, 256),  # Medium birds
        "large": (256, 512),  # Large birds
    }
    
    size_metrics = {}
    
    for size_name, (min_size, max_size) in size_bins.items():
        # Filter test set by object size
        filtered_data = filter_by_size(test_data, min_size, max_size)
        
        if filtered_data:
            results = model.val(data=filtered_data)
            size_metrics[f"{size_name}_mAP"] = results.box.map50
    
    return size_metrics
```

### Production Deployment Strategy

#### Model Versioning & A/B Testing
```python
class ModelManager:
    def __init__(self):
        self.models = {
            "current": "models/best.pt",
            "candidate": "models/candidate.pt",
        }
        self.metrics = {}
    
    def deploy_candidate(self, candidate_path):
        """Deploy new model with A/B testing"""
        
        # Load candidate model
        self.models["candidate"] = candidate_path
        
        # Run A/B test
        ab_results = self.run_ab_test()
        
        if ab_results["candidate_better"]:
            # Promote candidate to current
            self.promote_candidate()
            return True
        
        return False
    
    def run_ab_test(self):
        """Run A/B test between current and candidate"""
        
        test_images = load_test_images()
        
        current_metrics = evaluate_model(
            self.models["current"], test_images
        )
        
        candidate_metrics = evaluate_model(
            self.models["candidate"], test_images
        )
        
        # Statistical significance test
        significant = statistical_test(
            current_metrics, candidate_metrics
        )
        
        return {
            "current_metrics": current_metrics,
            "candidate_metrics": candidate_metrics,
            "significant": significant,
            "candidate_better": candidate_metrics["mAP50"] > current_metrics["mAP50"]
        }
```

#### Continuous Learning Pipeline
```python
class ContinuousLearner:
    def __init__(self, model_path):
        self.model = YOLO(model_path)
        self.new_data_buffer = []
        self.retrain_threshold = 1000  # Retrain every 1000 new samples
    
    def add_feedback(self, image, true_detections, predicted_detections):
        """Add human feedback for continuous learning"""
        
        self.new_data_buffer.append({
            "image": image,
            "true_detections": true_detections,
            "predicted_detections": predicted_detections,
        })
        
        if len(self.new_data_buffer) >= self.retrain_threshold:
            self.retrain_model()
    
    def retrain_model(self):
        """Retrain model with accumulated feedback"""
        
        # Create training dataset from feedback
        train_data = create_training_set_from_feedback(self.new_data_buffer)
        
        # Fine-tune model
        self.model.train(
            data=train_data,
            epochs=10,
            lr0=0.0001,  # Low learning rate for fine-tuning
            resume=True,
        )
        
        # Clear buffer
        self.new_data_buffer = []
        
        # Save updated model
        self.model.save("models/continuously_trained.pt")
```

## System Integration & Runtime

### Service Architecture

#### Single Command Startup (`./run_app.sh`)
```bash
#!/bin/bash
# Start all services concurrently

# Start FastAPI server (port 8000)
python -m uvicorn server.main:app --host 0.0.0.0 --port 8000 --reload &

# Start Streamlit frontend (port 8501)
streamlit run frontend/app.py --server.port 8501 &

# Start Flask labeller (port 5000)
python labeller/app.py --data labeller/nestvision &
```

#### Health Checks & Monitoring
```bash
# Health endpoints
curl http://localhost:8000/health    # FastAPI
curl http://localhost:8501/health    # Streamlit (if implemented)
curl http://localhost:5000/health    # Flask (if implemented)
```

### API Endpoints

#### FastAPI Backend (`/server/main.py`)

**Core Endpoints**:
- `GET /` - API documentation
- `GET /health` - Health check
- `GET /schema` - Database schema
- `POST /ask` - Natural language to SQL query
- `POST /ask/stream` - Streaming SQL query response
- `POST /cv/inference` - Computer vision inference
- `GET /cv/examples` - Example images for testing
- `POST /cv/correction/upload` - Upload for annotation correction

**Request/Response Models**:
```python
class QuestionRequest(BaseModel):
    question: str
    model: Optional[str] = None
    conversation_history: Optional[List[Dict[str, str]]] = None

class QueryResponse(BaseModel):
    sql_query: str
    results: Optional[List[Dict[str, Any]]]
    results_count: int
    answer: str
    error: Optional[str] = None
    show_chart: bool = False
    chart_type: Optional[str] = None
    show_map: bool = False

class CVInferenceResponse(BaseModel):
    bird_count: int
    detections: List[Dict[str, Any]]
    annotated_image_base64: str
    message: str
    inference_time: float
```

### Data Flow Architecture

#### Text-to-SQL Pipeline
1. **User Input** → Streamlit frontend
2. **API Call** → FastAPI `/ask` endpoint
3. **LLM Processing** → OpenRouter API (Claude)
4. **SQL Generation** → LLM converts natural language to SQL
5. **Query Execution** → SQLite database
6. **Result Processing** → LLM generates natural language answer
7. **Visualization** → Frontend renders charts/maps
8. **Response** → User sees answer + visualizations

#### Computer Vision Pipeline
1. **Image Upload** → Streamlit frontend
2. **Preprocessing** → Image validation and format conversion
3. **Inference Mode Selection**:
   - Fast mode: Downsampling for large images
   - SAHI mode: Intelligent slicing for accuracy
4. **Model Inference** → ONNX Runtime with YOLO model
5. **Post-processing** → NMS, coordinate transformation
6. **Annotation** → Draw bounding boxes on image
7. **Response** → Bird count, detections, annotated image

### Configuration Management

#### Environment Variables (`.env`)
```bash
OPENROUTER_API_KEY=your-key-here
DB_PATH=data/bird_data_complete.db
DB_TYPE=sqlite
API_BASE_URL=http://localhost:8000
MODEL_NAME=anthropic/claude-sonnet-4.5
```

#### Centralized Configuration
- Model selection controlled in one place (`.env`)
- Database path configurable
- API endpoints parameterized
- Environment-specific settings

### Performance Optimizations

#### Database Performance
- **Indexes**: Strategic indexes on frequently queried columns
- **Connection Pooling**: SQLite handles concurrent reads well
- **Query Optimization**: Efficient SQL generated by LLM
- **Caching**: Potential for result caching (Redis optional)

#### Computer Vision Performance
- **ONNX Runtime**: Optimized inference engine
- **Model Quantization**: FP32/FP16 options
- **Batch Processing**: Multiple image handling
- **GPU Acceleration**: CUDA support when available
- **Memory Management**: Image caching and cleanup

#### Frontend Performance
- **Lazy Loading**: Components loaded on demand
- **State Management**: Efficient session state handling
- **API Optimization**: Streaming responses for large data
- **Caching**: Browser caching for static assets

### Error Handling & Resilience

#### Backend Error Handling
```python
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail}
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error"}
    )
```

#### Database Resilience
- **Transaction Management**: ACID compliance
- **Backup Strategy**: File-based backup
- **Data Validation**: Input sanitization
- **Recovery**: Rebuild from CSV sources

#### Service Resilience
- **Health Checks**: Automatic service monitoring
- **Graceful Shutdown**: Proper cleanup on exit
- **Logging**: Comprehensive error logging
- **Fallbacks**: Alternative inference modes

## Future Enhancements

### Scalability Improvements
1. **Database**: PostgreSQL migration for concurrent writes
2. **Caching**: Redis for query result caching
3. **Load Balancing**: Multiple FastAPI instances
4. **CDN**: Static asset distribution

### Advanced Features
1. **Real-time Processing**: WebSocket support for live inference
2. **Batch Processing**: Queue system for large datasets
3. **Model Serving**: TensorFlow Serving or Triton
4. **API Rate Limiting**: Request throttling and quotas

### Monitoring & Observability
1. **Metrics**: Prometheus metrics collection
2. **Tracing**: Distributed tracing with Jaeger
3. **Logging**: Structured logging with ELK stack
4. **Alerting**: Automated alerts for service issues

### Security Enhancements
1. **Authentication**: User authentication and authorization
2. **API Keys**: Secure API key management
3. **Input Validation**: Comprehensive input sanitization
4. **HTTPS**: SSL/TLS encryption

This comprehensive technical overview provides the foundation for understanding, maintaining, and extending the NestScope platform for avian monitoring and analysis.</content>
<parameter name="filePath">/home/olise/Projects/nexus/NESTSCOPE_TECHNICAL_DEEP_DIVE.md