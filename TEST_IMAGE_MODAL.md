# Image Modal & Load More - Testing Guide

## ✅ What's New

I've added two major improvements to the reference images in the classification interface:

### 1. **Load More Button**
- **Initial Load**: 5 images per species (instead of 3)
- **Pagination**: Click "Load More Images" to fetch 5 more images
- **Smart Loading**: Button only appears when more images are available
- **State Management**: Tracks loaded images per species independently

### 2. **Image Modal/Lightbox**
- **Click to View**: Click any reference image to open it in a full-screen modal
- **High Quality**: View images at full resolution without leaving the page
- **Easy Navigation**:
  - Click the × button to close
  - Press ESC key to close
  - Click outside the image to close
- **Species Name**: Shows species name as caption

---

## 🧪 Testing Instructions

### Test 1: Basic Image Loading

1. **Start Flask**:
   ```bash
   python3 labeller/app.py --data labeller/nestvision
   ```

2. **Open Classification Interface**:
   ```bash
   xdg-open http://localhost:5000/classify-tree
   ```

3. **Navigate to Species Selection**:
   - Click a cluster from the left sidebar
   - Go through the decision tree (Size → Color → Species)
   - When you reach species options, you should see reference images

4. **Check Initial Load**:
   - ✅ Each species shows 5 reference images (in a 2-column grid)
   - ✅ Images load from Wikipedia/Wikimedia Commons
   - ✅ "Load More Images" button appears below the images

---

### Test 2: Load More Functionality

1. **Click "Load More Images"**:
   - Button should show "Loading..." temporarily
   - 5 more images should appear below existing ones
   - Grid expands to show all loaded images

2. **Keep Loading**:
   - Click "Load More Images" again
   - More images should load
   - Button disappears when no more images are available

3. **Multiple Species**:
   - Each species maintains its own pagination state
   - Loading more images for Species A doesn't affect Species B

**Expected Behavior:**
```
Initial: [img1] [img2] [img3] [img4] [img5] [Load More]
          ↓ (click Load More)
After:   [img1] [img2] [img3] [img4] [img5]
         [img6] [img7] [img8] [img9] [img10] [Load More]
          ↓ (click Load More again)
Final:   [img1] [img2] ... [img15]
         (no more button - all images loaded)
```

---

### Test 3: Image Modal

1. **Click Any Image**:
   - Modal should open with dark overlay (95% black background)
   - Image displays at full resolution (max 90% of screen)
   - Species name appears as caption below image

2. **Close Modal - Method 1 (× Button)**:
   - Click the × button in top-right corner
   - Modal should close smoothly

3. **Close Modal - Method 2 (ESC Key)**:
   - Open modal again
   - Press ESC key
   - Modal should close

4. **Close Modal - Method 3 (Background Click)**:
   - Open modal again
   - Click anywhere outside the image (on the dark background)
   - Modal should close

5. **Multiple Opens**:
   - Open different images
   - Each should display correctly in the modal
   - Previous modal state shouldn't interfere

---

## 📸 Visual Examples

### Before (Old Behavior):
```
Reference Images:
┌─────┬─────┬─────┐
│ img1│ img2│ img3│  → Click opens new tab
└─────┴─────┴─────┘
(Only 3 images, no way to see more)
```

### After (New Behavior):
```
Reference Images:
┌─────┬─────┐
│ img1│ img2│  → Click opens modal
├─────┼─────┤
│ img3│ img4│
├─────┼─────┤
│ img5│     │
├─────┴─────┤
│ Load More │  → Click loads 5 more
└───────────┘
```

---

## 🐛 Troubleshooting

### Problem: Images not loading

**Check Flask console for errors:**
```bash
# Look for messages like:
✓ Loaded 5 Wikipedia images for Brown Pelican (offset=0, limit=5)
```

**Check browser console (F12 → Console):**
```javascript
// Should see successful API calls:
GET /api/species/BRPE/references?offset=0&limit=5  → 200 OK
```

---

### Problem: Load More button doesn't appear

**Possible causes:**
1. **All images already loaded** - Expected behavior if species has ≤5 images
2. **API not returning `has_more` flag** - Check API response:
   ```bash
   curl http://localhost:5000/api/species/BRPE/references?offset=0&limit=5
   ```
   Should return:
   ```json
   {
     "photos": ["url1", "url2", ...],
     "has_more": true,  ← This flag controls button visibility
     "offset": 0,
     "limit": 5
   }
   ```

---

### Problem: Modal doesn't open

**Check browser console for errors:**
```javascript
// Common issues:
- openImageModal is not defined
- modalImage element not found
```

**Verify modal HTML exists:**
```javascript
// In browser console:
document.getElementById('imageModal')  // Should not be null
```

---

## 🎓 How It Works (Educational)

### Backend Pagination Logic

```python
# API: /api/species/BRPE/references?offset=5&limit=5
#
# offset=5: Skip first 5 images
# limit=5: Return next 5 images
#
# Wikipedia Commons search returns many images.
# We slice them based on offset/limit:
#
# all_images = [img1, img2, img3, ... img20]
# paginated = all_images[5:10]  # Returns [img6, img7, img8, img9, img10]
```

**Flow:**
```
User clicks "Load More"
    ↓
Frontend: offset = current_count (e.g., 5)
    ↓
Backend: Fetch images from Wikipedia
    ↓
Backend: Slice array → images[5:10]
    ↓
Backend: Return 5 images + has_more flag
    ↓
Frontend: Append new images to grid
    ↓
Frontend: Update offset (5 → 10)
    ↓
Frontend: Show/hide "Load More" based on has_more
```

---

### Frontend State Management

```javascript
// Each species tracks its own pagination state:
loadedImagesState = {
  "BRPE": {
    offset: 10,        // Already loaded 10 images
    limit: 5,          // Fetch 5 at a time
    hasMore: true,     // More images available
    speciesName: "Brown Pelican"
  },
  "GREG": {
    offset: 5,         // Only loaded 5 images
    limit: 5,
    hasMore: true,
    speciesName: "Great Egret"
  }
}

// When user clicks "Load More" for BRPE:
// → Fetches with offset=10, limit=5
// → Displays images 11-15
// → Updates offset to 15
```

---

### Modal CSS Tricks

```css
/* Modal starts hidden */
.image-modal {
    display: none;
}

/* When active, uses flexbox centering */
.image-modal.active {
    display: flex;           /* Enable flexbox */
    align-items: center;     /* Vertical centering */
    justify-content: center; /* Horizontal centering */
}

/* Image scales to fit screen */
.modal-image {
    max-width: 100%;   /* Never wider than viewport */
    max-height: 85vh;  /* Max 85% of viewport height */
    object-fit: contain; /* Maintain aspect ratio */
}
```

---

## 🎯 Summary of Changes

### Files Modified:

1. **`labeller/services/wikipedia_images_v2.py`**
   - Added `offset` parameter to `get_wikipedia_images()`
   - Supports pagination for "Load More" functionality

2. **`labeller/services/reference_images_complete.py`**
   - Added `offset` and `limit` parameters to `get_reference_images()`
   - Passes pagination to Wikipedia API

3. **`labeller/app.py`**
   - Updated `/api/species/<code>/references` endpoint
   - Accepts `?offset=X&limit=Y` query parameters
   - Returns `has_more` flag for frontend

4. **`labeller/templates/species_classification_tree.html`**
   - Added modal CSS styles (lightbox)
   - Added modal HTML structure
   - Updated `loadReferencePhotos()` function with pagination
   - Added `openImageModal()` and `closeImageModal()` functions
   - Added state management for loaded images
   - Changed from 3 to 5 initial images

---

## ✅ Testing Checklist

- [ ] Images load (5 initially)
- [ ] "Load More" button appears
- [ ] Clicking "Load More" loads 5 more images
- [ ] Button disappears when no more images
- [ ] Clicking image opens modal
- [ ] Modal shows full-size image
- [ ] Modal shows species name
- [ ] Clicking × closes modal
- [ ] Pressing ESC closes modal
- [ ] Clicking background closes modal
- [ ] Multiple species work independently
- [ ] No errors in browser console
- [ ] No errors in Flask console

---

## 🚀 Next Steps (Optional)

**Potential Future Enhancements:**

1. **Image Navigation in Modal**:
   - Add Previous/Next buttons to browse all images without closing modal
   - Keyboard shortcuts (← / →) for navigation

2. **Image Metadata**:
   - Show image source (Wikipedia Commons URL)
   - Display image license (CC BY-SA, Public Domain, etc.)
   - Show photographer credit

3. **Performance Optimization**:
   - Lazy loading for images (load as you scroll)
   - Thumbnail preview → full resolution on click
   - Cache Wikipedia API responses

4. **Enhanced Modal**:
   - Zoom controls (zoom in/out on large images)
   - Pan/drag functionality for zoomed images
   - Fullscreen mode

---

## 📚 Key Concepts Learned

1. **API Pagination**: Using offset/limit for loading data in chunks
2. **State Management**: Tracking UI state per item (per species)
3. **Modal/Lightbox Pattern**: Full-screen overlay for content viewing
4. **Event Handling**: Multiple ways to close UI elements (button, ESC, background)
5. **Progressive Loading**: Start with small amount, load more on demand
6. **CSS Flexbox**: Centering content in modals
7. **DOM Manipulation**: Dynamically adding/removing elements

---

**Questions?** Test the features and let me know if anything needs adjustment!
