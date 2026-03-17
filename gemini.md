# gemini.md

This file provides guidance to Gemini CLI when working with code in this repository.

## 🎓 Educational Project Notice

**IMPORTANT: This is a learning-focused project.** The user is using NestScope as a hands-on opportunity to understand software engineering, AI/ML, and full-stack development.

### Gemini's Educational Responsibilities

When working on this project, Gemini MUST:

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
I'm going to add a new admin endpoint for bulk species updates. Here's what we need to do:

1. **Create new API endpoint**: POST /db/species/bulk_update that accepts species data
2. **Add authentication check**: Ensure only admins can access this endpoint
3. **Update database with change tracking**: Log all changes for audit trail

Let me explain each part:

### 1. API Endpoint
This endpoint will [explanation]. The flow is:
Admin → API → Validation → Database → Change Log → Response

[Show code for just this part with inline comments]

### 2. Authentication
We'll use the existing auth middleware to verify admin access:
[code example]

### 3. Change Tracking
Every update will be logged using db_change_tracker.py:
[Show tracking code]

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

**NestScope** is an AI-powered Gulf Coast avian monitoring platform focused on admin and expert tools:
- **Nestperts** - Expert annotation platform for species training and identification
- **NestDB** - Database administration with full read/write access
- **Flood Intelligence** - NOAA flood data integration and risk analysis
- **Coastal Tools** - Coastal data processing and analysis for researchers

Data covers 2010-2021 bird colony observations across Texas, Louisiana, Mississippi, Alabama, and Florida.

**Note**: Public-facing tools (NestChat and NestVision) have been removed. See `DELETION_SUMMARY.md` for details.

## Quick Start Commands

### Running the Application

**Backend API (Admin Endpoints):**
```bash
python -m uvicorn server.main:app --host 0.0.0.0 --port 8000 --reload
```

**Nestperts (Expert Annotation Platform):**
```bash
cd labeller
python app.py
# Or use the startup script:
./run_nestperts.sh
```

### Services

- **FastAPI backend**: http://localhost:8000 (health check at `/health`)
  - Admin endpoints for NestDB, flood intelligence, and coastal tools
  - Full database read/write access for authenticated users

- **Nestperts app**: http://localhost:5000
  - Expert annotation and species training
  - OAuth authentication required
  - Swift Detector for bounding box refinement and auto-detection

Logs are written to `logs/` directory:
- `logs/server.log` - FastAPI backend logs
- `logs/nestperts.log` - Flask Nestperts logs

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

### 1. Enhanced Metadata System

**Database Schema:**
- `data/database_metadata_enhanced.json` - Enhanced schema with:
  - Table relationships (foreign keys)
  - Column semantic types (count, coordinate, categorical, etc.)
  - Table purposes (primary_counts, photo_records, reference, metadata)
  - Query hints for common question patterns
  - Terminology guide clarifying "observations" vs "records"

**Key Distinction:**
- **tblColonyTotals2010-2021_MayJuneCombined**: Pre-aggregated BIRD and NEST COUNTS
- **tblSpeciesData2010/2011-2013/2015_2018_2021**: Individual PHOTO RECORDS

**Auto-Generated Metadata:**
The migration script automatically generates enhanced metadata:
```bash
cd data/
python migrate_access_to_sqlite.py --input <source.accdb> --output bird_data_complete.db
```

This creates `database_metadata_enhanced.json` with all relationships and semantic information.

### 2. NestDB (Admin SQL Generation)

**Purpose:** Database administration with full read/write access for authenticated users.

**Key Endpoint:** `POST /nestdb/generate_query`
- Generates SQL queries for admin interface
- **NO read-only restrictions** (unlike removed public endpoints)
- Returns SQL query for user review before execution
- Supports INSERT, UPDATE, DELETE, CREATE, ALTER, DROP
- Multi-statement support (semicolon-separated)

**Implementation:**
- Uses focused admin system prompt (no conversational fluff)
- Injects full database metadata context
- Returns `{sql_query, is_write_operation, model_used}`
- Frontend displays query for review before execution

**Security:**
- Requires authentication/authorization
- All queries reviewed by admin before execution
- Write operations clearly marked
- Change tracking via `db_change_tracker.py`
- Version control via `db_version.py`

### 3. Nestperts (Expert Species Training Platform)

**Purpose:** Expert platform for bird species identification and training data annotation using Swift AI detection.

**Flask-based UI** at port 5000 with expert workflow features:
- Multi-expert annotation workflow
- Species identification and classification
- Project state tracked in `project_state.json`
- YOLO26 format labels (normalized coordinates) with species metadata

**Swift AI Integration:**

Nestperts uses the Swift Detector (`swift.onnx`) for interactive and bulk detection:
- **Click-to-Detect (S)**: User clicks on bird → generates bounding box around nearest bird.
- **Auto-Detect All (A)**: Automatically finds and boxes all birds in the image.
- **Identify All**: Batch classifies all detected birds using the Swift Classifier.

**API Endpoints:**
- `POST /api/ai_detect_click` - Click-based detection
- `POST /api/detect_all_birds` - Full image bird detection
- `POST /api/classify_all_birds` - Batch species identification
- `POST /api/correction/upload` - Upload image with detections for correction

**Expert Training Workflow:**
1. Expert opens image in Nestperts.
2. Presses **A** to auto-detect all birds (labeled as "bird").
3. Uses **S** (AI Tool) to click and add any birds the detector missed.
4. Expert identifies species for each bird manually or using **Identify All**.
5. Species-labeled data saved for training classification models.

**Important Implementation Details:**
- `IMAGE_CACHE` reduces redundant image loading during detection.
- `INFERENCE_LOCK` prevents concurrent model inference (prevents GPU stalls).
- Intelligent duplicate prevention: Auto-detect skips birds that are already annotated.
- Detection uses `swift.onnx` (YOLOv8), Classification uses `classifier_swift.onnx`.

## Key Files

### Backend (FastAPI)
- `server/main.py` - FastAPI app with admin endpoints
- `server/db_version.py` - Database version control system
- `server/db_change_tracker.py` - Track database changes
- `server/flood_tools/` - Flood intelligence and NOAA integration
- `server/coastal_tools/` - Coastal data processing
- `server/services/` - Backend services (risk intelligence, db explorer, flood cache)
- `server/config.yaml` - Server configuration (version-controlled)

### Nestperts (Flask)
- `labeller/app.py` - Flask app with Swift AI integration and species training
- `labeller/auth.py` - OAuth authentication system
- `labeller/templates/` - HTML templates for expert UI
- `labeller/projects/` - Expert annotation projects
- `labeller/data/` - User and project data storage

### Models
- `models/swift.onnx` - Bird detection model (YOLOv8)
- `models/classifier_swift.onnx` - Bird species classification model (ONNX)

### Data
- `data/bird_data_complete.db` - SQLite database with observation data
- `data/database_metadata_enhanced.json` - Enhanced schema metadata

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
tail -f logs/nestperts.log
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

### Nestperts Authentication

OAuth setup for expert access:
```bash
cd labeller
python setup_auth.py  # Configure OAuth credentials
```

## Common Patterns

### Adding New Admin Endpoints

1. Define Pydantic request/response models
2. Add endpoint function with route decorator
3. Update root endpoint documentation at `/`
4. Test with FastAPI's interactive docs at `/docs`
5. Add authentication/authorization if needed

### Managing Database Changes

Use the database version control system:
```python
from server.db_version import DatabaseVersionControl

db_version = DatabaseVersionControl("data/bird_data_complete.db")
db_version.commit_version("Description of changes")
```

### Adding New Expert Projects

Create new project directories in `labeller/projects/`:
```bash
mkdir -p labeller/projects/new_project/{images,labels}
echo "species1\nspecies2" > labeller/projects/new_project/classes.txt
```

## Technology Stack

- **Backend**: FastAPI, SQLite, OpenRouter API (Gemini)
- **Admin Tools**: Flask (Nestperts), vanilla JavaScript
- **Segmentation**: Swift AI (Ultralytics) for annotation refinement
- **Database**: SQLite with version control and change tracking
- **Authentication**: OAuth 2.0 for expert access
- **Flood Data**: NOAA API integration
- **Deployment**: Uvicorn (backend), Flask dev server (Nestperts)

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
2. If that works, check the endpoint directly: curl http://localhost:8000/db/tables
3. Check the logs: tail -f logs/server.log
4. Look for error messages - what's the exact error?

This is the process I follow for any backend issue."
```

## Important Notes

- The OpenRouter API key is required for NestChat (text-to-SQL) functionality
- Nestperts works offline once models are downloaded
- Nestperts can run independently with `--data` pointing to any YOLO dataset
- All coordinates in labels are normalized (0-1 range) following YOLO format
- **Educational focus**: Always explain changes in terms a junior engineer would understand
