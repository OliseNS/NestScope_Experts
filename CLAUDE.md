# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**NestScope** is an AI-powered Gulf Coast avian monitoring platform that combines:
- Natural language database queries (NestChat)
- Computer vision bird detection and counting (NestVision)
- Expert species training and annotation platform (Nestperts)

Data covers 2010-2021 bird colony observations across Texas, Louisiana, Mississippi, Alabama, and Florida.

## Quick Start Commands

### Running the Application

Start all services at once:
```bash
./run_app.sh
```

This launches three services:
- **FastAPI backend**: http://localhost:8000 (health check at `/health`)
- **Streamlit frontend**: http://localhost:8501
- **Nestperts app**: http://localhost:5000

Logs are written to `logs/` directory:
- `logs/server.log` - FastAPI backend logs
- `logs/streamlit.log` - Streamlit frontend logs
- `logs/nestperts.log` - Flask Nestperts logs

### Running Services Individually

**Backend API:**
```bash
python -m uvicorn server.main:app --host 0.0.0.0 --port 8000 --reload
```

**Frontend:**
```bash
streamlit run frontend/app.py --server.port 8501
```

**Nestperts:**
```bash
python labeller/app.py --data labeller/nestvision
```

### Database Setup

Before first run, initialize the SQLite database:
```bash
python scripts/data_management/import_all_to_sqlite.py
```

This imports CSV files from `CSV_Files/` into `data/bird_data_complete.db`.

### Environment Configuration

Required environment variables (`.env` file):
```
OPENROUTER_API_KEY=your-key-here
DB_PATH=data/bird_data_complete.db
DB_TYPE=sqlite
API_BASE_URL=http://localhost:8000
```

## Architecture

### 1. Text-to-SQL Pipeline (NestChat)

**Flow:** User question → LLM generates SQL → Execute query → LLM generates natural language answer

**Key Pattern: Agentic Visualization Control**

The backend LLM controls which visualizations to display by embedding directives in its responses. The frontend parses these directives and respects them instead of auto-detecting visualization types.

**Visualization Directives:**
- `[SHOW_CHART: line]` - Display line chart for time-series data
- `[SHOW_CHART: bar]` - Display bar chart for comparisons/rankings
- `[SHOW_MAP: true]` - Display geographic map with colony locations
- `[NO_VIZ]` - No visualization needed

The `parse_visualization_directives()` function in `server/main.py` extracts these directives and removes them from the displayed answer.

**Critical: Coordinate Inclusion Rules**

The system prompt (`server/prompt.txt`) enforces that SQL queries MUST include `Latitude` and `Longitude` columns whenever:
- Query returns colony names or locations
- Query uses GROUP BY with ColonyName
- Query performs aggregations on colony data
- User asks about geographic locations

This enables map visualizations. The prompt includes extensive examples of correct vs incorrect queries.

**Implementation Details:**
- `SQLChatbot` class in `server/main.py`
- Two answer generation modes: streaming (`/ask/stream`) and non-streaming (`/ask`)
- System prompt loaded from `server/prompt.txt`
- Uses OpenRouter API (default model: `anthropic/claude-sonnet-4.5`, configurable via `MODEL_NAME` in `.env`)
- **Centralized configuration**: Model is set in ONE place only (`.env` file) and used by both backend and frontend

### 2. Computer Vision Pipeline (NestVision)

**Bird Detection:** YOLOv8-based ONNX model (`models/seconditer.onnx`)

**Two Inference Modes:**

1. **Fast Mode** (default): Quick inference using downsampling for large images
   - Best for previews and real-time processing
   - Uses `_downsample_and_predict()` method
   - Much faster than SAHI for large images

2. **SAHI Mode**: Slicing Aided Hyper Inference with intelligent slicing
   - More accurate for detecting small objects
   - Uses 20% overlap between slices
   - NMS applied across all slices to merge detections
   - Uses `_predict_with_sahi()` method

**Mode Selection Logic in `server/cv_tools/inference.py`:**
```python
# Fast mode: downsample large images, standard inference for small
if fast_mode:
    if height > imgsz or width > imgsz:
        detections = _downsample_and_predict(image, conf_threshold)
    else:
        # Standard inference for small images

# SAHI mode: smart slicing for large images
else:
    if use_sliding_window and (height > imgsz or width > imgsz):
        detections = _predict_with_sahi(image_path, conf_threshold)
```

**API Endpoint:** `POST /cv/inference`
- Parameters: `file` (image), `conf_threshold` (default: 0.25), `fast_mode` (default: True)
- Returns: bird count, detections, base64 annotated image, inference time

**Annotation Style:**
- Bounding boxes use Claude orange color (#D97757 / BGR: (87, 119, 217))
- No confidence labels displayed (clean annotation)
- Boxes drawn with 3px thickness

### 3. Nestperts (Expert Species Training Platform)

**Purpose:** Expert platform for bird species identification and training data annotation using MobileSAM segmentation

**Flask-based UI** at port 5000 with expert workflow features:
- Multi-expert annotation workflow
- Species identification and classification
- Project state tracked in `project_state.json`
- YOLO format labels (normalized coordinates) with species metadata

**MobileSAM Integration:**

Nestperts uses MobileSAM (from Ultralytics) for interactive segmentation:
- Point-based segmentation: user clicks on bird → generates bounding box
- Two detection modes:
  - **Fast mode**: 720x720 resolution, no retina masks (optimized for speed)
  - **SAHI mode**: 1024x1024 resolution, retina masks enabled (better accuracy for small objects)

**API Endpoints:**
- `POST /api/sam_segment` - Point-based segmentation with click coordinates
- `GET /api/sam_status` - Model status and device info (GPU/CPU)
- `POST /api/correction/upload` - Upload image with detections for correction

**Expert Training Workflow:**
1. Expert runs inference on image in NestVision
2. Clicks "Train with Experts" button to send to Nestperts
3. Image uploaded to Nestperts via `/api/correction/upload`
4. Image saved to `labeller/nestvision/images/`
5. Initial detections saved as YOLO labels in `labeller/nestvision/labels/`
6. Expert refines bounding boxes using MobileSAM point clicks
7. Expert assigns species to each detected bird
8. Species-labeled data saved for training classification models

**Important Implementation Details:**
- `IMAGE_CACHE` reduces redundant image loading during segmentation
- `INFERENCE_LOCK` prevents concurrent model inference (prevents GPU stalls)
- Intelligent mask validation filters out masks that are too large (>30% of image) or too small (<50 pixels)
- Automatically adds 5% padding to bounding boxes for better coverage

## Key Files

### Backend (FastAPI)
- `server/main.py` - FastAPI app with all endpoints
- `server/prompt.txt` - System prompt for SQL generation (includes coordinate rules)
- `server/cv_tools/inference.py` - BirdDetector class with ONNX inference

### Frontend (Streamlit)
- `frontend/app.py` - Main landing page
- `frontend/pages/01_nest_chat.py` - NestChat (text-to-SQL interface)
- `frontend/pages/02_nest_vision.py` - NestVision (CV inference interface)
- `frontend/services/api_client.py` - Backend API communication
- `frontend/styles/` - UI theming and styles

### Nestperts (Flask)
- `labeller/app.py` - Flask app with MobileSAM integration and species training
- `labeller/templates/` - HTML templates for expert UI
- `labeller/nestvision/` - Dataset directory (images/, labels/, classes.txt, species data)

### Models
- `models/seconditer.onnx` - YOLOv8 bird detection model (1024x1024 input)
- `models/mobile_sam.pt` - MobileSAM segmentation model

### Data
- `data/bird_data_complete.db` - SQLite database with observation data
- `CSV_Files/` - Source CSV data files

## Model Training

Training pipeline located in `VisionTrain/` directory (separate from main application).

## Development Tips

### Debugging Backend Issues
```bash
# Check server health
curl http://localhost:8000/health

# View API documentation
open http://localhost:8000/docs

# Tail logs in real-time
tail -f logs/server.log
tail -f logs/streamlit.log
tail -f logs/nestperts.log
```

### Testing CV Inference

Example images available at `server/cv_tools/images/`. Get list via API:
```bash
curl http://localhost:8000/cv/examples
```

### Database Schema

View schema via API:
```bash
curl http://localhost:8000/schema
```

Key tables:
- `observations` - Raw observation data with all fields
- `colony_totals` - Aggregated data by colony (includes Latitude/Longitude)
- `species` - Species reference data

### Frontend State Management

Streamlit uses session state (`st.session_state`) for managing conversation history and UI state. State is page-specific and doesn't persist across page navigation.

## Common Patterns

### Adding New Endpoints to Backend

1. Define Pydantic request/response models
2. Add endpoint function with route decorator
3. Update root endpoint documentation at `/`
4. Test with FastAPI's interactive docs at `/docs`

### Modifying System Prompt

Edit `server/prompt.txt` - changes take effect on next query (no restart needed with `--reload`).

### Changing Visualization Logic

Modify visualization directives in the answer generation system prompt in `server/main.py` (search for "VISUALIZATION DIRECTIVES").

### Updating Bird Detection Model

Replace `models/seconditer.onnx` and update `MODEL_PATH` in `server/cv_tools/inference.py` if needed. Ensure input size matches `imgsz` parameter.

## Technology Stack

- **Backend**: FastAPI, SQLite, OpenRouter API (Claude), ONNX Runtime
- **Frontend**: Streamlit, Plotly (charts), Folium (maps)
- **Computer Vision**: Ultralytics YOLO (ONNX), SAHI (sliced inference)
- **Segmentation**: MobileSAM (Ultralytics)
- **Labelling**: Flask, vanilla JavaScript

## Important Notes

- The OpenRouter API key is required for NestChat (text-to-SQL) functionality
- NestVision (CV inference) works offline once models are downloaded
- Nestperts can run independently with `--data` pointing to any YOLO dataset
- All coordinates in labels are normalized (0-1 range) following YOLO format
- Fast mode is recommended for large images unless high precision is critical
