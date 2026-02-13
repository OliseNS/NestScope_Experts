# Quick Fix - Restart Labeller

## The Issue
The labeller was started with wrong path: `--data nestvision`
Should be: `--data labeller/nestvision`

## Fix Applied
Updated `run_app.sh` to use correct path.

## To Fix Immediately

### Option 1: Restart Everything (Recommended)
```bash
# Stop current services (Ctrl+C in the terminal running ./run_app.sh)
# Then restart:
./run_app.sh
```

### Option 2: Just Restart Labeller
```bash
# Find and kill labeller process
pkill -f "labeller/app.py"

# Start labeller with correct path
python labeller/app.py --data labeller/nestvision > logs/labeller.log 2>&1 &
```

### Option 3: Manual Test
```bash
# Start labeller manually in a new terminal
cd /home/olise/Projects/nexus
python labeller/app.py --data labeller/nestvision
```

## Verify It's Working

1. **Check labeller is running:**
   ```bash
   curl http://localhost:5000/health
   ```

2. **Check DATASET_PATH:**
   Look at terminal output when labeller starts:
   ```
   Starting OliseLabel on labeller/nestvision
   Images directory: labeller/nestvision/images
   Labels directory: labeller/nestvision/labels
   ```

3. **Try correction again:**
   - Go to NestVision
   - Run detection
   - Click "Correct AI"
   - Should work now!

## What Changed

**Before (WRONG):**
```bash
python labeller/app.py --data nestvision
```
This made it look for `nestvision/` which doesn't exist.

**After (CORRECT):**
```bash
python labeller/app.py --data labeller/nestvision
```
This correctly uses `labeller/nestvision/` which exists.

## Files Changed
- `run_app.sh` - Updated labeller startup command
- `labeller/app.py` - Added directory creation safety check

## Quick Verification

After restarting, test the correction endpoint:
```bash
# Should return success
curl -X POST http://localhost:5000/api/correction/upload \
  -H "Content-Type: application/json" \
  -d '{
    "image_base64":"iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
    "detections":[]
  }'
```

Should see:
```json
{
  "status": "success",
  "image_filename": "correction_xxxxx.jpg",
  "correction_url": "/editor/Corrections"
}
```
