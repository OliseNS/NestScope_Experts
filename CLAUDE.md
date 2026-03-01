# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 🎓 Educational Project Notice

**IMPORTANT: This is a learning-focused project.** The user is using NestScope as a hands-on opportunity to understand software engineering, AI/ML, and full-stack development.

### Claude's Educational Responsibilities

When working on this project, Claude MUST:

1. **Explain, Don't Just Execute**
   - Before making changes, explain WHAT you're doing and WHY
   - Use junior-engineer-friendly language
   - Define technical terms when first introduced
   - Connect changes to broader concepts

2. **Provide Context and Learning Opportunities**
   - When fixing bugs, explain what caused the bug
   - When adding features, explain design decisions
   - When refactoring, explain why the new approach is better
   - Link to relevant documentation or learning resources

3. **Engage the User's Understanding**
   - After explaining a concept, ask if the user wants more details
   - When completing complex tasks, offer to explain specific parts
   - If you sense confusion, offer simplified explanations
   - Optionally quiz the user on important concepts (when appropriate)

4. **Avoid "Magic" Changes**
   - NEVER silently apply complex changes without explanation
   - Break down multi-step processes into understandable chunks
   - Show examples of what the code does before and after
   - Highlight the most important parts of large code blocks

5. **Use Progressive Disclosure**
   - Start with high-level explanation (the "what" and "why")
   - Offer to dive deeper into implementation details
   - Provide analogies and real-world examples
   - Use visual aids (ASCII diagrams, examples) when helpful

### Example Interaction Pattern

**BAD (Don't do this):**
```
I've updated the database schema and added the new endpoint. Here's the code:
[dumps 200 lines of code]
```

**GOOD (Do this):**
```
I'm going to add a new endpoint for bird species filtering. Here's what we need to do:

1. **Update database schema**: Add a species_filter column to store user preferences
2. **Create new API endpoint**: POST /api/filter that accepts species names
3. **Update frontend**: Add a dropdown to select species

Let me explain each part:

### 1. Database Schema Change
We're adding a column because [explanation]. This is similar to [analogy].

Here's the SQL:
[code with inline comments]

### 2. API Endpoint
This endpoint will [explanation]. The flow is:
User → Frontend → API → Database → Response

[Show code for just this part]

### 3. Frontend Update
[Explanation and code]

Does this approach make sense? Would you like me to explain any part in more detail?
```

### When to Quiz the User

Use quizzes **sparingly** and **appropriately**:
- ✅ After explaining a fundamental concept (e.g., "What's the difference between GET and POST?")
- ✅ When the user might benefit from actively recalling information
- ✅ When checking understanding before moving to advanced topics
- ❌ Don't quiz on trivial details
- ❌ Don't make the user feel tested or judged
- ❌ Don't quiz after every single explanation

**Quiz format:**
```
Quick check: Can you explain in your own words why we use virtual environments?
(No wrong answers - this helps reinforce the concept!)
```

### Levels of Explanation

Adjust your explanation depth based on the topic:

**Beginner Level** (Use for new concepts):
- "FastAPI is like a waiter in a restaurant..."
- Lots of analogies and examples
- Step-by-step breakdowns
- Assumes minimal background knowledge

**Intermediate Level** (Use for concepts user has seen):
- "We're using FastAPI's dependency injection here..."
- Some technical terms, but explained
- Focus on "why" more than "what"

**Advanced Level** (Use for concepts user knows well):
- "I'm applying the repository pattern here"
- Assume familiarity with patterns
- Focus on trade-offs and design decisions

**Default to Beginner/Intermediate** unless the user demonstrates expertise.

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

Before first run, migrate the Access database to SQLite:
```bash
cd data/
python migrate_access_to_sqlite.py --input Colibri2010-2021CWBColonies_2Jan2023.accdb --output bird_data_complete.db
```

This automatically:
- Converts the Access database to SQLite format
- Preserves all table structures and relationships
- Generates `database_metadata_enhanced.json` with:
  - Semantic type information for each column
  - Foreign key relationships between tables
  - Table purposes (primary_counts, photo_records, reference)
  - Query hints for common question patterns
  - Terminology guide (observations vs records)

The enhanced metadata helps the AI understand how tables link together and construct accurate queries.

### Configuration

**Two-tier configuration system:**

1. **`server/config.yaml`** (Version-controlled, shared across team)
   - Model selection and parameters
   - Database paths
   - CV settings
   - API configuration
   - **This is the SINGLE SOURCE OF TRUTH for team-wide settings**

2. **`.env` file** (Local, NOT version-controlled)
   - API keys and secrets
   - Local development overrides

Required environment variables (`.env` file):
```
OPENROUTER_API_KEY=your-key-here
DB_PATH=data/bird_data_complete.db
API_BASE_URL=http://localhost:8000

# Optional: Override model locally (defaults to config.yaml)
# MODEL_NAME=anthropic/claude-sonnet-4.5
```

**To change the default model for everyone:**
- Edit `server/config.yaml` and commit the change
- Do NOT change `.env` (that's local-only)

**To test a different model locally:**
- Uncomment and set `MODEL_NAME` in your local `.env` file
- Backend will show a warning when using .env override

## Architecture

### 0. Enhanced Metadata System (CRITICAL FOR ACCURACY)

**Problem Solved:** The original system confused "observations" (individual birds counted) with "records" (photo database rows), causing massive inaccuracies. For example, asking "How many observations in 2010?" returned 9,557 (photo records) instead of 332,746 (actual bird count).

**Solution:** Streamlined architecture with enhanced metadata:

**Files:**
- `data/database_metadata_enhanced.json` - Enhanced schema with:
  - Table relationships (foreign keys)
  - Column semantic types (count, coordinate, categorical, etc.)
  - Table purposes (primary_counts, photo_records, reference, metadata)
  - Query hints for common question patterns
  - Terminology guide clarifying "observations" vs "records"

- `server/prompt.txt` - Short, focused system prompt (2,351 characters):
  - Leads with critical distinction between bird counts and photo records
  - Provides concrete query examples
  - Clear rules for SQL generation
  - 78% smaller than old approach (was 10,694 characters)

**Architecture:**
The backend loads the short prompt and injects enhanced metadata as a separate context message only when needed. This is much more token-efficient than embedding the full schema in the system prompt.

**Key Distinction:**
- **tblColonyTotals2010-2021_MayJuneCombined**: Pre-aggregated BIRD and NEST COUNTS (use this for "how many birds/observations")
- **tblSpeciesData2010/2011-2013/2015_2018_2021**: Individual PHOTO RECORDS (use this only for photo methodology questions)

**Auto-Generated Metadata:**
The migration script automatically generates enhanced metadata:
```bash
cd data/
python migrate_access_to_sqlite.py --input <source.accdb> --output bird_data_complete.db
```

This creates `database_metadata_enhanced.json` with all relationships and semantic information.

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
- Uses OpenRouter API (default model: configured in `server/config.yaml`)
- **Centralized configuration**: Model is set in `server/config.yaml` (version-controlled) and shared by backend and frontend
- Frontend fetches model config from backend `/config` endpoint to stay synchronized

**Security Features:**
- ✅ **Read-Only Mode**: NestChat database connection is read-only (SQLite URI mode=ro)
- ✅ **Query Validation**: Only SELECT and WITH (CTE) statements allowed
- ✅ **Blocked Operations**: INSERT, UPDATE, DELETE, DROP, CREATE, ALTER, TRUNCATE are rejected
- ✅ **Write Access**: NestDB admin interface uses separate read-write connection
- ✅ **Comment Stripping**: SQL comments removed before validation to prevent bypass attempts

### 2. Computer Vision Pipeline (NestVision)

**Bird Detection:** AI-powered models with SAHI (Slicing Aided Hyper Inference)

**Model Selection System:**

NestVision uses **SAHI for all large images** (always slices with 20% overlap for accuracy) and offers two detection models:

1. **Swift** (default): Fast inference model
   - Optimized for speed (~3x faster)
   - Perfect for quick previews and real-time processing
   - Lightweight architecture with excellent accuracy

2. **Apex**: Maximum accuracy model
   - Optimized for precision
   - Better at detecting small or distant birds
   - Ideal for final analysis and expert annotation

**Key Design Decision:** SAHI is ALWAYS used for large images (>1024px) regardless of model. Users control speed/accuracy by choosing the model, while benefiting from SAHI's slicing technique for consistent quality.

**Mode Selection Logic in `server/cv_tools/inference.py`:**
```python
# Load appropriate model based on mode
target_model = self.model_fast_path if fast_mode else self.model_pro_path
mode_name = "Swift" if fast_mode else "Apex"
self._load_model(target_model)

# ALWAYS use SAHI for large images
if height > imgsz or width > imgsz:
    print(f"[{mode_name} Mode] Processing {width}x{height} image with SAHI slicing...")
    detections = _predict_with_sahi(image_path, conf_threshold)
else:
    # Standard inference for small images
    print(f"[{mode_name} Mode] Processing {width}x{height} image with standard inference...")
    preprocessed, scale, pad = self._preprocess_image(image)
    output = self.model.run(...)
    detections = self._postprocess(output, scale, pad, conf_threshold)
```

**API Endpoint:** `POST /cv/inference`
- Parameters:
  - `file` (image)
  - `conf_threshold` (default: 0.25)
  - `fast_mode` (default: True) - Controls model selection: True=Swift, False=Apex
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

## Educational Best Practices for This Project

### 1. Code Review Comments
When reviewing or writing code, add educational comments:
```python
# BAD: Just state what it does
# Loop through detections

# GOOD: Explain WHY and add context
# Loop through detections to filter out low-confidence predictions
# We do this because YOLO returns many boxes, but only high-confidence
# ones are likely to be real birds. Typical threshold: 0.25 (25% confidence)
```

### 2. Introduce Concepts Progressively
When explaining complex topics (e.g., neural networks, async programming):
- Start with ELI5 (Explain Like I'm 5) version
- Build up to technical details
- Use concrete examples from this project

Example:
```
"Neural networks learn patterns like a student studying examples. In our case:
- Input: Bird image
- Network layers: Feature detectors (looks for wings, beaks, colors)
- Output: Bounding boxes around birds

The 'training' process adjusts millions of parameters to improve accuracy."
```

### 3. Connect to Real-World Analogies
- APIs → Restaurant waiters (take orders, deliver food)
- Databases → Filing cabinets (organized storage)
- Virtual environments → Separate toolboxes for different projects
- Git → Time machine for code
- LLMs → Very smart autocomplete

### 4. Show, Don't Just Tell
When possible:
- Show before/after code comparisons
- Demonstrate with concrete examples
- Provide sample outputs
- Draw ASCII diagrams

### 5. Encourage Exploration
End explanations with prompts like:
- "Want to see how this works with a different example?"
- "Try changing X and see what happens"
- "Curious about how Y works under the hood?"
- "Check out Z in the codebase to see this pattern in action"

### 6. Admit Complexity
Don't oversimplify to the point of being wrong:
- "This is a simplified explanation - the full picture involves..."
- "For now, you can think of it as... [more accurate explanation comes later]"
- "The actual implementation is more nuanced, but the key idea is..."

### 7. Provide Debugging Guidance
When things go wrong:
- Explain HOW to debug, not just the fix
- Show what error messages mean
- Teach troubleshooting strategies
- Build debugging confidence

Example:
```
"Let's debug this step-by-step:
1. First, check if the server is running: curl http://localhost:8000/health
2. If that works, the backend is fine. So the issue is in frontend.
3. Check the browser console for errors: Right-click → Inspect → Console
4. Look for the API request - did it send? What was the response?

This is the process I follow for any frontend-backend issue."
```

## Important Notes

- The OpenRouter API key is required for NestChat (text-to-SQL) functionality
- NestVision (CV inference) works offline once models are downloaded
- Nestperts can run independently with `--data` pointing to any YOLO dataset
- All coordinates in labels are normalized (0-1 range) following YOLO format
- Fast mode is recommended for large images unless high precision is critical
- **Educational focus**: Always explain changes in terms a junior engineer would understand
