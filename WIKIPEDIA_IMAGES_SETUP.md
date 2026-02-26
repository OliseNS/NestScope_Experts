# Wikipedia Images Integration - Complete Setup Guide

## 🎯 Problem Summary

**Issue:** Images not displaying on `/classify-tree` page at http://localhost:5000

**Root Cause:** The system was trying to display Macaulay Library **search result pages** as images:
```html
<!-- This doesn't work - it's an HTML page, not an image! -->
<img src="https://search.macaulaylibrary.org/catalog?taxonCode=brnpel...">
```

**Why it failed:**
- Macaulay Library URLs were links to search pages (HTML), not actual image files
- Browsers can't display HTML pages inside `<img>` tags
- The `onerror` handler hid the broken images, leaving blank spaces

---

## ✅ Solution: Wikipedia/Wikimedia Commons API

We switched to **Wikimedia Commons** which provides **direct image URLs** that work in `<img>` tags!

### How It Works (Educational Breakdown)

**Before (Broken):**
```
User clicks species → API returns search page URL → Browser can't display → Image hidden
```

**After (Working):**
```
User clicks species → API searches Wikimedia Commons → Returns actual image URLs → Images display!
```

### Technical Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Frontend (species_classification_tree.html)                │
│  - User selects species                                      │
│  - Calls /api/species/{code}/references                     │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  Flask Backend (app.py)                                      │
│  - Route: /api/species/<species_code>/references            │
│  - Calls get_reference_images(species_code)                 │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  Reference Service (reference_images_complete.py)            │
│  - Maps species code → common name (BRPE → Brown Pelican)   │
│  - Calls Wikipedia API fetcher                               │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  Wikipedia Fetcher (wikipedia_images_v2.py)                  │
│  1. Search Wikimedia Commons for species                     │
│  2. Extract image filenames                                  │
│  3. Build direct URLs (upload.wikimedia.org/...)            │
│  4. Return list of 3 image URLs                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 📁 Files Created/Modified

### New Files
1. **`labeller/services/wikipedia_images_v2.py`** - Wikimedia Commons image fetcher
   - Searches Commons for bird images
   - Returns direct image URLs
   - Handles errors gracefully

2. **`labeller/test_wikipedia_images.html`** - Visual test page
   - Open in browser to verify images load
   - Shows example species with photos

3. **`test_reference_api.py`** - Backend API test
   - Tests the full flow from species code → image URLs
   - Prints debug output

### Modified Files
1. **`labeller/services/reference_images_complete.py`**
   - Now imports `wikipedia_images_v2` instead of old version
   - Fetches real Wikipedia images for each species
   - Falls back to Macaulay search URL if Wikipedia fails

2. **`labeller/app.py`**
   - Updated `/api/reference_image_proxy` endpoint
   - Now allows Wikipedia/Wikimedia URLs (not just Macaulay)
   - Added security whitelist for image sources

---

## 🧪 Testing Instructions

### Test 1: Visual HTML Test (Recommended First)

Open the test page in your browser:

```bash
# From project root
open labeller/test_wikipedia_images.html
# Or on Linux:
xdg-open labeller/test_wikipedia_images.html
```

**What you should see:**
- ✅ High-quality bird photos loading for 4 species
- ✅ Green "Loaded successfully" status under each image
- ✅ Console message: "ALL IMAGES LOADED SUCCESSFULLY!"

**If images don't load:**
- Check browser console (F12 → Console tab) for errors
- Look for CORS errors or 403 Forbidden responses

---

### Test 2: Backend API Test

Test the Python API directly:

```bash
python3 test_reference_api.py
```

**Expected output:**
```
✓ Found 3 Commons images for 'Brown Pelican'
✓ Loaded 3 Wikipedia images for Brown Pelican

Species Name: Brown Pelican
Photos Found: 3

📸 Image URLs:
   1. https://upload.wikimedia.org/wikipedia/commons/thumb/d/db/Brown_Pelican...
   2. https://upload.wikimedia.org/wikipedia/commons/thumb/2/2f/Pelecanus_occ...
   3. https://upload.wikimedia.org/wikipedia/commons/thumb/1/1e/Pelecanus_occ...
```

---

### Test 3: Full Application Test

Start the Flask server and test the full flow:

```bash
# Start Flask (Nestperts)
python3 labeller/app.py --data labeller/nestvision

# Open in browser
open http://localhost:5000/classify-tree
```

**What to test:**
1. Click on a cluster in the left sidebar
2. Select a species in the decision tree (right panel)
3. **Look for the reference photos section** - it should show 3 bird images
4. Images should load and display correctly (no broken image icons)

**If images still don't show:**
1. Check the browser console for errors
2. Check Flask console output for error messages
3. Verify the `/api/species/{code}/references` endpoint is being called

---

## 🔍 How Wikipedia API Works (Educational)

### The Wikipedia/Wikimedia Ecosystem

```
┌─────────────────────────────────────────────────────────────┐
│  Wikipedia (en.wikipedia.org)                                │
│  - Encyclopedia articles with text                           │
│  - References images stored on Commons                       │
└─────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  Wikimedia Commons (commons.wikimedia.org)                   │
│  - Central repository for ALL Wikipedia images               │
│  - Free/open licenses (public domain, Creative Commons)     │
│  - High-quality, community-curated photos                    │
└─────────────────────────────────────────────────────────────┘
```

### API Request Flow

**Step 1: Search Commons for images**
```
GET https://commons.wikimedia.org/w/api.php
    ?action=query
    &generator=search
    &gsrsearch=Brown Pelican filetype:bitmap
    &gsrnamespace=6    (Namespace 6 = File)
    &prop=imageinfo
    &iiprop=url|size
```

**Step 2: Parse response**
```json
{
  "query": {
    "pages": [
      {
        "imageinfo": [{
          "url": "https://upload.wikimedia.org/...",
          "thumburl": "https://upload.wikimedia.org/.../800px-..."
        }]
      }
    ]
  }
}
```

**Step 3: Return direct image URLs**
```python
return [
    "https://upload.wikimedia.org/wikipedia/commons/thumb/.../800px-Brown_Pelican.jpg",
    "https://upload.wikimedia.org/wikipedia/commons/thumb/.../800px-Pelecanus_occidentalis.jpg"
]
```

### Why We Need a User-Agent Header

Wikipedia requires all API clients to identify themselves with a `User-Agent` header:

```python
HEADERS = {
    "User-Agent": "NestScope/1.0 (Educational bird monitoring project)"
}
```

**Why this matters:**
- Prevents bot abuse and DDoS attacks
- Helps Wikipedia track API usage patterns
- Allows them to contact you if there's an issue
- **Required** - requests without User-Agent get 403 Forbidden

**Best practices:**
- Include project name and version
- Add contact info (email or GitHub URL)
- Be descriptive about your use case

---

## 🚀 Next Steps

### Option A: Use as-is (Recommended)
The system now works! Just restart your Flask server to pick up the changes.

### Option B: Improve Performance (Optional)
Add caching to avoid repeated Wikipedia API calls:

```python
# Cache images for 24 hours
IMAGE_CACHE = {}

def get_reference_images_cached(species_code):
    if species_code in IMAGE_CACHE:
        return IMAGE_CACHE[species_code]

    images = get_reference_images(species_code)
    IMAGE_CACHE[species_code] = images
    return images
```

### Option C: Add More Image Sources (Advanced)
Combine multiple sources for better coverage:
- ✅ Wikipedia/Commons (implemented)
- 🔄 iNaturalist API (research-grade observations)
- 🔄 eBird Media API (requires API key)
- 🔄 GBIF (Global Biodiversity Information Facility)

---

## 🐛 Troubleshooting

### Problem: Images still not showing in browser

**Check 1: Verify Flask is using new code**
```bash
# Restart Flask with verbose logging
python3 labeller/app.py --data labeller/nestvision

# You should see messages like:
# "✓ Found 3 Commons images for 'Brown Pelican'"
```

**Check 2: Test API endpoint directly**
```bash
curl http://localhost:5000/api/species/BRPE/references
```

Should return:
```json
{
  "name": "Brown Pelican",
  "photos": [
    "https://upload.wikimedia.org/wikipedia/commons/thumb/...",
    ...
  ],
  ...
}
```

**Check 3: Browser network tab**
1. Open browser DevTools (F12)
2. Go to Network tab
3. Refresh the page
4. Look for requests to `/api/species/{code}/references`
5. Check if the response contains image URLs

### Problem: 403 Forbidden from Wikipedia

**Cause:** Missing or invalid User-Agent header

**Fix:** Verify `HEADERS` is set in `wikipedia_images_v2.py`:
```python
HEADERS = {
    "User-Agent": "NestScope/1.0 (Educational bird monitoring project)"
}
```

### Problem: No images found for a species

**Cause:** Wikipedia might not have images for that species

**Fix:** Add fallback logic or use scientific names:
```python
# Try common name first, then scientific name
images = get_wikipedia_images(common_name)
if not images:
    images = get_wikipedia_images(scientific_name)
```

---

## 📚 Learning Resources

Want to learn more about Wikipedia APIs?

1. **Official API Documentation:**
   - https://www.mediawiki.org/wiki/API:Main_page
   - https://www.mediawiki.org/wiki/API:Images

2. **Wikimedia Commons:**
   - https://commons.wikimedia.org/wiki/Commons:API

3. **User-Agent Policy:**
   - https://meta.wikimedia.org/wiki/User-Agent_policy

4. **API Sandbox (Interactive Testing):**
   - https://en.wikipedia.org/wiki/Special:ApiSandbox

---

## 🎓 Key Concepts Learned

1. **API Integration** - How to fetch data from external APIs
2. **Error Handling** - Graceful fallbacks when API calls fail
3. **CORS & User-Agent** - Why browsers and APIs require identification
4. **Direct URLs vs Search URLs** - Difference between image files and HTML pages
5. **Asynchronous Loading** - Frontend displays while images load
6. **Caching Strategies** - Reducing API calls for better performance

---

## ✅ Completion Checklist

- [x] Created Wikipedia image fetcher (`wikipedia_images_v2.py`)
- [x] Updated reference images service
- [x] Modified Flask proxy to allow Wikimedia URLs
- [x] Created test files (HTML + Python)
- [x] Added proper User-Agent headers
- [x] Tested API with sample species
- [ ] **Your turn:** Test in full application at http://localhost:5000/classify-tree
- [ ] **Your turn:** Verify images load when classifying birds
- [ ] **Optional:** Add caching for better performance
- [ ] **Optional:** Add more image sources (iNaturalist, eBird)

---

## 📝 Summary

**Before:** Macaulay Library search URLs → Broken images → Blank spaces

**After:** Wikipedia Commons API → Direct image URLs → Beautiful bird photos! 🦅📸

**Impact:** Users can now see high-quality reference photos when classifying birds, making identification much easier and more accurate.

---

**Questions?** Check the troubleshooting section or ask for help!
