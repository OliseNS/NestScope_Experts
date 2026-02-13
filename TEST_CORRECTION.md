# Testing the Correction Feature

## How to Test

1. **Start all services:**
   ```bash
   ./run_app.sh
   ```

2. **Check services are running:**
   - FastAPI: http://localhost:8000/health
   - Streamlit: http://localhost:8501
   - Labeller: http://localhost:5000

3. **Upload and detect:**
   - Go to http://localhost:8501
   - Click "NestVision" tab
   - Upload an image (or use example)
   - Wait for detection

4. **Correct AI:**
   - Click "🔧 Correct AI" button
   - Should automatically open correction tool in new tab
   - Image should be visible on canvas
   - Bounding boxes should be drawn

5. **Check browser console:**
   - Press F12 in correction page
   - Check console for any errors
   - Look for:
     - "Image loaded successfully"
     - "Labels loaded"
     - Any error messages

## Debugging

### If image doesn't show:

1. **Check browser console** (F12)
   - Look for "Failed to load image" error
   - Check the image URL being loaded

2. **Check labeller logs:**
   ```bash
   tail -f logs/labeller.log
   ```
   Look for:
   - "[CORRECTION] Saving image to: ..."
   - "[SERVE IMAGE] Requested hash: ..."

3. **Test image URL directly:**
   - Copy the image hash from the correction URL
   - Go to: http://localhost:5000/api/correction/image/{hash}
   - Should display the image

4. **Check file exists:**
   ```bash
   ls -la labeller/nestvision/corrections/images/
   ```

5. **Check file permissions:**
   ```bash
   ls -l labeller/nestvision/corrections/images/*.jpg
   ```

## Expected Behavior

### When you click "Correct AI":
1. ✅ Shows "Uploading to correction tool..." spinner
2. ✅ Shows "✅ Uploaded! Opening correction tool in new tab..."
3. ✅ New tab opens automatically
4. ✅ Image loads on canvas
5. ✅ Bounding boxes are drawn
6. ✅ Classes list shows on left sidebar

### In the correction tool:
1. ✅ Can click boxes to change their class
2. ✅ Can draw new boxes by dragging
3. ✅ Can delete boxes with Delete key
4. ✅ Can save corrections with "💾 Save Corrections"
5. ✅ Success message appears
6. ✅ Window closes after save

## Known Issues

- If image is very large (>10MB), upload may be slow
- Browser popup blocker may prevent auto-open (use fallback link)
- Canvas may not scale on very small screens

## Files to Check

- `labeller/nestvision/corrections/images/` - Uploaded images
- `labeller/nestvision/corrections/labels/` - Correction labels
- `logs/labeller.log` - Labeller debug output
- Browser console - JavaScript errors

## Test Image Hashes

Current test image: `27c02e7dea3a27b1.jpg`
Test URL: http://localhost:5000/api/correction/image/27c02e7dea3a27b1
