# NestScope Complete Startup Guide

## Quick Start

```bash
./run_app.sh
```

Then open: **http://localhost:8501**

---

## What Gets Started

### 1. FastAPI Backend (Port 8000)
- **Purpose:** Text-to-SQL, CV inference, database API
- **Health:** http://localhost:8000/health
- **Docs:** http://localhost:8000/docs
- **Log:** `tail -f logs/server.log`

### 2. Public Webapp (Port 8501)
- **Purpose:** NestChat, NestVision (no auth required)
- **URL:** http://localhost:8501
- **Health:** http://localhost:8501/api/health
- **Log:** `tail -f logs/webapp.log`

### 3. Expert Platform (Port 5000)
- **Purpose:** Nestperts, NestDB, Flood Intelligence (OAuth required)
- **URL:** http://localhost:5000
- **Health:** http://localhost:5000/health
- **Log:** `tail -f logs/nestperts.log`

---

## Startup Sequence

The script starts services in this order to ensure dependencies are met:

1. **FastAPI Backend** (waits for health check)
   - Retries up to 10 times with 2-second intervals
   - Must be healthy before proceeding

2. **Public Webapp** (waits 2 seconds)
   - Connects to backend for API calls

3. **Expert Platform** (waits 3 seconds, checks health)
   - Connects to backend for NestDB and Flood Intelligence
   - Requires OAuth for access

---

## Verification Steps

### Step 1: Check All Services Started
Look for green checkmarks in the startup output:
```
✓ Server health check passed
✓ Webapp process started
✓ Nestperts process started
✓ Nestperts health check passed
```

### Step 2: Test Public Tools
```bash
# Open in browser
xdg-open http://localhost:8501

# Or test endpoints
curl http://localhost:8501/api/health
curl http://localhost:8000/health
```

**Expected:**
- Landing page loads with stats
- NestChat page works
- NestVision page works
- Server status dots show green

### Step 3: Test Expert Tools
```bash
# Open in browser
xdg-open http://localhost:5000

# Or test health
curl http://localhost:5000/health
```

**Expected:**
- Redirects to Google OAuth login
- After login, shows Projects page
- NestDB loads (no CORS errors)
- Flood Intelligence loads data

---

## Common Issues & Fixes

### Issue 1: "Port already in use"

**Symptoms:**
```
⚠ Port 5000 already in use
```

**Fix:**
```bash
# Kill processes on all ports
lsof -ti:8000 | xargs kill -9
lsof -ti:8501 | xargs kill -9
lsof -ti:5000 | xargs kill -9

# Restart
./run_app.sh
```

### Issue 2: CORS Errors in NestDB/Flood Intelligence

**Symptoms:**
```
Cross-Origin Request Blocked: The Same Origin Policy disallows reading the remote resource at http://localhost:8000
```

**Root Cause:**
- Backend (port 8000) not running when page loads
- API_BASE_URL not configured correctly

**Fix:**
```bash
# 1. Verify backend is running
curl http://localhost:8000/health

# 2. Check .env has API_BASE_URL
grep API_BASE_URL .env

# Should show: API_BASE_URL=http://localhost:8000

# 3. Restart everything
./run_app.sh
```

### Issue 3: Expert Tools Pages Load Slowly

**Symptoms:**
- NestDB or Flood Intelligence takes 30+ seconds to load
- Blank page or loading spinner forever

**Root Cause:**
- Backend not ready when page loads
- Fetching data before backend health check

**Fix:**
Already implemented! Pages now:
1. Check backend health before fetching data
2. Show clear error if backend unavailable
3. Offer retry button

**Manual test:**
```bash
# Start backend first
python -m uvicorn server.main:app --host 0.0.0.0 --port 8000 --reload

# Wait 5 seconds, then start labeller
cd labeller && python app.py
```

### Issue 4: Labeller Works Standalone but Not from run_app.sh

**Symptoms:**
```bash
# This works:
cd labeller && python app.py

# This doesn't:
./run_app.sh
```

**Root Cause:**
- Working directory issue (imports failing)
- Relative paths not resolving

**Fix:**
Updated `run_app.sh` to run from labeller directory:
```bash
LABELLER_DIR="$(cd labeller && pwd)"
(cd "$LABELLER_DIR" && python app.py) > logs/nestperts.log 2>&1 &
```

---

## Environment Variables Required

Check your `.env` file has:

```bash
# Backend API (for text-to-SQL)
OPENROUTER_API_KEY=your-key-here

# Database
DB_PATH=data/bird_data_complete.db

# OAuth (for expert tools)
GOOGLE_CLIENT_ID=your-client-id
GOOGLE_CLIENT_SECRET=your-client-secret
SECRET_KEY=random-secret-key

# Turso Cloud (for user management)
TURSO_DATABASE_URL=https://users-....turso.io
TURSO_AUTH_TOKEN=eyJ...

# Backend URL (for expert tools API calls)
API_BASE_URL=http://localhost:8000
```

---

## Testing Individual Services

### Test Backend Only:
```bash
python -m uvicorn server.main:app --host 0.0.0.0 --port 8000 --reload

# Test
curl http://localhost:8000/health
# Expected: {"status":"healthy"}
```

### Test Public Webapp Only:
```bash
cd webapp
python app.py

# Test
curl http://localhost:8501/api/health
# Expected: {"status":"ok","service":"webapp"}
```

### Test Expert Platform Only:
```bash
./run_labeller_only.sh

# Or manually:
cd labeller
python app.py

# Test
curl http://localhost:5000/health
# Expected: {"status":"ok"}
```

---

## Performance Expectations

### Backend (FastAPI):
- **Startup:** 2-5 seconds
- **Health check:** < 100ms
- **Text-to-SQL query:** 2-5 seconds
- **CV inference:** 1-3 seconds

### Public Webapp (Flask):
- **Startup:** 1-2 seconds
- **Page load:** < 500ms
- **SSE streaming:** Real-time

### Expert Platform (Flask + OAuth):
- **Startup:** 2-4 seconds
- **Login redirect:** < 500ms
- **NestDB load:** 1-2 seconds (after backend check)
- **Flood Intelligence load:** 2-3 seconds (fetching data)

---

## Architecture Reminder

```
┌─────────────────────────────────────────────────────┐
│                  NestScope System                    │
└─────────────────────────────────────────────────────┘

PUBLIC (No Auth)              EXPERT (OAuth Required)
Port 8501                     Port 5000
├─ Landing Page               ├─ Nestperts
├─ NestChat                   ├─ NestDB
└─ NestVision                 ├─ Flood Intelligence
                              ├─ User Management
      │                       └─ Help/Docs
      │                              │
      └──────────┬───────────────────┘
                 │
                 ▼
          FastAPI Backend
          Port 8000
          ├─ Text-to-SQL
          ├─ CV Inference
          ├─ Database API
          └─ Flood Data
```

---

## Success Indicators

✅ **All working correctly:**
- `./run_app.sh` shows all green checkmarks
- http://localhost:8501 loads landing page
- http://localhost:5000 redirects to Google login
- Server status dots in webapp navbar show green
- NestDB loads tables without CORS errors
- Flood Intelligence loads map and data
- No errors in any log files

---

## Getting Help

### Check logs:
```bash
# Backend
tail -f logs/server.log

# Public webapp
tail -f logs/webapp.log

# Expert platform
tail -f logs/nestperts.log
```

### Run diagnostics:
```bash
# Test labeller can be imported
python test_labeller.py

# Check ports in use
netstat -an | grep LISTEN | grep -E "8000|8501|5000"

# Test all health endpoints
curl http://localhost:8000/health
curl http://localhost:8501/api/health
curl http://localhost:5000/health
```

### Still having issues?

See:
- `LABELLER_TROUBLESHOOT.md` - Expert platform issues
- `ARCHITECTURE.md` - System architecture
- `labeller/README.md` - Expert platform docs

---

## Quick Reference

### Start everything:
```bash
./run_app.sh
```

### Start individual services:
```bash
# Backend only
python -m uvicorn server.main:app --host 0.0.0.0 --port 8000 --reload

# Webapp only
cd webapp && python app.py

# Expert platform only
./run_labeller_only.sh
```

### Stop everything:
```bash
# Press Ctrl+C in terminal, or:
pkill -f "uvicorn"
pkill -f "app.py"
```

### Restart everything:
```bash
./run_app.sh
```

---

**Happy monitoring! 🦅**
