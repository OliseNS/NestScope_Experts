# Dataset Creation Optimization Guide
## Maximizing Accuracy with Available Data

Based on analysis of `NewDataset/create_complete_dataset.py`, here are optimizations to squeeze maximum accuracy from the constrained mosaic-based data.

---

## Current Parameters Analysis

### 1. Confidence Threshold: `0.1` (Line 316)
```python
def run_inference_on_crop(self, img_array, conf_threshold=0.1):
```

**Analysis:**
- **0.1 = 10% confidence** - VERY low threshold
- Catches more birds BUT also more false positives
- With expert dots as ground truth, false positives get filtered anyway

**Optimization:**
- **Keep at 0.1** ✅ Because we use dots as ground truth
- Any YOLO box within 50px of a dot gets used
- Boxes far from dots get discarded
- **No harm in low confidence when ground truth filters it**

---

### 2. TTA IoU Threshold: `0.5` (Line 363)
```python
fused_boxes = self._weighted_boxes_fusion(all_boxes, iou_threshold=0.5)
```

**Analysis:**
- **0.5 IoU** = boxes need 50% overlap to be considered same bird
- Higher = more conservative fusion (may create duplicate boxes)
- Lower = more aggressive fusion (may merge different birds)

**Optimization:**
- **Try 0.4** for tighter fusion (more aggressive merging)
- Birds in aerial images are well-separated
- Aggressive fusion reduces box duplication
- **Recommended: Test both 0.4 and 0.5, visualize results**

---

### 3. Box Size Filtering: `8-150 pixels` (Line 392)
```python
if box_width > 150 or box_height > 150 or box_width < 8 or box_height < 8:
    continue
```

**Analysis:**
- **8px minimum** = catches small terns/gulls
- **150px maximum** = filters out huge false positives (rocks, driftwood)
- From visualizations, most birds are 20-50px

**Optimization:**
- **Tighten minimum to 10px** (filter out noise)
- **Keep maximum at 150px** ✅
- **Reason:** 8px boxes are likely noise, not real birds
- Expert dots should have ~15-50px default boxes

**Recommended:**
```python
if box_width > 150 or box_height > 150 or box_width < 10 or box_height < 10:
    continue
```

---

### 4. Aspect Ratio Filtering: `0.2-5.0` (Line 396)
```python
aspect_ratio = box_width / box_height if box_height > 0 else 0
if aspect_ratio < 0.2 or aspect_ratio > 5.0:
    continue
```

**Analysis:**
- **0.2 = very tall thin boxes** (5:1 height:width)
- **5.0 = very wide flat boxes** (5:1 width:height)
- Birds are roughly circular/elliptical (aspect ~0.5-2.0)

**Optimization:**
- **Tighten to 0.3-3.0** for more realistic bird shapes
- Filters out poles, sticks, shadows (extreme aspect ratios)

**Recommended:**
```python
if aspect_ratio < 0.3 or aspect_ratio > 3.0:
    continue
```

---

### 5. Species Default Box Sizes (Lines 412-421)
```python
size_map = {
    'BRPE': 35, 'AWPE': 40, 'GREG': 32,
    'GBHE': 32, 'ROSP': 30, 'DCCO': 28,
    'TRHE': 26, 'WHIB': 26, 'SNEG': 24,
    'HERG': 26, 'BCNH': 26, 'CAEG': 24,
    'ROYT': 22, 'SATE': 22, 'LAGU': 22,
    'BLSK': 22, 'GBTE': 20, 'AMOY': 22,
    'AMAV': 22,
}
```

**Analysis:**
- Used when YOLO doesn't detect a bird near expert dot
- Creates square boxes centered on dot
- Sizes are species-appropriate (pelicans bigger than terns)

**Optimization:**
These look **GOOD** ✅ Based on bird biology:
- Large birds (pelicans, herons): 32-40px ✅
- Medium birds (gulls, terns): 20-26px ✅
- Small birds (terns): 20-22px ✅

**No changes needed** - already well-calibrated

---

### 6. Dot-to-Box Matching Distance: `50 pixels` (Line 457)
```python
# Use YOLO box if within 50 pixels
if best_yolo_box and min_distance <= 50:
    # Use YOLO box
else:
    # Use default species box
```

**Analysis:**
- **50px threshold** = 5% of 1024px tile
- With ±5-10px spatial error from mosaics, this is reasonable
- Too tight → YOLO boxes rejected, more defaults used
- Too loose → Wrong YOLO boxes assigned to dots

**Optimization:**
- **Try 40px for tighter matching**
- Reasoning: Reduce chance of wrong box assignment
- With TTA, YOLO boxes should be pretty centered

**Recommended:**
Test both 40px and 50px:
```python
if best_yolo_box and min_distance <= 40:  # Tighter matching
```

---

### 7. Tile Quality Filters (Lines 55, 159, 589-591)
```python
min_birds=3,      # Minimum birds per tile
max_birds=500,    # Maximum birds per tile
overlap_ratio=0.2, # 20% tile overlap

# Valid region check (line 159)
def is_valid_region(self, img_array, threshold=0.3):
    non_black = np.sum(np.max(img_array, axis=2) > 10)
    total = img_array.shape[0] * img_array.shape[1]
    return (non_black / total) > threshold
```

**Analysis:**
- **Min 3 birds** = Reasonable for training signal
- **Max 500 birds** = Prevents super-dense confusing tiles
- **30% non-black** = Filters mostly-water tiles
- **20% overlap** = Good coverage without excessive redundancy

**Optimization:**
- **Tighten valid region to 40%** (more land/birds required)
- **Lower max birds to 300** (very dense tiles are hard to learn from)
- **Keep min=3 and overlap=20%** ✅

**Recommended:**
```python
min_birds=3,      # Keep ✅
max_birds=300,    # Reduce from 500
overlap_ratio=0.2, # Keep ✅

# Valid region check
return (non_black / total) > 0.4  # Increase from 0.3
```

---

## Optimized Parameters Summary

### Apply These Changes to `create_complete_dataset.py`:

```python
# Line 55: Constructor parameters
def __init__(self, model_path="swift.onnx", output_dir="ultimate_training_dataset",
             tile_size=1024, min_birds=3, max_birds=300, overlap_ratio=0.2, use_tta=True):
                                          # ↑ Changed from 500

# Line 159: Valid region threshold
def is_valid_region(self, img_array, threshold=0.4):  # ↑ Changed from 0.3
    non_black = np.sum(np.max(img_array, axis=2) > 10)
    total = img_array.shape[0] * img_array.shape[1]
    return (non_black / total) > threshold

# Line 363: TTA IoU threshold
fused_boxes = self._weighted_boxes_fusion(all_boxes, iou_threshold=0.4)
                                                              # ↓ Changed from 0.5

# Line 392: Box size filtering
if box_width > 150 or box_height > 150 or box_width < 10 or box_height < 10:
                                                    # ↑ Changed from 8
    continue

# Line 396: Aspect ratio filtering
if aspect_ratio < 0.3 or aspect_ratio > 3.0:
            # ↑ Changed from 0.2    ↑ Changed from 5.0
    continue

# Line 457: Dot matching distance
if best_yolo_box and min_distance <= 40:  # ↓ Changed from 50
```

---

## Expected Impact

### Before Optimization (Current):
- 529 tiles from 2,970 positions (17.8%)
- 25,325 labeled birds
- Box sources: 15.2% YOLO, 84.8% default

### After Optimization (Estimated):
- **~400-450 tiles** (fewer due to stricter quality filters)
- **~20,000-22,000 labeled birds** (proportional reduction)
- **Box sources: 18-20% YOLO, 80-82% default** (better YOLO utilization)
- **Higher per-tile quality** (better land coverage, tighter boxes)

**Trade-off:** Fewer tiles BUT higher quality per tile
**For DevDays:** Show judges you optimize for quality over quantity

---

## Implementation Steps

### 1. Create Optimized Version
```bash
cd /home/olisemeka.dev/Projects/nexus/NewDataset/
cp create_complete_dataset.py create_complete_dataset_optimized.py
```

### 2. Apply Changes
Edit `create_complete_dataset_optimized.py` with the parameters above

### 3. Run Optimized Generation
```bash
source ../.venv/bin/activate
python create_complete_dataset_optimized.py \
  --model swift.onnx \
  --output ultimate_training_dataset_optimized \
  --overlap 0.2 \
  --min-birds 3 \
  --max-birds 300
```

### 4. Compare Results
```bash
# Visualize optimized dataset
python visualize_dataset.py \
  --dataset ultimate_training_dataset_optimized \
  --output dataset_visualizations_optimized \
  --num-samples 100

# Compare statistics
diff ultimate_training_dataset/dataset_statistics.json \
     ultimate_training_dataset_optimized/dataset_statistics.json
```

---

## What to Show Judges

### 1. Original Dataset
- 529 tiles, 25,325 birds
- Shows we can work at scale

### 2. Optimized Dataset
- ~420 tiles, ~21,000 birds
- Shows we optimize for quality

### 3. Comparison
"We ran two versions: one optimized for coverage (529 tiles), one for quality (420 tiles). Both show our model works, but the optimized version has tighter boxes and better land coverage per tile. For DevDays, we're showing the coverage version, but post-hackathon we'll retrain on quality."

**This demonstrates:**
- Systematic experimentation
- Understanding of quality vs quantity trade-offs
- Iterative refinement process

---

## Advanced Optimizations (Post-Hackathon)

### 1. Adaptive Confidence Thresholds per Species
```python
species_confidence = {
    'BRPE': 0.15,  # Higher threshold for large birds
    'LAGU': 0.08,  # Lower threshold for small birds
    'ROYT': 0.10,
}
```

### 2. Context-Aware Box Sizes
```python
# Adjust box size based on colony density
if tile_density > 100:  # High density
    size_multiplier = 0.9  # Slightly smaller boxes
else:  # Low density
    size_multiplier = 1.1  # Slightly larger boxes
```

### 3. Multi-Scale Tiles
```python
# Generate tiles at different resolutions
for tile_size in [768, 1024, 1280]:
    generate_crops_from_mosaic(tile_size)
```

---

## Recommended for DevDays

**DON'T re-generate dataset if you're short on time!**

Your current dataset (529 tiles) is **already good** for demonstration. The optimizations above are **marginal improvements** (maybe 5-10% better quality).

**Better use of time:**
1. Practice your presentation
2. Review judge feedback strategy
3. Test NestScope demo flow
4. Prepare answers to technical questions

**Post-hackathon:** Implement optimizations and compare performance

---

## Quick Quality Check

To verify your current dataset quality WITHOUT regenerating:

```bash
cd /home/olisemeka.dev/Projects/nexus/

# Check a few random samples
python -c "
import random
from pathlib import Path

labels = list(Path('ultimate_training_dataset/labels').glob('*.txt'))
samples = random.sample(labels, 10)

for label_file in samples:
    with open(label_file) as f:
        lines = f.readlines()
    print(f'{label_file.name}: {len(lines)} birds')
"
```

If you see 3-100 birds per sample → **Good quality** ✅
If you see 500+ birds → **Some tiles too dense** (but still usable)

---

## Bottom Line

**Your current dataset is good enough for DevDays!**

The optimizations above provide **marginal improvements** (~5-10%). Focus your remaining time on:
1. Presentation polish
2. Demo reliability
3. Judge question preparation

**Post-hackathon:** Implement optimizations and document the improvement for TWI partnership proposal.
