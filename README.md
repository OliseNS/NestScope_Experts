# NestScope

**AI-Powered Gulf Coast Avian Monitoring Platform**

NestScope combines natural language database queries with computer vision bird detection to analyze Gulf Coast colonial waterbird data from 2010-2021.

## What is NestScope?

NestScope is a learning project that demonstrates how to build a complete AI-powered application from scratch. It combines:
- **Natural language processing** (talk to databases in plain English)
- **Computer vision** (detect birds in images)
- **Web development** (interactive frontend)
- **API design** (RESTful backend)
- **Machine learning** (train custom models)

This is a **hands-on learning opportunity** - explore the code, ask questions, and understand how everything connects!

## Repository

- **GitHub:** [https://github.com/OliseNS/nexus_project](https://github.com/OliseNS/nexus_project)
- **Clone:** `git clone https://github.com/OliseNS/nexus_project.git` then `cd nexus_project`

## Documentation index

| Document | Contents |
|----------|----------|
| **README.md** (this file) | Overview, setup, architecture, model notes |
| **[DOCKER.md](DOCKER.md)** | Docker Compose, volumes, TLS, operations |
| **[labeller/README.md](labeller/README.md)** | Nestperts (port 5000), Google OAuth, local auth SQLite |
| **[server/README.md](server/README.md)** | FastAPI server layout and modules |
| **[QUICKSTART.md](QUICKSTART.md)** | LuckyCharm + RunPod workflow |
| **[docs/README.md](docs/README.md)** | Index of files in `docs/` |
| **[docs/VISION_MODELS.md](docs/VISION_MODELS.md)** | Deploying vision models (ONNX, Swift, Docker volumes, GPU) |
| **[docs/gemini.md](docs/gemini.md)** | Notes for Gemini CLI usage |

## Features

### 💬 NestChat - Talk to Your Data
Ask questions in natural language:
- "What colonies had the most Brown Pelicans in 2015?"
- "Show me observation trends over time"
- "Which states have the highest bird diversity?"

**How it works:**
1. You type a question (via any client of the API, e.g. a Streamlit app or custom UI)
2. The configured LLM (via OpenRouter) generates SQL from the schema
3. The query runs on the SQLite database
4. The LLM turns results into a natural language answer
5. The API can return visualization hints for charts and maps

### 🦅 NestVision - AI Bird Detection
Upload images and count birds automatically:
- **Fast Mode**: Quick detection for previews
- **SAHI Mode**: Accurate detection for small/distant birds
- **Bounding boxes**: Visual confirmation of detections
- **Expert training**: Send images to Nestperts for labeling

**How it works:**
1. Upload bird image
2. YOLOv8 model detects birds
3. Bounding boxes drawn on image
4. Bird count and confidence scores returned

### 👨‍🔬 Nestperts - Expert Annotation Platform
Label bird images for training data:
- **Swift AI segmentation**: Click birds to generate boxes
- **Species labeling**: Assign species to each detection
- **Multi-expert workflow**: Track who labeled what
- **YOLO format export**: Ready for model training

### 📊 Data Coverage
- **Years**: 2010-2021
- **States**: Texas, Louisiana, Mississippi, Alabama, Florida
- **Species**: 20+ coastal waterbird species
- **Observations**: 100,000+ data points from colony surveys

### 🛰️ Edge Detection - Jetson Nano Deployment
Deploy bird detection to the field with NVIDIA Jetson Nano:
- **On-board AI inference**: YOLO runs locally on Jetson GPU — no cloud, no internet
- **Continuous aerial survey mode**: Camera captures every N seconds, simulating helicopter flyover
- **Real-time transmission**: Detection results sent to NestScope server over local network
- **Offline buffering**: Results saved locally when server is unreachable, auto-synced when reconnected
- **Natural language querying**: Ask NestChat "How many birds in the last scan?" and get live field data

**How it works:**
1. Jetson Nano captures image (camera or file)
2. YOLO model detects birds on-device (GPU accelerated)
3. Results (count, bounding boxes) sent via HTTP to laptop server
4. Server saves to `edge_scans` table in SQLite
5. NestChat can immediately query: "What did the Jetson detect?"

**The deployment story:**
> In production, the Jetson Nano is mounted on a helicopter. As it flies over bird colonies,
> the Jetson automatically captures aerial images and runs NestVision on-board. Results are
> transmitted in real-time back to NestScope where scientists query the data instantly through NestChat.

**Usage on Jetson:**
```bash
# Single image detection
python3 jetson_detect.py --image bird_photo.jpg

# Continuous aerial survey mode (captures every 5 seconds)
python3 jetson_detect.py --camera-loop

# Custom interval
python3 jetson_detect.py --camera-loop --interval 3

# Send buffered offline results
python3 jetson_detect.py --flush
```

## Quick Start

### Prerequisites

Before starting, make sure you have:
- **Python 3.8 or newer** (check with `python --version`)
- **OpenRouter API key** (sign up at https://openrouter.ai/)
- **10GB free disk space** (for models and data)
- **Basic terminal knowledge** (how to run commands)

### Step-by-Step Installation

#### 1. Clone the Repository
```bash
git clone https://github.com/OliseNS/nexus_project.git
cd nexus_project
```

**What this does:** Downloads the project code to your computer. The default folder name is `nexus_project` (rename if you prefer).

#### 2. Create a Virtual Environment
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

**What is a virtual environment?** An isolated Python installation for this project. Keeps dependencies separate from other projects. You'll see `(.venv)` in your terminal prompt when activated.

**Important:** Always activate the virtual environment before running commands!

#### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

**What this does:** Installs all Python libraries needed (FastAPI, Streamlit, PyTorch, etc.). Takes 5-10 minutes.

**Troubleshooting:**
- If you see "permission denied", don't use `sudo` - check your virtual environment is activated
- If installation fails, try upgrading pip: `pip install --upgrade pip`

#### 4. Set Up Environment Variables
```bash
cp .env.example .env
nano .env  # Or use any text editor
```

**Edit .env and add:**
```env
OPENROUTER_API_KEY=your_api_key_here
DB_PATH=data/bird_data_complete.db
DB_TYPE=sqlite
API_BASE_URL=http://localhost:8000
MODEL_NAME=anthropic/claude-sonnet-4.5
```

**What are environment variables?** Secure way to store secrets (API keys) and configuration without hardcoding them in code.

#### Nestperts (port 5000) — Google sign-in

Expert tools use **Google OAuth** and a **local SQLite auth database** (default `data/user_auth.db`), not Turso.

1. In `.env`, set `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, and `SECRET_KEY` (see `labeller/README.md` for the Google Cloud redirect URI).
2. From the repo root, seed your administrator (creates the auth DB and whitelist):

   ```bash
   python seed_root_admin.py
   ```

   (You will be prompted for the email; or pass it: `python seed_root_admin.py you@example.com`.)

3. Start Nestperts (or `./run_app.sh`) and sign in with that Google account.

Optional: `python labeller/setup_auth.py` for an interactive wizard. Migrating old Turso data: `python scripts/migrate_auth_from_turso.py` (requires a one-time `pip install libsql-client`).

#### 5. Bird observation database

The API and NestDB expect a SQLite file at **`DB_PATH`** (default **`data/bird_data_complete.db`**). How you create it depends on your data pipeline (CSV import, migration from another environment, or restoring a backup). Ensure that path exists and is readable before starting the stack; `./run_app.sh` and the API `/health` check both assume the database is present.

If your tree includes import or ETL scripts under `scripts/`, use those according to their docstrings.

### Running the Application

#### Option A: Run All Services at Once (Recommended)
```bash
./run_app.sh
```

This starts:
- **Backend** (FastAPI) on port 8000
- **Nestperts** (Flask) on port 5000

Logs are saved to `logs/` directory.

**To stop:** Press `Ctrl+C` in the terminal.

#### Docker (servers in containers)

Use this for repeatable deployments or hosting behind a reverse proxy.

```bash
# Typical: bind-mount your ./data and ./labeller/projects from the host
docker compose -f docker-compose.yml -f docker-compose.host-mounts.yml up -d --build
```

- API: `http://localhost:8000/docs` — Nestperts: `http://localhost:5000`  
- Full checklist (TLS, OAuth redirect URIs, backups): **`DOCKER.md`**

#### Option B: Run services individually

**Terminal 1 — FastAPI**
```bash
python -m uvicorn server.main:app --host 0.0.0.0 --port 8000 --reload
```

**Terminal 2 — Nestperts**
```bash
cd labeller && python app.py
```

Use **when** you want separate terminals/logs or only one service.

**Optional Streamlit UI:** This repository’s main `requirements.txt` includes Streamlit for teams that maintain a separate frontend. If you have a `frontend/` app in your fork, run it with `streamlit run frontend/app.py --server.port 8501`.

### Access the application

| Service | URL (local defaults) |
|---------|----------------------|
| **API docs (Swagger)** | http://localhost:8000/docs |
| **Nestperts** | http://localhost:5000 |

### Verification

```bash
curl -s http://localhost:8000/health
curl -s http://localhost:5000/health
```

Optional LLM eval tooling (`deepeval`) is listed in `requirements.txt`; see package docs if you use the evaluation endpoints.

### First-time user guide

1. **API**: Open http://localhost:8000/docs and try a documented endpoint (e.g. health, schema) once the bird database is in place.
2. **Nestperts**: Open http://localhost:5000, complete Google OAuth after seeding the root admin (`seed_root_admin.py`).
3. **Custom UI**: Point any HTTP client at the API using `API_BASE_URL` (see `.env.example`).

## Project structure

Layout of [nexus_project](https://github.com/OliseNS/nexus_project) (high level; your clone may omit optional dirs):

```
nexus_project/
├── seed_root_admin.py           # Nestperts auth DB + root admin (see labeller/README.md)
├── Dockerfile                   # Container image (API + Nestperts)
├── docker-compose.yml           # Default stack (named volumes)
├── docker-compose.host-mounts.yml
├── DOCKER.md                    # Docker deployment
├── deploy/nginx.conf.example    # Example TLS reverse proxy
├── run_app.sh                   # Start FastAPI + Nestperts locally
├── requirements.txt
├── server/                      # FastAPI app (NestChat / NestDB / CV APIs)
├── labeller/                    # Nestperts (Flask, port 5000)
├── scripts/                     # Utilities (e.g. jetson_detect.py, migrate_auth_from_turso.py)
├── docs/                        # Extra docs (gemini.md, VISION_MODELS.md, …)
├── data/                        # SQLite data (bird DB, caches; not all in git)
├── models/                      # ONNX / weights (often gitignored; see .gitignore)
├── luckycharm/                  # Local visualization client (see QUICKSTART.md)
├── logo/                        # Brand assets
└── README.md
```

### What each area is for

| Path | Purpose |
|------|---------|
| **server/** | FastAPI backend — `server/README.md` |
| **labeller/** | Nestperts expert UI — `labeller/README.md` |
| **scripts/** | Jetson edge script, auth migration, data helpers |
| **docs/** | Additional markdown (e.g. Gemini CLI notes) |
| **data/** | `bird_data_complete.db`, `user_auth.db`, caches |
| **models/** | Detection / segmentation weights when present locally |

## How it fits together

```
┌─────────────────────────────────────────────────────────────┐
│  Clients (browser, Streamlit, scripts, internal tools)       │
└────────────────────────┬────────────────────────────────────┘
                         │  HTTP / JSON
                         ↓
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI (server/)                           │
│  • Text-to-SQL / Q&A, DB admin, CV inference, flood tools    │
│  • SQLite bird database + ONNX models (when present)         │
│  • LLMs via OpenRouter (see MODEL_NAME / config.yaml)        │
└────────────────────────┬────────────────────────────────────┘
                         │  shared SQLite auth (user_auth.db)
                         ↓
┌─────────────────────────────────────────────────────────────┐
│                    Nestperts (labeller/)                     │
│  • Expert annotation, NestDB UI, flood dashboards            │
│  • Google OAuth + local SQLite whitelist                     │
└─────────────────────────────────────────────────────────────┘
```

Optional: **VisionTrain/** (training), **Jetson** (`scripts/jetson_detect.py`), **Docker** (`DOCKER.md`).

### Edge Detection Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│              JETSON NANO (Edge Device)                       │
│                                                             │
│  Camera ──→ YOLO Model ──→ Bird Detections                 │
│              (swift.pt)     (count + bboxes)                │
│                                                             │
│  If server reachable:     If server unreachable:            │
│    POST /edge/scan ──→      Save to offline_buffer.json     │
│                              (auto-sync later)              │
└──────────────────┬──────────────────────────────────────────┘
                   │ HTTP POST (JSON)
                   │ WiFi / Local Network
                   ▼
┌─────────────────────────────────────────────────────────────┐
│                    BACKEND (FastAPI)                         │
│                                                             │
│  /edge/scan endpoint ──→ SQLite (edge_scans table)         │
│                                                             │
│  NestChat: "How many birds in the last scan?"              │
│     └──→ SELECT bird_count FROM edge_scans                 │
│           ORDER BY id DESC LIMIT 1                          │
│     └──→ "The last scan detected 47 birds..."              │
└─────────────────────────────────────────────────────────────┘
```

### Example flow: “What colonies are in Texas?”

1. A client sends the question to the FastAPI **ask** / query pipeline (see `/docs`).
2. The server sends the schema + question to the **configured LLM** (OpenRouter).
3. The model returns **SQL**; the server runs it on **SQLite**.
4. The model (or a second pass) turns rows into a **natural language answer** and optional **visualization hints** (e.g. `[SHOW_MAP: true]`).
5. The client renders text/charts/maps as implemented in that client.

### Example flow: “Count birds in this image”

1. Client **POST**s image bytes to the **computer vision** endpoints (see `/docs`).
2. Server loads the **ONNX** (or configured) detector, runs inference, NMS, encoding.
3. Response JSON includes **counts, boxes,** and optional **annotated image** payload for the UI to show.

## Technology Stack Explained

### Backend Technologies

| Technology | What It Is | Why We Use It |
|------------|-----------|---------------|
| **FastAPI** | Python web framework | Fast, modern, auto-generated docs |
| **SQLite** | Embedded database | No server needed, perfect for local apps |
| **OpenRouter** | LLM API gateway | Access Claude without direct Anthropic account |
| **ONNX Runtime** | Inference engine | Fast model inference, cross-platform |
| **Pandas** | Data manipulation | Easy SQL result processing |

### Frontend Technologies

| Technology | What It Is | Why We Use It |
|------------|-----------|---------------|
| **Streamlit** | Python web framework | Build UIs with pure Python (no HTML/CSS/JS!) |
| **Plotly** | Charting library | Interactive charts (line, bar, scatter) |
| **Folium** | Mapping library | Geographic visualizations |
| **Requests** | HTTP library | Call backend API |
| **PIL/Pillow** | Image processing | Load, resize, display images |

### Computer Vision Technologies

| Technology | What It Is | Why We Use It |
|------------|-----------|---------------|
| **YOLOv8** | Object detection model | State-of-the-art, fast, accurate |
| **ONNX** | Model format | Deploy PyTorch models without PyTorch |
| **SAHI** | Slicing algorithm | Detect small objects in large images |
| **Swift AI** | Segmentation model | Interactive segmentation from points |
| **OpenCV** | Computer vision library | Image processing, drawing boxes |

### Training Technologies

| Technology | What It Is | Why We Use It |
|------------|-----------|---------------|
| **PyTorch** | Deep learning framework | Train neural networks |
| **Ultralytics** | YOLO implementation | Easy training API, well-documented |
| **CUDA** | GPU acceleration | Train 10-100x faster |

## Model Information

### Detection Model
- **File**: `models/seconditer.onnx`
- **Type**: YOLOv8-based ONNX
- **Input**: 1024x1024
- **Purpose**: Bird detection and counting

### Segmentation Model
- **File**: `models/mobile_sam.pt`
- **Type**: Swift AI (PyTorch)
- **Purpose**: Interactive segmentation in labeller

### Detection Model (Legacy)
- **File**: `models/best.pt`
- **Type**: PyTorch YOLO
- **Purpose**: Legacy detection model

## Key Innovations

### 1. Agentic Visualization Control

Most apps use **rule-based visualization** (rigid, breaks easily):
```python
# Traditional approach
if "over time" in question:
    show_line_chart()
elif "top" in question:
    show_bar_chart()
```

NestScope uses **agentic visualization** (intelligent, context-aware):
```python
# Agentic approach
answer = llm.generate_answer(question, results)
# LLM embeds: "[SHOW_CHART: bar]" in answer
viz_type = parse_directives(answer)
```

**Benefits:**
- LLM understands context and user intent
- Handles ambiguous cases intelligently
- No hardcoded rules to maintain
- Adapts to new question types automatically

### 2. Two-Stage LLM Pipeline

Instead of one big prompt, we split into two stages:
1. **SQL Generation**: Question → SQL query
2. **Answer Generation**: Results → Natural language answer

**Why?**
- **Separation of concerns**: Each stage has one job
- **Easier debugging**: See exactly where things fail
- **Better prompts**: Optimize each stage independently
- **Streaming friendly**: Can stream answer while query runs

### 3. SAHI for Small Object Detection

Standard YOLO struggles with small/distant birds. SAHI (Slicing Aided Hyper Inference) solves this:
- Slice large image into overlapping patches
- Run inference on each patch
- Merge detections with NMS

**Trade-off:** Slower but more accurate (use "Fast Mode" for speed).

## Learning Paths

### Path 1: I want a web UI on top of the API
**Goal:** Call NestScope from a browser app (Streamlit, React, or internal tools)

1. Open `http://localhost:8000/docs` and try **Authorize** + a few GET/POST flows.
2. Read `server/README.md` for module layout.
3. If your team maintains Streamlit in a **`frontend/`** tree (fork or submodule), run it per that README; otherwise scaffold a small client that posts to `/ask` (or your wrapped routes).
4. Set `API_BASE_URL` in `.env` to match how the browser reaches the API.

**Time:** 2–4 hours for a minimal client  
**Prerequisites:** Basic Python or JS, HTTP basics  
**Resources:** FastAPI docs, Streamlit docs (if using Streamlit)

### Path 2: I Want to Understand the Backend
**Goal:** Learn how APIs work and how to use LLMs

1. Read `server/README.md`
2. Look at `server/main.py` - API endpoints
3. Test endpoints in Swagger UI (http://localhost:8000/docs)
4. Study `server/prompt.txt` - LLM system prompt
5. Experiment: Add a new endpoint

**Time:** 3-5 hours
**Prerequisites:** Basic Python, understand HTTP
**Resources:** FastAPI tutorial, OpenRouter docs

### Path 3: I Want to Understand Computer Vision
**Goal:** Learn how object detection models work

1. Read `server/cv_tools/inference.py`
2. Understand YOLO architecture (watch YouTube video)
3. Run inference on test images
4. Read `labeller/README.md` - annotation tool
5. If **`VisionTrain/`** exists in your clone, read `VisionTrain/README.md` for the training pipeline.

**Time:** 5-8 hours
**Prerequisites:** Basic Python, linear algebra helpful
**Resources:** YOLO docs, PyTorch tutorials

### Path 4: I Want to Train My Own Model
**Goal:** Create a custom bird detection model

1. If present, read `VisionTrain/README.md` thoroughly.
2. Annotate images in Nestperts.
3. Prepare datasets with your team’s prep scripts (often under `VisionTrain/`).
4. Train and export to ONNX following Ultralytics / project docs.
5. Point `server` config at the new weights.

**Time:** 2-3 days (plus compute time)
**Prerequisites:** Python, ML basics, GPU access
**Resources:** Ultralytics docs, YOLO training guides

### Path 5: I Want to Build Something Similar
**Goal:** Apply these patterns to your own project

1. Study the architecture diagram
2. Understand the data flow examples
3. Pick one component to replicate (e.g., text-to-SQL)
4. Build it step-by-step with your own data
5. Reference NestScope code as needed

**Time:** 1-2 weeks
**Prerequisites:** All of the above
**Resources:** This entire codebase!

## Common Issues and Solutions

### "Module Not Found" Errors
**Problem:** Python can't find imported modules
**Solution:**
- Activate virtual environment: `source .venv/bin/activate`
- Install requirements: `pip install -r requirements.txt`
- Check you're in the right directory: `pwd` (should end with your clone name, e.g. `nexus_project`)

### "Connection Refused" to Backend
**Problem:** Frontend can't reach backend API
**Solution:**
- Check backend is running: `curl http://localhost:8000/health`
- Start backend: `python -m uvicorn server.main:app --port 8000`
- Check firewall isn't blocking port 8000

### "Database Locked" Error
**Problem:** Multiple processes accessing SQLite simultaneously
**Solution:**
- SQLite doesn't handle concurrent writes well
- Use one connection at a time
- For production, consider PostgreSQL

### Inference is Very Slow
**Problem:** Bird detection takes >10 seconds per image
**Solution:**
- Use Fast Mode (enabled by default)
- Reduce image size before uploading
- Check CPU usage (should use all cores)
- Consider GPU acceleration (requires CUDA setup)

### LLM Returns Irrelevant SQL
**Problem:** Generated SQL doesn't match question
**Solution:**
- Check `server/prompt.txt` - is schema accurate?
- Add example Q&A pairs for similar questions
- Verify OpenRouter API key is valid
- Try different LLM model

### Out of Memory During Training
**Problem:** GPU runs out of VRAM during model training
**Solution:**
- Reduce batch size (try 8, 4, or 2)
- Reduce image size (try 640 instead of 1024)
- Use smaller model (yolov8n instead of yolov8m)
- Close other GPU-using programs

## Development Tips

### Viewing Logs
```bash
# Backend logs
tail -f logs/server.log

# Frontend logs
tail -f logs/streamlit.log

# Nestperts logs
tail -f logs/nestperts.log
```

### Clearing Caches
```bash
# Streamlit cache
# Press 'C' in terminal running Streamlit

# Python cache
find . -type d -name "__pycache__" -exec rm -rf {} +
```

### Testing Individual Components
```bash
# Test database connection
python -c "import sqlite3; conn = sqlite3.connect('data/bird_data_complete.db'); print('Connected!')"

# Test OpenRouter API
curl https://openrouter.ai/api/v1/models -H "Authorization: Bearer $OPENROUTER_API_KEY"

# Test ONNX model loading
python -c "import onnxruntime; print('ONNX Runtime:', onnxruntime.__version__)"
```

## Project Roadmap

### Current Status
- ✅ Text-to-SQL with Gemini
- ✅ Bird detection with YOLOv8
- ✅ Annotation platform with Swift AI
- ✅ Training pipeline
- ✅ Comprehensive documentation

### Potential Enhancements
- [ ] Species classification model (not just detection)
- [ ] Real-time video inference
- [ ] Multi-user authentication
- [ ] Database editor with version control
- [ ] Export training data to COCO format
- [ ] Deploy to cloud (AWS, GCP, Azure)
- [ ] Mobile app (Flutter/React Native)

## Resources and Links

### Official Documentation
- **FastAPI**: https://fastapi.tiangolo.com/
- **Streamlit**: https://docs.streamlit.io/
- **YOLOv8**: https://docs.ultralytics.com/
- **ONNX**: https://onnxruntime.ai/docs/
- **OpenRouter**: https://openrouter.ai/docs

### Learning Resources
- **Python Tutorial**: https://docs.python.org/3/tutorial/
- **REST API Basics**: https://restfulapi.net/
- **SQL Tutorial**: https://www.w3schools.com/sql/
- **Computer Vision Course**: https://cs231n.github.io/
- **Deep Learning Book**: https://www.deeplearningbook.org/

### Community
- **GitHub Issues**: Report bugs and request features
- **Discussions**: Ask questions and share ideas
- **Contributing**: See CONTRIBUTING.md (if it exists)

## Acknowledgments

- **Gulf Coast bird data**: NOAA, USFWS, and state wildlife agencies
- **YOLOv8**: Ultralytics team
- **Swift AI**: ChaoningZhang et al.
- **Gemini**: Anthropic
- **Open source community**: All the amazing libraries we use!

## License

[Add your license here]

## Contact

For questions or feedback:
- Open an issue on GitHub
- Email: [your-email@example.com]
- Twitter: [@your-handle]

---

**Built with ❤️ for learning and conservation**
