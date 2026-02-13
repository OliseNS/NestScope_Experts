# Fix Image Loading - URGENT

## Problem
Images exist but return 404 because labeller is running OLD CODE before Config fix.

## Quick Fix - Run This Command:

```bash
./restart_labeller.sh
```

Or manually:
```bash
# Kill old labeller
pkill -f "labeller/app.py"

# Start new one
python labeller/app.py --data labeller/nestvision > logs/labeller.log 2>&1 &
```

## What This Does

1. Stops the old labeller process (running old code)
2. Starts new labeller with Config fixes
3. Now uses correct paths for images

## Verify It's Fixed

After restart, you should see in logs:
```bash
tail -f logs/labeller.log
```

Look for:
```
Starting OliseLabel on labeller/nestvision
State file: labeller/project_state.json
Images directory: labeller/nestvision/images
Labels directory: labeller/nestvision/labels
```

Then test image:
```bash
curl -I http://localhost:5000/images/correction_1770995345777.jpg
```

Should return:
```
HTTP/1.1 200 OK
Content-Type: image/jpeg
```

## Debug Mode Active

The image serving route now has debug logging. After restart, check logs to see:
```
[SERVE_IMAGE] Requested: correction_xxx.jpg
[SERVE_IMAGE] Serving from: labeller/nestvision/images
[SERVE_IMAGE] Full path: labeller/nestvision/images/correction_xxx.jpg
[SERVE_IMAGE] File exists: True
```

## Why This Fixes It

**Before (old process):**
- Using hardcoded `DATASET_PATH = "nestvision"`
- Looking in wrong directory
- Returns 404

**After (restarted with new code):**
- Uses `Config.DATASET_PATH = "labeller/nestvision"`
- Looks in correct directory
- Returns 200 + image

## Other Services

Don't need to restart:
- ✅ FastAPI (port 8000) - Keep running
- ✅ Streamlit (port 8501) - Keep running

Only restart:
- 🔄 Labeller (port 5000) - MUST restart to load new code

## Alternative: Restart Everything

If you prefer to restart all services:
```bash
# Stop all (Ctrl+C in terminal running ./run_app.sh)
# Then:
./run_app.sh
```

This will start everything fresh with the new code.
