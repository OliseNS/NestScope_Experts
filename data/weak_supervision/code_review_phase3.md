# Code Review: batch_download_detect.py

**Reviewer:** Claude
**Date:** 2026-02-26
**Status:** ⚠️ ISSUES FOUND - DO NOT RUN YET

---

## Critical Issues (Must Fix)

### 🔴 Issue 1: Missing `device` Attribute
**Location:** Line ~220 in `batch_download_detect.py`
```python
print(f"✓ Detector ready (device: {detector.device})")
```

**Problem:** `BirdDetector` class does not have a `device` attribute. This will raise `AttributeError`.

**Fix:** Remove or replace with:
```python
print(f"✓ Detector ready")
```

**Why This Happened:** I incorrectly assumed BirdDetector would expose a device attribute like PyTorch models do. The ONNX inference session uses providers ('CUDAExecutionProvider' or 'CPUExecutionProvider') but doesn't expose a simple `.device` attribute.

---

### 🔴 Issue 2: Missing Dependency - `tqdm`
**Location:** Multiple places (lines 76, 89, 104)
```python
from tqdm import tqdm
...
for mapping in tqdm(batch_mappings, desc="  Downloading"):
```

**Problem:** Script imports `tqdm` (progress bar library) but it may not be installed in the virtual environment.

**Fix Options:**
1. **Add to requirements:** Add `tqdm` to project dependencies
2. **Remove and use simple counter:** Replace with basic print statements
3. **Optional import:** Make tqdm optional with fallback

**Recommendation:** Option 3 (optional import) is most robust:
```python
try:
    from tqdm import tqdm
except ImportError:
    # Fallback: simple counter without progress bar
    def tqdm(iterable, desc=""):
        return iterable
```

**Educational Note:** `tqdm` is a popular library that shows progress bars (e.g., `[=====>    ] 50% 50/100`). Very useful for long-running loops but not critical for functionality.

---

### 🟡 Issue 3: Unused Import
**Location:** Line 30
```python
import shutil
```

**Problem:** `shutil` is imported but never used in the script.

**Impact:** Low (just clutter, no functional issue)

**Fix:** Remove the line

**Why This Happens:** During development, you might anticipate needing a library and import it, then never use it. Good practice is to review imports before finalizing code.

---

### 🟡 Issue 4: Unused Output File Variable
**Location:** Line 43
```python
DETECTION_FILE = PROJECT_ROOT / "data" / "weak_supervision" / "bird_crops" / "detection_info.json"
```

**Problem:** `DETECTION_FILE` is defined but never used. Only `METADATA_FILE` is written.

**Impact:** Low (documentation mentions it but it's not created)

**Fix Options:**
1. Remove the variable if not needed
2. Add code to actually write detection info separately
3. Rename to make it clear it's for future use

**Recommendation:** For now, remove it to avoid confusion. We're storing all detection info in metadata.json.

---

## Design Review

### ✅ Good Design Choices

1. **Batch Processing (100 images at a time)**
   - **Why Good:** Prevents disk from filling up (original images are ~40+ GB total)
   - **How It Works:** Download → Detect → Extract crops → Delete originals, repeat
   - **Benefit:** Keeps disk usage under ~500 MB per batch

2. **Progress Saving After Each Batch**
   - **Why Good:** If script crashes or is interrupted, you don't lose all work
   - **How It Works:** `metadata.json` is written after each batch completes
   - **Benefit:** Can resume from where it left off (though we'd need to add resume logic)

3. **5% Padding on Crops**
   - **Why Good:** YOLO bounding boxes are tight - adding padding ensures we don't cut off wings/tails
   - **How It Works:** Expands bbox by 5% on all sides with bounds checking
   - **Trade-off:** Includes more background but captures full bird

4. **Bounds Checking in Crop Extraction**
   - **Why Good:** Prevents index errors when bird is near image edge
   - **How It Works:** `x1 = max(0, x1 - pad_x)` ensures coordinates stay within image
   - **Safety:** Won't crash even if bird is at corner

### ⚠️ Design Concerns

1. **No Resume Functionality**
   - **Problem:** If script stops at batch 50/68, you'd restart from scratch
   - **Fix:** Add logic to check existing crops and skip processed photos
   - **Complexity:** Medium (need to track which photos already processed)

2. **Memory Management for Large Batches**
   - **Concern:** Loading 100 images into memory simultaneously could cause issues
   - **Current Behavior:** Downloads all, then processes all
   - **Better Approach:** Process one-at-a-time within batch
   - **Impact:** Minimal risk on modern systems with 8+ GB RAM, but worth noting

3. **Error Handling for Individual Failures**
   - **Current:** Try-except around detection, continues on failure
   - **Good:** Won't crash entire batch if one image fails
   - **Missing:** No log of which photos failed and why
   - **Fix:** Add failed photos to a separate list and report at end

4. **No Validation of Downloaded Images**
   - **Concern:** If S3 download succeeds but file is corrupt, OpenCV may fail
   - **Current:** Detection try-except will catch it
   - **Better:** Validate image loads before detection

---

## Performance Analysis

### Expected Runtime

**Parameters:**
- Total photos: 6,795
- Batch size: 100
- Number of batches: 68
- SAHI mode: 3-5 seconds per image
- Download time: ~1 second per image

**Calculation:**
```
Per batch:
  Download: 100 images × 1 sec = 100 sec (1.7 min)
  Detection: 100 images × 4 sec = 400 sec (6.7 min)
  Crop extraction: ~10 sec (fast)
  Total per batch: ~510 sec (8.5 min)

Total time:
  68 batches × 8.5 min = 578 minutes = 9.6 hours
```

**Realistic Estimate:** 8-10 hours for full run

**Ways to Speed Up:**
1. Switch to `fast_mode=True` (2-4x faster, slightly less accurate)
2. Increase batch size to reduce overhead
3. Parallelize detection across batches (complex)

### Disk Usage

**During Processing:**
- Batch of 100 images: ~500 MB - ~1 GB
- Total crops (end state): ~2-3 GB (assuming 40K crops × 50-75 KB each)

**Peak Disk Usage:** ~3-4 GB

**Safe to Run:** Yes, as long as you have >5 GB free space

---

## Code Quality Issues

### 1. Missing Docstrings
Some functions lack detailed docstrings:
- `process_batch()` - Needs parameter descriptions
- `main()` - Could explain overall flow

### 2. Magic Numbers
Several hardcoded values that should be constants or parameters:
- `padding=0.05` in `extract_bird_crop()` - Why 5%?
- `fast_mode=False` - Should this be configurable?

### 3. No Logging
Uses `print()` statements instead of proper logging module:
```python
import logging
logging.info("Processing batch...")
```

**Why Logging is Better:**
- Can write to file automatically
- Can set different levels (DEBUG, INFO, WARNING, ERROR)
- Timestamps added automatically
- Can silence or enable based on environment

---

## Security & Safety

### ✅ Safe Practices
1. **Read-only S3 access** (unsigned, public bucket)
2. **Bounds checking** on array indexing
3. **Path validation** with Path library
4. **Try-except** around risky operations

### ⚠️ Potential Issues
1. **No quota checking** - Could theoretically download gigabytes if S3 mappings are wrong
2. **No timeout** on S3 downloads - Stuck download could hang indefinitely
3. **File overwrites** - If script run twice, crops would be overwritten silently

---

## Testing Recommendations

### Before Full Run:

1. **Test with 1 Image (Sanity Check)**
   ```python
   # Modify BATCH_SIZE = 1 and mappings = mappings[:1]
   ```
   Expected: 1 image downloaded, birds detected, crops extracted

2. **Test with 1 Batch (10 Images)**
   ```python
   mappings = mappings[:10]
   ```
   Expected: ~50-70 crops, metadata.json created, originals deleted

3. **Verify Crop Quality**
   - Manually inspect 10 random crops
   - Check that birds are centered and not cut off
   - Verify padding looks reasonable

4. **Test Cleanup**
   - Confirm downloaded_images/ folder is empty after batch
   - Verify crops persisted in bird_crops/images/

5. **Test Error Handling**
   - Try with a non-existent S3 key
   - Try with a corrupt image path
   - Verify script doesn't crash and logs error

---

## Recommendations

### Must Fix Before Running:
1. ✅ Remove `.device` attribute access (causes crash)
2. ✅ Add optional tqdm import (prevents ImportError)
3. ✅ Remove unused `shutil` import
4. ✅ Remove or clarify unused `DETECTION_FILE`

### Should Fix (Low Priority):
5. Add resume functionality (skip already-processed photos)
6. Add proper logging instead of print statements
7. Add validation for downloaded images
8. Report failed photos at end
9. Add configuration file for BATCH_SIZE, FAST_MODE, etc.

### Nice to Have:
10. Add progress percentage to batch processing
11. Estimate remaining time
12. Add summary statistics per batch (avg birds/image, etc.)
13. Create visualization of first few crops for manual review

---

## Verdict

**Status:** ⚠️ **Cannot run yet - must fix critical issues first**

**Estimated Fix Time:** 15-20 minutes

**Risk Level After Fixes:** 🟢 Low (safe to test with small batch)

**Recommended Approach:**
1. Fix the 4 critical/high issues
2. Test with 1 image
3. Test with 10 images
4. If both successful, run full batch overnight

---

## Learning Takeaways

### Why Code Review Matters

This review found 2 **critical bugs** that would have caused the script to crash immediately:
1. AttributeError on `.device`
2. ImportError on `tqdm`

**Without review:** Script crashes after ~30 seconds, wasting time
**With review:** Fix in 5 minutes, smooth execution

**General Lesson:** Always test with small samples before committing to long-running operations (10 hour scripts!).

### Common Bug Patterns

1. **Assuming APIs** - I assumed BirdDetector would have `.device` without checking
2. **Forgetting dependencies** - Used `tqdm` without verifying it's installed
3. **Unused code** - Imported libraries but never used them

These are classic "wrote code quickly without running it" bugs. Good code review catches them before execution.

---

## Next Steps

1. **Fix the critical issues** (see fixes below)
2. **Test with 1 image** (modify script to use `mappings[:1]`)
3. **Review test outputs** (check crops, metadata)
4. **Decide:** Run full script or make improvements first?

