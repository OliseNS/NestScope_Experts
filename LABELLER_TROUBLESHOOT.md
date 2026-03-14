# Nestperts/Labeller Troubleshooting Guide

## Problem: Port 5000 won't load / Can't access Nestperts

### Quick Fixes:

#### 1. Check if it's running:
```bash
curl http://localhost:5000/health
```

**Expected:** `{"status": "ok"}`
**If connection refused:** Service isn't running

#### 2. Check the logs:
```bash
tail -f logs/nestperts.log
```

Look for error messages about:
- OAuth configuration
- Database connection (Turso)
- Port already in use

#### 3. Run standalone for debugging:
```bash
./run_labeller_only.sh
```

This runs Nestperts in foreground so you can see errors directly.

#### 4. Test manual start:
```bash
cd labeller
python app.py
```

If you see errors about missing packages, install them:
```bash
pip install -r requirements.txt
```

---

## Common Issues:

### Issue 1: "Port 5000 already in use"

**Solution:**
```bash
# Kill process on port 5000
lsof -ti:5000 | xargs kill -9

# Then restart
./run_app.sh
```

### Issue 2: OAuth errors / "Missing GOOGLE_CLIENT_ID"

**Check .env file:**
```bash
grep GOOGLE .env
```

**Should have:**
- `GOOGLE_CLIENT_ID=...`
- `GOOGLE_CLIENT_SECRET=...`

If missing, create/update `.env` file with your Google OAuth credentials.

### Issue 3: Turso database connection errors

**Check credentials:**
```bash
grep TURSO .env
```

**Should have:**
- `TURSO_DATABASE_URL=https://...`
- `TURSO_AUTH_TOKEN=eyJ...`

### Issue 4: App starts but immediately crashes

**Run with full error output:**
```bash
cd labeller
FLASK_ENV=development python app.py
```

Common causes:
- Missing Python packages (run `pip install -r requirements.txt`)
- Syntax errors in app.py
- Import errors from dependencies

---

## Verification Steps:

### 1. Test app import:
```bash
python test_labeller.py
```

This checks if the app can be imported and all dependencies are available.

### 2. Check port 5000:
```bash
netstat -an | grep 5000
```

If you see `LISTEN`, something is running on port 5000.

### 3. Test OAuth setup:
```bash
curl http://localhost:5000/login
```

Should redirect to Google OAuth or show a login page.

### 4. Check health endpoint:
```bash
curl http://localhost:5000/health
```

Should return: `{"status": "ok"}`

---

## Still Not Working?

### Full restart sequence:
```bash
# 1. Kill all processes
pkill -f "app.py"
pkill -f "uvicorn"

# 2. Clean logs
rm logs/*.log

# 3. Start fresh
./run_app.sh

# 4. Watch logs in real-time
tail -f logs/nestperts.log
```

### Check all services:
```bash
# Backend (port 8000)
curl http://localhost:8000/health

# Webapp (port 8501)
curl http://localhost:8501/api/health

# Labeller (port 5000)
curl http://localhost:5000/health
```

---

## Manual OAuth Setup (if needed):

1. Go to: https://console.cloud.google.com/apis/credentials
2. Create OAuth 2.0 Client ID
3. Authorized redirect URIs:
   - `http://localhost:5000/auth/google/callback`
   - `http://127.0.0.1:5000/auth/google/callback`
4. Copy Client ID and Secret to `.env`

---

## Environment Variables Checklist:

Required in `.env`:
- ✓ `GOOGLE_CLIENT_ID`
- ✓ `GOOGLE_CLIENT_SECRET`
- ✓ `SECRET_KEY`
- ✓ `TURSO_DATABASE_URL`
- ✓ `TURSO_AUTH_TOKEN`
- ✓ `OPENROUTER_API_KEY` (for backend)
- ✓ `DB_PATH` (for backend)

---

## Success Indicators:

When working correctly:
1. `./run_app.sh` shows green checkmarks for all services
2. http://localhost:8501 loads (Public Tools)
3. http://localhost:5000 redirects to Google login (Expert Tools)
4. `curl http://localhost:5000/health` returns `{"status": "ok"}`
5. Logs show no ERROR messages
6. Server status dots in webapp navbar show green

---

## Get Help:

If still having issues, provide:
1. Contents of `logs/nestperts.log`
2. Output of `python test_labeller.py`
3. Output of `curl http://localhost:5000/health`
4. Your OS and Python version
