# 🔧 Gallery Image Loading - Debugging Guide

## Problem
Reference images are not loading in the Akinator classification UI gallery.

## What We've Done

### 1. Removed Size Questions ✅
- Size is ambiguous in photos without reference objects
- Akinator now focuses on visible features (color, bill shape, legs, etc.)

### 2. Added Live Candidate Gallery ✅
- Shows top 8 matching species with thumbnails
- Updates dynamically as you answer questions
- Provides visual feedback

### 3. Fixed Image URLs ✅
- Backend returns actual Macaulay Library CDN URLs
- 10 species have direct image URLs
- Gallery code properly handles image display

### 4. Added Comprehensive Debugging ✅
- Console logging shows exactly what's happening
- Multiple test pages to isolate issues
- Direct URL testing (no proxy needed)

---

## 🧪 Testing Steps

### Step 1: Restart the Flask App
```bash
# Stop current app (Ctrl+C if running)
cd /home/olisemeka.dev/Projects/nexus
python3 labeller/app.py --data labeller/nestvision
```

### Step 2: Test Direct Image Loading
Open in browser: **http://localhost:5000/debug-gallery**

This comprehensive test page will show:
- **Test 1**: Direct CDN URLs (no proxy)
- **Test 2**: Simulated gallery (exact replica of Akinator code)
- **Console Output**: Real-time logging

**Expected Results:**
- ✅ All 6 bird images should load
- Console should show: `✅ Loaded BRPE`, `✅ Loaded GREG`, etc.
- Images displayed in both tests

**If images DON'T load:**
- Check browser console (F12) for error messages
- Look for CORS errors, network errors, or 404s
- Note which specific images fail

### Step 3: Test Actual Akinator UI
Open in browser: **http://localhost:5000/classify-akinator**

1. Select a cluster from the sidebar
2. **Open browser dev tools (F12)** → Console tab
3. Watch for these log messages:
   ```
   🚀 Starting Akinator session for bird: 123
   📦 Akinator response: {...}
   ✅ Found candidates, updating gallery: 8 candidates
   🖼️ Updating gallery with candidates: [...]
     BRPE: https://cdn.download.ams.birds.cornell.edu/...
     GREG: https://cdn.download.ams.birds.cornell.edu/...
   ```

4. Look at the right panel - you should see:
   - "Possible Species" header
   - "8 candidates" (or however many)
   - Grid of thumbnails with species codes

**If you see "No photo" placeholders:**
- Check console for error messages
- Look for `❌ Failed to load` errors
- Note the exact error message

### Step 4: Test Individual Image URL
Open this DIRECTLY in a new browser tab:
```
https://cdn.download.ams.birds.cornell.edu/api/v1/asset/63128991/1800
```

**Expected:** You should see a Brown Pelican photo

**If this fails:**
- Network/firewall might be blocking Cornell's CDN
- Check if you can access https://macaulaylibrary.org at all

---

## 🐛 Common Issues & Solutions

### Issue 1: Images Don't Load - "Failed to load"
**Symptoms:** Console shows `❌ Failed to load BRPE from: https://...`

**Possible Causes:**
1. **Network/Firewall**: Your network blocks Cornell's CDN
2. **CORS**: Browser blocks cross-origin images
3. **Invalid URLs**: The asset IDs don't exist

**Solutions:**
1. Test direct URL in browser tab (Step 4 above)
2. Check network tab in dev tools for HTTP status codes
3. Try proxy endpoint (already implemented at `/api/reference_image_proxy`)

### Issue 2: Gallery Doesn't Appear
**Symptoms:** Right panel shows "Answer questions..." but no gallery

**Possible Causes:**
1. API not returning candidates
2. JavaScript error preventing gallery render
3. CSS hiding the gallery

**Debug:**
1. Check console for `✅ Found candidates` message
2. If missing, check for `⚠️ No candidates in response!`
3. Check if candidates array is empty or undefined

### Issue 3: Some Species Have Photos, Others Don't
**Symptoms:** BRPE, GREG, SNEG show images, others show "No photo"

**This is EXPECTED!** Only 10 species have images currently:
- BRPE, GREG, SNEG, DCCO, LAGU, ROYT, BLSK, AWPE, ROSP, WHIB

The other 31 species need images added to `labeller/services/reference_images.py`

---

## 📊 Current Coverage

**Species with images (10/41):**
```python
BRPE - Brown Pelican
GREG - Great Egret
SNEG - Snowy Egret
DCCO - Double-crested Cormorant
LAGU - Laughing Gull
ROYT - Royal Tern
BLSK - Black Skimmer
AWPE - American White Pelican
ROSP - Roseate Spoonbill
WHIB - White Ibis
```

**Species without images (31/41):**
Will show "No photo" placeholder

---

## 🔍 What to Check

When you run the tests, please report back:

1. **Do images load in `/debug-gallery`?**
   - [ ] Yes, all 6 images load
   - [ ] No, none load
   - [ ] Mixed - some load, some don't

2. **What does the browser console show?**
   - Copy/paste any error messages
   - Screenshot if helpful

3. **Does the gallery appear in `/classify-akinator`?**
   - [ ] Yes, I see "Possible Species" section
   - [ ] No, nothing appears

4. **If gallery appears, do images show?**
   - [ ] Yes, I see bird photos
   - [ ] No, I see "No photo" placeholders
   - [ ] I see "Failed" messages

5. **Can you access Cornell CDN directly?**
   - Test: https://cdn.download.ams.birds.cornell.edu/api/v1/asset/63128991/1800
   - [ ] Yes, I see a pelican photo
   - [ ] No, connection fails/timeouts

---

## 🚀 Next Steps

Once we know what's happening from the tests above, we can:

1. **If direct URLs work**: Remove proxy, use direct URLs (simplest)
2. **If CORS blocks**: Enable proxy endpoint (already coded)
3. **If network blocks Cornell**: Cache images locally
4. **If all works**: Add more species images!

---

## 📝 Files Changed

1. `labeller/services/akinator_engine.py` - Removed size questions, hybrid image source
2. `labeller/templates/species_classification_akinator.html` - Gallery UI, logging
3. `labeller/app.py` - Added proxy endpoint, debug routes
4. `labeller/templates/debug_gallery.html` - Comprehensive test page

---

## ✉️ Reporting Results

Please run the tests and let me know:
- Which test page works/fails
- Console messages (copy/paste or screenshot)
- Network tab errors (if any)
- Whether you can access Cornell CDN directly

This will help me pinpoint the exact issue and fix it!
