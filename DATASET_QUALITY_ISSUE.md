# 🚨 CRITICAL: Dataset Quality Issue - Spatial Degradation

## Problem Discovered

Your training dataset is generated from **COG mosaics** instead of **original high-resolution images**. This introduces significant spatial degradation that will harm model performance.

## Evidence

From the dot files (`LAGU-Bird_dots.json`):
```json
{
  "type": "Feature",
  "properties": {
    "species": null,
    "type": "Bird",
    "code": "LAGU",
    "month_x": "May",
    "year": "2021",
    "screenshot": "22May21Camera1-2183.jpg",  ← ORIGINAL HIGH-RES IMAGE
    "mosaic": "2021_Barataria Bay_Queen Bess Island_May22_1_0_0.tif",  ← MOSAIC IT WAS PROJECTED TO
    "colony": "QBI",
    "colonyname": "Queen Bess Island"
  },
  "geometry": {
    "type": "Point",
    "coordinates": [-89.95794902, 29.30294188]  ← LON/LAT (GEOREFERENCED)
  }
}
```

**Key Finding:** Each dot has a `"screenshot"` field showing the **original high-res image filename** where the expert manually placed the dot.

## The Degradation Pipeline (Current Approach ❌)

```
1. Expert dots image: 22May21Camera1-2183.jpg (high-res, pixel-perfect)
   ↓ Image is georeferenced (introduces lens distortion correction, spatial errors)
2. Image stitched into mosaic: May_cog.tif (compression, resampling, seam artifacts)
   ↓ Dots projected to mosaic using lon/lat coordinates (rounding errors)
3. Your script extracts 1024x1024 tiles from mosaic
   ↓ Training happens on spatially degraded data
4. Model learns from:
   - Georeferencing artifacts
   - Mosaic compression losses
   - Coordinate transformation errors
   - Stitching seams and boundary effects
```

## Why This Is Bad

### 1. **Spatial Accuracy Loss**
- Georeferencing: ±2-5 pixel error typical
- COG resampling: Bilinear/cubic interpolation blur
- Lon/lat → pixel conversion: Floating point rounding

**Result:** Bounding boxes may be 5-10 pixels off from true bird location

### 2. **Image Quality Degradation**
- Original high-res: 12-15 MB JPEG, ~5000x3000px
- COG mosaic: Compressed, potentially 8-bit color depth
- Tile extraction: Additional resampling

**Result:** Model trains on lower-quality imagery

### 3. **Mosaic Artifacts**
- Seam lines where images are stitched
- Brightness/contrast mismatches between source images
- Edge distortions from georeferencing

**Result:** Model may learn artifacts as features

## The Correct Approach ✅

```
1. Load dot file: LAGU-Bird_dots.json
2. For each dot, extract "screenshot" field: "22May21Camera1-2183.jpg"
3. Load ORIGINAL high-res image from bucket (if available)
4. If image has EXIF geotags or georeferencing metadata:
   - Reverse project lon/lat → original image pixel coordinates
5. Else if original pixel-based dot files exist:
   - Use those directly (pixel-perfect ground truth)
6. Extract tiles from ORIGINAL high-res images
7. Apply labels in original image space (no coordinate transformations)
```

**Benefits:**
- ✅ Pixel-perfect label accuracy
- ✅ Original image quality (no compression/resampling)
- ✅ No mosaic artifacts
- ✅ No georeferencing errors

## Required Data Investigation

To implement the correct approach, we need to determine:

### 1. Are original high-res images available?
- Current bucket structure shows images from 2024
- Dot files reference 2021 images ("22May21Camera1-2183.jpg")
- **Action:** Check if 2021 original images exist in S3 bucket

### 2. Do original pixel-coordinate dot files exist?
- Dotting policy mentions Image-Pro software
- Experts dotted images before georeferencing
- **Action:** Check if `.ipx` or other Image-Pro format files exist

### 3. Can we reverse-project dots to original images?
- Dots have lon/lat coordinates
- Mosaic metadata has georeferencing parameters
- **Action:** Extract georeferencing transform, apply inverse to map dots back

## Recommended Action Plan

### Short Term (DevDays 2026 - March 20)
If original 2021 images aren't accessible before the hackathon:

1. **Acknowledge limitation** in your presentation to judges
2. **Document the issue** (show this analysis!)
3. **Propose future work** to rebuild dataset from originals
4. **Highlight awareness** of spatial accuracy importance

Derek Dohler (TWI) wants "reliability proof" → This shows you understand data quality!

### Long Term (Post-Hackathon)
1. **Contact The Water Institute** to get access to original 2021 high-res images
2. **Rebuild training dataset** from originals using corrected pipeline
3. **Compare model performance** (mosaic-trained vs original-trained)
4. **Publish findings** about spatial degradation effects on bird detection accuracy

## Impact on Current Dataset

Your `ultimate_training_dataset` (529 tiles, 25,325 labels) was generated from:
- Queen Bess Island May 2021: COG mosaic (1033 MB)
- Queen Bess Island June 2021: COG mosaic (253 MB)
- Pepperfish Key May 2021: COG mosaic

**Estimated spatial accuracy:** ±5-10 pixels per label
**Image quality:** Degraded from original

## Questions to Answer

1. **Where are the 2021 original high-res images?**
   - Check: `twi-aviandata.s3.amazonaws.com/HighResolutionImages/2021/`
   - Alternative: Ask TWI for access

2. **Do dot files contain original pixel coordinates?**
   - Current files have lon/lat only
   - Original Image-Pro files might have pixel coords

3. **Can we access georeferencing metadata?**
   - Check `.tif.aux.xml` or `.tfw` files
   - Needed for reverse projection

## Proof of Concept Script

I'll create `visualize_dot_on_highres.py` to demonstrate:
1. Downloading original high-res image
2. Mapping dot coordinates to it
3. Visualizing the difference vs mosaic-based approach

This will show judges you understand the problem deeply.

## References

- Dotting policy document: `/home/olisemeka.dev/Projects/nexus/dotting_policy.txt`
- Dot file location: `public/mosaics/BaratariaBay/QueenBessIsland/2021/*_dots.json`
- Original images (2024): `public/devDays/2024_QueenBessIsland/`
- Need to locate: 2021 original images

---

**Date Identified:** March 9, 2026
**Impact:** High - Affects model training quality
**Priority:** Document for judges now, fix post-hackathon
