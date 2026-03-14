# NestScope Architecture

## Two Separate Applications

NestScope consists of **TWO independent applications** with clear separation of concerns:

---

## 1. Public Tools (No Authentication)

**Location:** `/webapp` + `/server` (FastAPI backend)
**Ports:** 8501 (webapp), 8000 (FastAPI backend)
**Tech Stack:** FastAPI + Lightweight HTML/CSS/JS
**Authentication:** None required

### Features:
- **NestChat**: Natural language queries on bird data
  - Text-to-SQL with Claude
  - Interactive charts and maps
  - Data export to CSV
  - Conversation context maintained

- **NestVision**: AI bird detection
  - Upload images for detection
  - Auto species classification
  - Annotated results download
  - Example images gallery

### Running:
```bash
# Start webapp only
cd webapp && python app.py

# Or start everything (recommended)
./run_app.sh
```

### Endpoints:
- `http://localhost:8501` - Web interface
- `http://localhost:8501/chat` - NestChat
- `http://localhost:8501/vision` - NestVision
- `http://localhost:8501/api/services/status` - Health check for all services
- `http://localhost:8000` - FastAPI backend
- `http://localhost:8000/docs` - API documentation

---

## 2. Expert Tools (OAuth Authentication Required)

**Location:** `/labeller`
**Port:** 5000
**Tech Stack:** Flask + OAuth (Google)
**Authentication:** Required (OAuth 2.0)

### Features:
- **Nestperts**: Advanced annotation platform
  - Project-based workflow
  - MobileSAM segmentation
  - Multi-expert collaboration
  - YOLO/COCO/GeoJSON export

- **NestDB**: Database management
  - Table explorer
  - SQL query editor
  - Data versioning
  - Change tracking

- **Flood Intelligence**: NOAA flood data
  - Real-time water levels
  - Predictions and alerts
  - Colony risk assessment

- **Help & Docs**: Documentation portal

### Running:
```bash
cd labeller
bash run_nestperts.sh

# Or start everything (recommended)
./run_app.sh  # Starts all services
```

### Endpoints:
- `http://localhost:5000` - Main platform (requires auth)
- `http://localhost:5000/nestperts` - Annotation tool
- `http://localhost:5000/nestdb` - Database manager
- `http://localhost:5000/flood` - Flood intelligence
- `http://localhost:5000/help` - Documentation

---

## System Architecture Diagram

```
┌─────────────────────────────────────────────────────┐
│                   NestScope System                   │
└─────────────────────────────────────────────────────┘

PUBLIC TOOLS (No Auth)                    EXPERT TOOLS (Auth Required)
┌──────────────────────┐                 ┌──────────────────────┐
│  Webapp (Port 8501)  │                 │  Labeller (Port 5000)│
│                      │                 │                      │
│  - Landing Page      │────Links to────▶│  - Nestperts        │
│  - NestChat          │                 │  - NestDB           │
│  - NestVision        │                 │  - Flood Intel      │
│  - Server Status     │                 │  - Help/Docs        │
└──────┬───────────────┘                 └──────────────────────┘
       │                                           │
       │ API Calls                                │ OAuth
       ▼                                          ▼
┌──────────────────────┐                 ┌──────────────────────┐
│ FastAPI (Port 8000)  │                 │   Google OAuth       │
│                      │                 │   (Authentication)   │
│  - Text-to-SQL       │                 └──────────────────────┘
│  - CV Inference      │
│  - Database Queries  │
│  - Health Checks     │
└──────────────────────┘
```

---

## Clear Separation of Concerns

### Webapp (Public)
- ✅ Simple, fast, no authentication
- ✅ Read-only database access
- ✅ Links to Expert Tools
- ✅ Shows health status of all services
- ❌ NO user management
- ❌ NO write operations to DB
- ❌ NO annotation features

### Labeller (Expert)
- ✅ OAuth authentication required
- ✅ User roles and permissions
- ✅ Write access to database
- ✅ Advanced annotation tools
- ✅ Links back to Public Tools
- ❌ Does NOT handle public queries
- ❌ Does NOT serve NestChat/NestVision

---

## Communication Between Systems

### From Public → Expert:
- Simple HTML links that open in new tab
- No API calls between systems
- Users navigate via browser

### Health Monitoring:
- Webapp checks health of both systems
- Status dots show real-time availability:
  - 🟢 Green = Healthy
  - 🔴 Red = Offline
  - 🟡 Yellow = Checking

---

## Starting Everything

**Single Command:**
```bash
./run_app.sh
```

This starts:
1. FastAPI backend (port 8000)
2. Public webapp (port 8501) - **OPEN THIS**
3. Expert labeller (port 5000)

**Access:**
- Public: http://localhost:8501
- Expert: http://localhost:5000 (OAuth required)
- API Docs: http://localhost:8000/docs

---

## Port Summary

| Port | Service | Auth | Purpose |
|------|---------|------|---------|
| 8000 | FastAPI Backend | No | Text-to-SQL, CV inference, data queries |
| 8501 | Public Webapp | No | NestChat, NestVision UI |
| 5000 | Expert Platform | Yes | Nestperts, NestDB, Flood Intelligence |

---

## Development Guidelines

### When working on Public Tools:
- Edit files in `/webapp` or `/server`
- No authentication logic
- Keep it simple and fast
- Read-only database operations

### When working on Expert Tools:
- Edit files in `/labeller`
- Use `@login_required` decorators
- User permissions matter
- Can write to database

### Never Mix:
- ❌ Don't add auth to webapp
- ❌ Don't add public features to labeller
- ❌ Don't share session state
- ✅ Keep them completely separate
- ✅ Link between them via URLs
