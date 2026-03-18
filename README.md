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

## Features

### 💬 NestChat - Talk to Your Data
Ask questions in natural language:
- "What colonies had the most Brown Pelicans in 2015?"
- "Show me observation trends over time"
- "Which states have the highest bird diversity?"

**How it works:**
1. You type a question
2. Gemini converts it to SQL
3. Query runs on SQLite database
4. Claude writes a natural language answer
5. Charts and maps appear automatically

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
git clone <repository-url>
cd nexus
```

**What this does:** Downloads the project code to your computer.

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

#### 5. Set Up the Database
```bash
python scripts/data_management/import_all_to_sqlite.py
```

**What this does:** Converts CSV files in `CSV_Files/` into a SQLite database. Creates `data/bird_data_complete.db` (about 50MB).

### Running the Application

#### Option A: Run All Services at Once (Recommended)
```bash
./run_app.sh
```

This starts:
- **Backend** (FastAPI) on port 8000
- **Frontend** (Streamlit) on port 8501
- **Nestperts** (Flask) on port 5000

Logs are saved to `logs/` directory.

**To stop:** Press `Ctrl+C` in the terminal.

#### Option B: Run Services Individually

**Terminal 1 - Backend:**
```bash
python -m uvicorn server.main:app --host 0.0.0.0 --port 8000 --reload
```

**Terminal 2 - Frontend:**
```bash
streamlit run frontend/app.py --server.port 8501
```

**Terminal 3 - Nestperts:**
```bash
python labeller/app.py --data labeller/nestvision
```

**When to use this?** When you want to see logs for each service separately, or only need one service running.

### Access the Application

Open your browser and visit:
- **Main App (Streamlit)**: http://localhost:8501
- **Backend API Docs**: http://localhost:8000/docs
- **Nestperts Labeller**: http://localhost:5000

### Verification Steps
 1. pip install deepeval (or add to requirements.txt and reinstall)
 2. Start server: python -m uvicorn server.main:app --reload
 3. Test endpoint: curl -X POST http://localhost:8000/eval/run
 4. Check status: curl http://localhost:8000/eval/status
 5. Get results: curl http://localhost:8000/eval/results
 6. Start frontend: streamlit run frontend/app.py
 7. Navigate to the new "Eval Dashboard" page and click "Run Evaluation"

### First-Time User Guide

1. **Try NestChat**: Go to "Nest Chat" page, ask "What colonies are in Texas?"
2. **Try NestVision**: Go to "Nest Vision" page, select an example image, click "Run Inference"
3. **Explore API Docs**: Visit http://localhost:8000/docs to see all endpoints
4. **Check System Status**: Go to "System Status" page to verify everything is running

## Project Structure

```
nexus/
├── frontend/                    # 🖥️ Streamlit web interface (what users see)
│   ├── app.py                  # Landing page
│   ├── pages/                  # Individual pages (Chat, Vision, Status, DB Editor)
│   ├── components/             # Reusable UI pieces (charts, maps, sidebar)
│   ├── services/               # Backend API communication
│   ├── utils/                  # Helper functions (data processing, image handling)
│   ├── styles/                 # Custom CSS and theming
│   └── README.md               # 📖 Frontend documentation
│
├── server/                      # ⚙️ FastAPI backend (the brain)
│   ├── main.py                 # API endpoints and core logic
│   ├── prompt.txt              # System prompt for SQL generation
│   ├── cv_tools/               # Computer vision inference (YOLO ONNX)
│   └── README.md               # 📖 Backend documentation
│
├── labeller/                    # 👨‍🔬 Nestperts annotation platform
│   ├── app.py                  # Flask web server with Swift AI
│   ├── templates/              # HTML templates for UI
│   ├── nestvision/             # YOLO dataset (images, labels, classes)
│   └── README.md               # 📖 Labeller documentation
│
├── VisionTrain/                 # 🏋️ Model training pipeline
│   ├── imgdata_prep/           # Dataset preparation scripts
│   ├── training_data/          # Organized YOLO dataset (train/val split)
│   ├── train_test_split.py     # Split data for training
│   └── README.md               # 📖 Training documentation
│
├── models/                      # 🤖 AI models
│   ├── seconditer.onnx         # Bird detection model (YOLO)
│   └── mobile_sam.pt           # Segmentation model (Swift AI)
│
├── data/                        # 📊 SQLite database
│   └── bird_data_complete.db   # All bird observation data (2010-2021)
│
├── CSV_Files/                   # 📁 Source data (imported to database)
│
├── scripts/                     # 🛠️ Utility scripts
│   ├── jetson_detect.py        # 🛰️ Jetson Nano edge detection script
│   ├── data_management/        # Database import/export
│   ├── analysis/               # Data analysis tools
│   └── deployment/             # Deployment helpers
│
├── docs/                        # 📚 Project documentation
│
├── logs/                        # 📝 Application logs
│   ├── server.log              # Backend logs
│   ├── streamlit.log           # Frontend logs
│   └── nestperts.log           # Labeller logs
│
├── .env                         # 🔐 Environment variables (API keys, config)
├── requirements.txt             # 📦 Python dependencies
├── run_app.sh                   # 🚀 Launch script (starts all services)
├── README.md                    # 📖 This file!
└── gemini.md                    # 🤖 Instructions for Gemini CLI

```

### What Each Folder Does

| Folder | Purpose | Start Here |
|--------|---------|------------|
| **frontend/** | User interface (Streamlit) | `frontend/README.md` |
| **server/** | Backend API (FastAPI) | `server/README.md` |
| **labeller/** | Expert annotation tool | `labeller/README.md` |
| **VisionTrain/** | Model training pipeline | `VisionTrain/README.md` |
| **models/** | Pre-trained AI models | No README (binary files) |
| **data/** | SQLite database | Query via NestChat or `/docs` endpoint |
| **scripts/** | One-off utilities | Check individual script docstrings |
| **scripts/jetson_detect.py** | Edge detection for Jetson Nano | Run with `--help` for options |
| **docs/** | Extra documentation | Browse for guides and examples |

## How It All Works Together

```
┌─────────────────────────────────────────────────────────────┐
│                         USER                                 │
│                    (Web Browser)                             │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ↓
┌─────────────────────────────────────────────────────────────┐
│                    FRONTEND (Streamlit)                      │
│  • NestChat page: Text input, chat interface                │
│  • NestVision page: Image upload, display results           │
│  • Components: Charts, maps, visualizations                 │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTP requests (JSON)
                         ↓
┌─────────────────────────────────────────────────────────────┐
│                    BACKEND (FastAPI)                         │
│  ┌─────────────────┐              ┌───────────────────┐    │
│  │   NestChat      │              │   NestVision      │    │
│  │   (Text-to-SQL) │              │   (Bird Detection)│    │
│  └────────┬────────┘              └─────────┬─────────┘    │
│           │                                  │               │
│           ↓                                  ↓               │
│  ┌─────────────────┐              ┌───────────────────┐    │
│  │   SQLite DB     │              │   YOLO ONNX       │    │
│  │   (Bird Data)   │              │   Model           │    │
│  └─────────────────┘              └───────────────────┘    │
│           ↓                                  │               │
│  ┌─────────────────┐                        │               │
│  │  Gemini     │←───────────────────────┘               │
│  │  (OpenRouter)   │                                        │
│  └─────────────────┘                                        │
└─────────────────────────────────────────────────────────────┘
                         │
                         ↓
┌─────────────────────────────────────────────────────────────┐
│                   NESTPERTS (Flask)                          │
│  • Expert annotation interface                              │
│  • Swift AI segmentation                                   │
│  • Species labeling                                         │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ↓
┌─────────────────────────────────────────────────────────────┐
│                   VISIONTRAIN                                │
│  • Training data preparation                                │
│  • Model training (YOLO)                                    │
│  • Export to ONNX                                           │
└─────────────────────────────────────────────────────────────┘
```

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

### Data Flow Example: "What colonies are in Texas?"

1. **User types question** in NestChat (frontend)
2. **Frontend sends POST request** to `/ask` endpoint (backend)
3. **Backend calls Gemini** with question + database schema
4. **Claude generates SQL**: `SELECT DISTINCT ColonyName FROM observations WHERE State = 'TX'`
5. **Backend executes SQL** on SQLite database
6. **Database returns results**: ["Smith Island", "Galveston Bay", ...]
7. **Backend calls Claude again** with results
8. **Claude writes answer**: "There are 23 colonies in Texas, including Smith Island, Galveston Bay..."
9. **Backend parses visualization directives** (e.g., `[SHOW_MAP: true]`)
10. **Frontend receives answer + directive**, displays text and map

### Data Flow Example: "Count birds in this image"

1. **User uploads image** in NestVision (frontend)
2. **Frontend sends POST request** to `/cv/inference` with image file (backend)
3. **Backend loads YOLO ONNX model**
4. **Preprocesses image** (resize, normalize)
5. **Runs inference** (model predicts bounding boxes)
6. **Applies NMS** (removes duplicate boxes)
7. **Draws bounding boxes** on image (Claude orange color)
8. **Encodes image to base64**
9. **Returns JSON** with bird count, detections, annotated image
10. **Frontend decodes and displays** annotated image

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

### Path 1: I Want to Understand the Frontend
**Goal:** Learn how Streamlit works and how to build web UIs with Python

1. Read `frontend/README.md`
2. Look at `frontend/app.py` - the entry point
3. Check `frontend/pages/01_nest_chat.py` - simplest page
4. Experiment: Add a new button or text field
5. Study `frontend/components/charts.py` - how charts work

**Time:** 2-4 hours
**Prerequisites:** Basic Python knowledge
**Resources:** Streamlit docs, Plotly docs

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
5. Read `VisionTrain/README.md` - training pipeline

**Time:** 5-8 hours
**Prerequisites:** Basic Python, linear algebra helpful
**Resources:** YOLO docs, PyTorch tutorials

### Path 4: I Want to Train My Own Model
**Goal:** Create a custom bird detection model

1. Read `VisionTrain/README.md` thoroughly
2. Annotate 500+ images in Nestperts
3. Prepare dataset with scripts in `imgdata_prep/`
4. Train model following guide
5. Export to ONNX and deploy

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
- Check you're in the right directory: `pwd` (should show `.../nexus`)

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
