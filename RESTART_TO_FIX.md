# Restart Required to Fix Issues

## Issues Fixed

1. **State file not loading** - Now looks in correct location based on dataset path
2. **Images not loading** - Now serves from correct directory
3. **Homepage not showing users** - Will show users from correct state file

## Changes Made

- Created `Config` class to hold configuration that updates at runtime
- Updated all functions to use `Config.DATASET_PATH` instead of module-level `DATASET_PATH`
- State file now automatically placed in parent directory of dataset
  - Dataset: `labeller/nestvision` → State: `labeller/project_state.json`

## RESTART NOW

```bash
# Stop all services (Ctrl+C in terminal)
# Then restart:
./run_app.sh
```

## What to Expect After Restart

### Console Output:
```
Starting OliseLabel on labeller/nestvision
State file: labeller/project_state.json
Images directory: labeller/nestvision/images
Labels directory: labeller/nestvision/labels
```

### Homepage (http://localhost:5000):
- Should show all users from project_state.json
- Including "Satyam - Approved" with all their images
- Including "Corrections" with correction images

### Correction Images:
- Should load properly in editor
- Image URL: http://localhost:5000/images/correction_xxx.jpg
- Should display on canvas

## Test After Restart

1. **Check homepage:**
   ```bash
   curl http://localhost:5000/
   ```
   Should show users

2. **Check state loading:**
   Look at labeller console output - should show correct state file path

3. **Test correction:**
   - Go to NestVision
   - Run detection
   - Click "Correct AI"
   - Should load image and show all tools

4. **Test image serving:**
   ```bash
   curl -I http://localhost:5000/images/correction_1770995079761.jpg
   ```
   Should return 200 OK (not 404)

## Why This Fixes Everything

**Before:**
- `DATASET_PATH = "nestvision"` (hardcoded at module load)
- `STATE_FILE = "project_state.json"` (looks in wrong place)
- Command line arg `--data labeller/nestvision` didn't update module variables
- Functions used old hardcoded values

**After:**
- `Config.DATASET_PATH` updated at runtime from command line
- `Config.STATE_FILE` automatically set to parent directory
- All functions use `Config.*` which reflects runtime values
- Paths are now correct!

## If Still Not Working

1. **Check labeller console output** for the paths being used
2. **Verify project_state.json exists** at `labeller/project_state.json`
3. **Check image exists** at `labeller/nestvision/images/correction_xxx.jpg`
4. **Try accessing state file directly:**
   ```bash
   cat labeller/project_state.json | head -20
   ```
