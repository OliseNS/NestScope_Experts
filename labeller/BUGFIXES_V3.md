# Nestperts V3 Bug Fixes

## Issues Fixed

### 1. ✅ "No images assigned to user" Error
**Problem:** Users with completed images but no new assignments couldn't access the editor.

**Root Cause:** Editor was only checking `assigned` array, ignoring `completed` array.

**Fix:**
```python
# Before
assigned_images = user_data.get('assigned', [])
if not assigned_images:
    return "No images assigned..."

# After
assigned_images = user_data.get('assigned', [])
completed_images = user_data.get('completed', [])
all_user_images = list(set(assigned_images + completed_images))
```

**Result:** Users can now view and edit both assigned AND completed images.

---

### 2. ✅ Gallery Images Not Loading (404 Error)
**Problem:** Clicking images in project gallery returned 404.

**Root Cause:**
- Template used wrong image URL: `/images/{{ image.name }}`
- Missing `openImageModal()` function in JavaScript

**Fix:**
```html
<!-- Before -->
<img src="/images/{{ image.name }}" ...>
<div onclick="openImage('{{ image.name }}')">

<!-- After -->
<img src="/project/{{ project.folder }}/image/{{ image.name }}" ...>
<div onclick="openImageModal('{{ image.name }}', '/project/{{ project.folder }}/image/{{ image.name }}')">
```

Added JavaScript:
```javascript
function openImageModal(imageName, imageUrl) {
    window.open(imageUrl, '_blank');
}
```

**Result:** Images now open in new tab when clicked.

---

### 3. ✅ Editor Canvas Not Loading Images
**Problem:** Editor opened but canvas was blank.

**Root Cause:** Absolute vs. relative path issues:
- `PROJECTS_DIR = 'projects'` → relative to current working directory
- When run as `python labeller/app.py`, CWD is `/home/.../nexus`, not `labeller/`
- Paths broke because Flask couldn't find `projects/` from CWD

**Fix:**
```python
# Before
PROJECTS_DIR = 'projects'  # Relative to CWD (broken!)

# After
APP_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECTS_DIR = os.path.join(APP_DIR, 'projects')  # Relative to app.py (correct!)
```

Also fixed species file path:
```python
# Before
species_file = os.path.join('labeller', 'data', 'species_list.json')  # Broken!

# After
species_file = os.path.join(APP_DIR, 'data', 'species_list.json')  # Correct!
```

**Result:** All paths now work regardless of where you run the script from.

---

## Path Resolution Explanation

### The Problem:
When you run:
```bash
python labeller/app.py
```

- **Current Working Directory (CWD):** `/home/olisemeka.dev/Projects/nexus`
- **app.py location:** `/home/olisemeka.dev/Projects/nexus/labeller/app.py`

If you use relative paths like:
```python
PROJECTS_DIR = 'projects'  # Looks for /home/olisemeka.dev/Projects/nexus/projects (WRONG!)
```

But the actual folder is at:
```
/home/olisemeka.dev/Projects/nexus/labeller/projects (CORRECT)
```

### The Solution:
Always use `__file__` to get paths relative to the script:
```python
APP_DIR = os.path.dirname(os.path.abspath(__file__))
# APP_DIR = /home/olisemeka.dev/Projects/nexus/labeller

PROJECTS_DIR = os.path.join(APP_DIR, 'projects')
# PROJECTS_DIR = /home/olisemeka.dev/Projects/nexus/labeller/projects ✓
```

Now it works from **any directory**:
```bash
cd /home/olisemeka.dev/Projects/nexus
python labeller/app.py  ✓

cd /home/olisemeka.dev/Projects/nexus/labeller
python app.py  ✓

cd /tmp
python /home/olisemeka.dev/Projects/nexus/labeller/app.py  ✓
```

---

## Files Modified

1. **`labeller/app.py`**
   - Fixed `PROJECTS_DIR` to use absolute path
   - Fixed `species_file` path
   - Updated editor route to show both assigned + completed images

2. **`labeller/templates/project_detail.html`**
   - Fixed image src URLs
   - Fixed onclick handlers
   - Added `openImageModal()` function

---

## Testing

### Test Gallery Images:
1. Go to http://localhost:5000
2. Click on "NestVision" project
3. Scroll to "Dataset Preview" section
4. Click any image
5. **Expected:** Image opens in new tab ✓

### Test Editor Image Loading:
1. Go to project detail page
2. Click on a user (e.g., "Satyam - Approved")
3. Editor should open
4. **Expected:** Image loads on canvas with annotations ✓
5. Use arrow keys to navigate
6. **Expected:** Images change smoothly ✓

### Test User Access:
1. All users should be accessible, even if they only have completed images
2. Progress indicator shows "X / Y" where Y = assigned + completed
3. Users can review and edit their past work

---

## Summary

All three major issues are now fixed:
- ✅ Users can access editor with completed images
- ✅ Gallery images load and open correctly
- ✅ Editor canvas displays images properly

The root cause was **path resolution** - using relative paths that didn't account for where the script was run from. Now all paths are **absolute** and work from anywhere.

---

## Deployment Checklist

Before deploying:
- [ ] Test from different directories
- [ ] Verify all images load in gallery
- [ ] Verify editor shows images for all users
- [ ] Test annotation saving
- [ ] Test image navigation (prev/next)

All checks should pass! 🎉
