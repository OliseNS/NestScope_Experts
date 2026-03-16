# Testing Instructions for NestScope Public

## Quick Test (2 Minutes)

### 1. Start the Server
```bash
cd public/
source ../.venv/bin/activate
./run.sh
```

Wait for this message:
```
INFO:     Application startup complete.
```

### 2. Open in Browser

**Important:** Use a **real web browser**, not curl!

Open: http://localhost:8000

You should see the NestScope landing page with statistics.

### 3. Test NestChat

1. Click "NestChat" in the navigation
2. Try the example question or ask:
   ```
   Create a comprehensive dashboard showing:
   1) Total bird and nest counts 2010-2021,
   2) Top 5 species breakdown in 2021, and
   3) Year-over-year growth rates
   ```
3. Watch the AI:
   - Generate SQL
   - Execute query
   - Create charts and tables
   - Stream the answer in real-time

**Expected:** Charts and tables appear in the chat

### 4. Test NestVision

1. Click "NestVision" in the navigation
2. Wait for models to load (~16MB, takes 5-10 seconds)
3. Upload a bird image or use drag-and-drop
4. Watch browser-based AI:
   - Run detection
   - Classify species
   - Draw bounding boxes
   - Show results

**Expected:** Annotated image with colored boxes around birds

## Common Issues & Solutions

### "HTTP 404: Not Found" in NestChat

**Problem:** JavaScript trying to call backend before page fully loads

**Solution:**
1. Hard refresh the page (Ctrl+Shift+R or Cmd+Shift+R)
2. Clear browser cache
3. Check browser console (F12) for actual error
4. Make sure server is running: `curl http://localhost:8000/health`

### "BirdDetector is not defined" in NestVision

**Problem:** Scripts loading in wrong order or cached old version

**Solution:**
1. Hard refresh (Ctrl+Shift+R)
2. Clear browser cache
3. Check browser console - should see "Loading ONNX models..."
4. Verify script is accessible: `curl http://localhost:8000/static/js/onnx-inference.js`

### Server Won't Start

**Problem:** Port already in use

**Solution:**
```bash
# Kill any existing server
pkill -f "uvicorn main:app"

# Wait a moment
sleep 2

# Try again
./run.sh
```

### Models Not Loading in NestVision

**Problem:** Internet connection or CORS issue

**Solution:**
1. Check internet connection (models download from CDN)
2. Check browser console for errors
3. Try different browser (Chrome/Firefox work best)
4. Disable browser extensions that might block scripts

## Verification Checklist

Use browser, not curl!

- [ ] Landing page loads with statistics
- [ ] NestChat page loads
- [ ] Can ask questions in NestChat
- [ ] SQL generates and executes
- [ ] Answers stream in real-time
- [ ] Charts/tables appear in chat
- [ ] NestVision page loads
- [ ] Models load (see progress message)
- [ ] Can upload images
- [ ] Detection runs in browser
- [ ] Annotated image displays

## Browser Console Checks

Press F12 to open browser console.

**NestChat should show:**
```
Loading chat interface...
EventSource connected
```

**NestVision should show:**
```
Loading ONNX models...
✓ Detection model loaded
✓ Classifier model loaded
✓ All models ready
```

## Performance Expectations

**NestChat:**
- SQL generation: 1-2 seconds
- Query execution: 0.1-1 second
- Answer streaming: 2-5 seconds
- **Total:** 3-8 seconds

**NestVision:**
- First time (model download): 10-15 seconds
- Model loading: 2-3 seconds
- Detection: 2-5 seconds (desktop), 10-20s (mobile)
- **Total first run:** 15-25 seconds
- **Subsequent runs:** 3-8 seconds (models cached)

## Known Limitations

### NestChat
- Requires OpenRouter API key in `.env`
- Internet connection required for AI
- Max 3 retry attempts for SQL errors

### NestVision
- Models are ~16MB (one-time download)
- Slower on mobile devices (CPU-only)
- Requires modern browser with WebAssembly
- Best on desktop with good CPU

## Browser Compatibility

### ✅ Fully Supported
- Chrome 90+
- Firefox 88+
- Edge 90+
- Safari 14+

### ⚠️ Limited Support
- Mobile browsers (slower)
- Older browsers (may not support ONNX Runtime Web)

### ❌ Not Supported
- IE11 (no WebAssembly)
- Very old mobile browsers

## Debug Mode

To see detailed logs:

1. Open browser console (F12)
2. Look for errors (red text)
3. Check Network tab for failed requests
4. Check Console tab for JavaScript errors

Common console errors and fixes:

**"Failed to fetch"**
→ Backend not running or wrong URL
→ Solution: Check `curl http://localhost:8000/health`

**"CORS policy"**
→ Browser blocking request
→ Solution: Shouldn't happen (same origin), check URL

**"onnxruntime is not defined"**
→ ONNX Runtime CDN didn't load
→ Solution: Check internet, try different CDN

**"BirdDetector is not a constructor"**
→ Script loading order wrong
→ Solution: Hard refresh browser

## Testing in Production (Railway)

Once deployed to Railway:

1. Get your Railway URL: `https://your-app.up.railway.app`
2. Add `/chat` for NestChat
3. Add `/vision` for NestVision
4. Test same as local

**Note:** First request may be slow (cold start ~10-15s)

## Success Criteria

You know it's working when:

✅ You can ask NestChat a question and get an answer with charts
✅ You can upload an image to NestVision and see bird detections
✅ No console errors (F12)
✅ Server logs show no errors

---

**If tests pass:** Everything is working! 🎉

**If tests fail:** Check browser console (F12) and server logs for actual errors
