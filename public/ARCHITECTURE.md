# NestScope Public Architecture

## Overview

NestScope Public is a **single-server application** that serves both API endpoints and the web interface. This architecture simplifies deployment and eliminates connection issues.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────┐
│                    User's Browser                        │
│  ┌──────────────────┐  ┌────────────────────────────┐  │
│  │   Web Interface  │  │  Client-Side CV Models     │  │
│  │   (HTML/CSS/JS)  │  │  (ONNX Runtime Web)        │  │
│  └────────┬─────────┘  └────────┬───────────────────┘  │
│           │                     │                        │
└───────────┼─────────────────────┼────────────────────────┘
            │                     │
            │ HTTP Requests       │ Model Files
            │ (NestChat API)      │ (/models/*.onnx)
            │                     │
            ▼                     ▼
┌──────────────────────────────────────────────────────────┐
│              FastAPI Server (Port 8000)                   │
│  ┌────────────────────┐  ┌──────────────────────────┐   │
│  │  API Endpoints     │  │  Static File Server      │   │
│  │  - /ask/...        │  │  - /static/*             │   │
│  │  - /stats          │  │  - /models/*             │   │
│  │  - /schema         │  │  - Templates             │   │
│  │  - /api/species    │  │                          │   │
│  └────────┬───────────┘  └──────────────────────────┘   │
│           │                                               │
│           ▼                                               │
│  ┌────────────────────┐                                  │
│  │  Agentic SQL Bot   │                                  │
│  │  - SQL Generation  │                                  │
│  │  - Self-Correction │                                  │
│  │  - Streaming       │                                  │
│  └────────┬───────────┘                                  │
│           │                                               │
│           ▼                                               │
│  ┌────────────────────┐                                  │
│  │  SQLite Database   │                                  │
│  │  (Read-Only)       │                                  │
│  └────────────────────┘                                  │
└──────────────────────────────────────────────────────────┘
```

## Components

### 1. FastAPI Server (`main.py`)

**Single unified server** that handles:

- ✅ **API Endpoints** - REST API for NestChat
- ✅ **Web Interface** - Serves HTML templates and static files
- ✅ **Model Files** - Serves ONNX models for client-side inference
- ✅ **Database Access** - Read-only SQLite queries

**Key Features:**
- Jinja2 template rendering
- Static file serving (`/static/`, `/models/`)
- CORS enabled for flexibility
- Server-Sent Events (SSE) streaming

**Ports:**
- Default: 8000 (configurable via `PORT` env var)
- Railway automatically sets `$PORT`

### 2. Client-Side CV Inference (Browser)

**ONNX Runtime Web** runs models directly in the user's browser:

- ✅ **Complete Privacy** - No images sent to server
- ✅ **No Backend Load** - Processing happens client-side
- ✅ **Offline Capable** - Models cached after first load
- ✅ **Cross-Platform** - Works on any device with a modern browser

**Models Served:**
- `/models/swift.onnx` - Bird detection (9.6MB)
- `/models/classifier_swift.onnx` - Species classification (6MB)

**JavaScript:**
- `/static/js/onnx-inference.js` - BirdDetector class
- ONNX Runtime Web CDN - Model execution

**Performance:**
- Desktop: 2-5 seconds
- Mobile: 10-20 seconds (CPU-only)
- Models load once, cached by browser

### 3. Agentic SQL Pipeline (Backend)

**5-Phase pipeline** for accurate NestChat responses:

**Phase 1:** Context & Setup (metadata loading)
**Phase 2:** SQL Generation (structured JSON output)
**Phase 3:** Execution (with error feedback)
**Phase 4:** Retry Loop (max 3 attempts)
**Phase 5:** Answer + Artifacts (streaming)

**Key Classes:**
- `SQLChatbot` - Base chatbot with SQL generation
- `AgenticSQLChatbot` - Extended with self-correction

**LLM Prompts:**
- `prompts/sql_prompt.txt` - SQL generation rules
- `prompts/sql_prompt_reasoning.txt` - Reasoning phase
- `prompts/sql_prompt_generation.txt` - Generation phase
- `prompts/prompt.txt` - Answer generation

### 4. Database (SQLite)

**Read-only access** for security:

- Connection: `sqlite3.connect(uri="file:path?mode=ro")`
- 8.4MB database with 2010-2021 bird surveys
- Enhanced metadata JSON for AI context

**Key Tables:**
- `tblColonyTotals2010-2021_MayJuneCombined` - Aggregated counts
- `tblSpeciesCodes` - Species reference
- `observations` - Raw observation data

## Data Flow

### NestChat Flow

```
User Question
    ↓
FastAPI /ask/agentic/stream
    ↓
AgenticSQLChatbot.generate_sql_query()
    ↓
Execute SQL (read-only connection)
    ↓
If error → Retry with guidance (max 3x)
    ↓
generate_answer_stream() with artifacts
    ↓
Stream SSE events to browser
    ↓
JavaScript parses artifacts & renders
```

### NestVision Flow

```
User Uploads Image
    ↓
JavaScript: BirdDetector.loadModels()
    ↓
Load ONNX models from /models/*
    ↓
BirdDetector.infer(image, confidence)
    ↓
Detection: ONNX Runtime Web (browser)
    ↓
Classification: ONNX Runtime Web (browser)
    ↓
Draw annotations on HTML canvas
    ↓
Display results (no server involved)
```

## Deployment Models

### Local Development

```bash
./run.sh
# Starts: FastAPI on port 8000
# Access: http://localhost:8000
```

### Railway

```bash
railway up
# Railway sets $PORT automatically
# Access: https://your-app.up.railway.app
```

### Docker

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Benefits of Single-Server Architecture

### ✅ Simplified Deployment
- One process to manage
- One port to expose
- No inter-service communication

### ✅ No Connection Issues
- No "connection refused" errors
- No CORS complications
- Same-origin requests

### ✅ Lower Resource Usage
- ~500MB RAM (vs 1.5GB for multi-server)
- Single Python process
- Shared database connections

### ✅ Easier Development
- One terminal to run everything
- One log file to monitor
- Simpler debugging

### ✅ Railway-Friendly
- Works with free tier
- Automatic port detection
- Single Procfile command

## Security Features

### Read-Only Database
```python
uri = f"file:{db_path}?mode=ro"
conn = sqlite3.connect(uri, uri=True)
```

### Query Validation
- Only SELECT and WITH statements allowed
- INSERT/UPDATE/DELETE blocked
- Comment stripping to prevent bypasses

### API Key Protection
- OpenRouter key in environment variable
- Never exposed to client
- Server-side AI calls only

### Client-Side CV Benefits
- No image data sent to server
- Complete user privacy
- No storage of user images
- Processing happens locally

## Performance Characteristics

### Server Startup
- Cold start: 3-5 seconds
- Model loading: N/A (client-side)
- Database connection: <100ms

### NestChat (Backend)
- SQL generation: 1-2 seconds
- Query execution: 0.1-1 second
- Answer streaming: 2-5 seconds
- **Total:** 3-8 seconds

### NestVision (Client-Side)
- Model download: 5-10 seconds (first time only)
- Model loading: 2-3 seconds (first time only)
- Detection: 2-5 seconds (desktop), 10-20s (mobile)
- Classification: 1-3 seconds
- **Total:** 3-8 seconds (after models cached)

### Resource Usage
- Memory: ~500MB (FastAPI + database)
- CPU: Light (spikes during AI calls)
- Disk: 25MB (code + models + database)
- Bandwidth: ~16MB models (one-time download)

## Scaling Considerations

### Horizontal Scaling
- Stateless server design
- Can run multiple instances
- Load balancer distributes requests
- Shared read-only database

### Caching Opportunities
- HTTP cache headers for models
- Browser caching for static assets
- Query result caching (optional)
- Template caching (Jinja2)

### Database Optimization
- Read-only mode prevents locks
- Connection pooling (optional)
- Indexed columns for common queries
- Metadata preloaded at startup

## Technology Stack

### Server-Side
- **FastAPI** - Modern async web framework
- **Uvicorn** - ASGI server
- **SQLite** - Embedded database
- **OpenAI SDK** - OpenRouter API client
- **Pandas** - Data processing
- **Jinja2** - Template engine

### Client-Side
- **ONNX Runtime Web** - Browser-based ML inference
- **Vanilla JavaScript** - No framework overhead
- **Chart.js** - Data visualization
- **Leaflet** - Interactive maps

### AI/ML
- **OpenRouter** - LLM API gateway
- **Claude Sonnet 4.5** - Default model
- **YOLO v8 (ONNX)** - Bird detection
- **ResNet (ONNX)** - Species classification

## Future Enhancements

### Potential Improvements
- [ ] WebGPU acceleration for CV models
- [ ] Progressive Web App (PWA) support
- [ ] Offline mode with IndexedDB
- [ ] WebSocket for real-time updates
- [ ] Query result caching layer
- [ ] Multi-language support

### Architecture Considerations
- Current design favors simplicity over scale
- Optimized for hobby/demo deployments
- Can be split into microservices if needed
- Database could move to PostgreSQL for production

---

**Last Updated:** March 15, 2026
**Architecture Version:** 2.0 (Unified Single-Server)
