# 🌐 Browser Testing Guide

## ⚠️ IMPORTANT: Use a Real Browser!

The errors you're seeing are **normal** when testing from the command line. The application is designed to run in a **web browser**, not via curl.

## What You Saw (and Why)

### Error 1: "HTTP 404: Not Found" in NestChat
This likely appeared because:
- You were testing with curl, or
- Browser cache had an old version of chat.js
- Page wasn't fully loaded when JavaScript ran

### Error 2: "BirdDetector is not defined" in NestVision
This appeared because:
- Scripts loaded in wrong order (fixed now)
- Browser cache had old version
- JavaScript tried to run before scripts loaded

## ✅ How to Test Properly

### 1. Start the Server
```bash
cd public/
source ../.venv/bin/activate
./run.sh
```

Wait for:
```
INFO:     Application startup complete.
```

### 2. Open in Browser
Open a **web browser** (Chrome, Firefox, Safari, Edge):
```
http://localhost:8000
```

### 3. Hard Refresh (Clear Cache)
**IMPORTANT:** Clear cached JavaScript:

**Windows/Linux:**
- Press `Ctrl + Shift + R`

**Mac:**
- Press `Cmd + Shift + R`

**Or:**
- Open DevTools (F12)
- Right-click refresh button → "Empty Cache and Hard Reload"

### 4. Test NestChat
1. Click "NestChat" in navigation
2. Type or click example: "How many colonies?"
3. Press Enter or click Send
4. Watch AI generate SQL and answer

**What You Should See:**
- "Generating query..." with ⚡ icon
- SQL code appears
- "Executing query..." with 🔍 icon
- Answer streams in
- Tables/charts appear if applicable

### 5. Test NestVision
1. Click "NestVision" in navigation
2. Wait for "Models ready!" message (5-10 seconds first time)
3. Upload a bird image or drag-and-drop
4. Watch browser run detection

**What You Should See:**
- "Loading AI Models..." → "✓ Models ready!"
- Upload interface appears
- After upload: "Running AI detection..."
- Annotated image with bounding boxes
- Species breakdown and bird count

## 🔍 Debugging in Browser

### Check Browser Console
Press **F12** to open DevTools, go to **Console** tab.

**NestChat - Good output:**
```javascript
Loading chat interface...
Connecting to /ask/agentic/stream
EventSource opened
```

**NestChat - Bad output:**
```javascript
❌ Failed to fetch
❌ 404 Not Found
```
**Fix:** Hard refresh (Ctrl+Shift+R)

**NestVision - Good output:**
```javascript
Loading ONNX models...
✓ Detection model loaded
✓ Classifier model loaded
✓ All models ready
```

**NestVision - Bad output:**
```javascript
❌ BirdDetector is not defined
❌ ort is not defined
```
**Fix:** Hard refresh to reload scripts

### Check Network Tab
Press **F12** → **Network** tab

Look for:
- ✅ `/static/js/chat.js` - Status 200
- ✅ `/static/js/onnx-inference.js` - Status 200
- ✅ `/ask/agentic/stream` - Status 200 (EventStream)
- ✅ `/models/swift.onnx` - Status 200

If you see 404 errors, the server isn't running or files are missing.

## 🎯 Expected Behavior

### Landing Page (/)
- Shows statistics: colonies, species, observations
- Navigation bar with NestChat and NestVision links
- Theme toggle (light/dark mode)

### NestChat (/chat)
1. Type question
2. AI generates SQL (1-2 seconds)
3. Query executes (< 1 second)
4. Answer streams in real-time
5. Charts/maps render automatically

**Example question:**
```
Create a comprehensive dashboard showing:
1) Total bird and nest counts 2010-2021
2) Top 5 species breakdown in 2021
3) Year-over-year growth rates
```

**Expected result:**
- SQL query for counts
- Table with data
- Possibly a chart
- Natural language explanation

### NestVision (/vision)
1. Models download (~16MB, first time only)
2. Upload interface appears
3. Upload image → detection runs in browser
4. Results show:
   - Annotated image with boxes
   - Bird count
   - Species breakdown
   - Processing time

**First run:** 10-15 seconds (downloading models)
**Subsequent runs:** 3-8 seconds (models cached)

## 🚫 Common Mistakes

### ❌ Testing with curl
```bash
curl http://localhost:8000/chat  # Shows HTML, not functional
```
**Problem:** Sees raw HTML, JavaScript doesn't execute

**Solution:** Use a web browser

### ❌ Not Clearing Cache
**Problem:** Old JavaScript runs with new backend

**Solution:** Hard refresh (Ctrl+Shift+R)

### ❌ Testing Too Fast
**Problem:** Click "Send" before page fully loads

**Solution:** Wait for page to load, check console for "ready" messages

### ❌ Forgetting API Key
**Problem:** NestChat doesn't work

**Solution:** Check `.env` has `OPENROUTER_API_KEY`

## ✅ Success Checklist

Test these in your **web browser**:

- [ ] http://localhost:8000 loads with stats
- [ ] Can navigate to /chat
- [ ] Can type and send messages in chat
- [ ] AI responds with streaming text
- [ ] Can navigate to /vision
- [ ] Models load with progress indicator
- [ ] Can upload images
- [ ] Detection runs and shows results
- [ ] No red errors in browser console (F12)

## 📱 Mobile Testing

The app works on mobile but with caveats:

**NestChat:** ✅ Works well on mobile
**NestVision:** ⚠️ Slower (10-20s detection time)

Mobile warning banner appears automatically on small screens.

## 🆘 Still Having Issues?

### Issue: Page won't load at all
**Check:**
```bash
curl http://localhost:8000/health
```
**Should return:**
```json
{"status":"healthy","database":"connected"}
```

If not, server isn't running. Check `./run.sh` output for errors.

### Issue: NestChat doesn't respond
**Check browser console (F12):**
- Look for network errors
- Check if EventSource connected
- Verify `/ask/agentic/stream` endpoint returns data

**Test backend directly:**
```bash
curl -X POST http://localhost:8000/ask/agentic/stream \
  -H "Content-Type: application/json" \
  -d '{"question":"test"}' | head -10
```
Should see SSE events starting with `data: {`

### Issue: NestVision won't load models
**Check browser console (F12):**
- Look for CORS errors
- Check if onnxruntime-web CDN loaded
- Verify internet connection (models download from CDN)

**Test model endpoints:**
```bash
curl -I http://localhost:8000/models/swift.onnx
```
Should return `HTTP/1.1 200 OK`

## 🎉 When It's Working

You'll know it's working when:

1. **Landing page** shows real stats (444 colonies, 96 species)
2. **NestChat** responds to questions with streaming text
3. **Charts and tables** render automatically in chat
4. **NestVision** loads models and detects birds in images
5. **No red errors** in browser console

---

**Remember:** Always test in a **real web browser**, not with curl! 🌐

The application is a Single Page Application (SPA) that requires JavaScript to function.
