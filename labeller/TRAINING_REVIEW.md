# Training Script Review & Improvements

## Dataset Analysis

**Location:** `labeller/donesplit/`

| Metric | Value | Notes |
|--------|-------|-------|
| Total Images | 501 | Small dataset - requires careful hyperparameters |
| Training Set | 469 images (93.2%) | Good for training |
| Validation Set | 32 images (6.8%) | ⚠️ Small but acceptable |
| Classes | 1 (bird) | Single-class detection |
| Image Size | 1024x1024 | High-res for small objects ✓ |

## Critical Issues in Original Script

### 🔴 Issue 1: Batch Size Too Large

**Original:**
```python
batch=64  # Taking advantage of your 80GB VRAM
```

**Problem:**
- With only **469 training images**, batch=64 means:
  - Only **7 batches per epoch** (469 ÷ 64 = 7.3)
  - Model sees very few gradient updates per epoch
  - Training becomes unstable and inefficient

**Fixed:**
```python
batch=32  # For 469 images: 32 batches = ~15 batches/epoch
```

**Why this matters:**
- More gradient updates per epoch = better learning
- Rule of thumb: `num_batches_per_epoch = training_images / batch_size` should be 10-50
- With batch=32: 469 ÷ 32 = **14.6 batches/epoch** ✓

### 🔴 Issue 2: Multi-Scale Value Incorrect

**Original:**
```python
multi_scale=.2  # Wrong type!
```

**Problem:**
- `multi_scale` should be **boolean** (True/False), not a float
- The value 0.2 gets interpreted as False (any non-zero = True in Python, but YOLO expects bool)
- This might work but is confusing and not documented behavior

**Fixed:**
```python
multi_scale=True  # Enable multi-scale training (±50% scaling)
```

**Why this matters:**
- Multi-scale training helps the model handle different altitudes/zoom levels
- Essential for aerial imagery where altitude varies

### ⚠️ Issue 3: Relative Path Without Context

**Original:**
```python
data="donesplit/data.yaml"
```

**Problem:**
- Relative paths break if you run the script from a different directory
- Example: Running from project root vs labeller/ folder gives different results

**Fixed:**
```python
script_dir = Path(__file__).parent
data_yaml = script_dir / "donesplit" / "data.yaml"
data=str(data_yaml)  # Absolute path
```

**Why this matters:**
- Script works consistently regardless of where you run it from
- Prevents confusing "file not found" errors

### ⚠️ Issue 4: Missing Model Fallback

**Original:**
```python
model = YOLO("yolo26n.pt")  # What if this file doesn't exist?
```

**Problem:**
- If `yolo26n.pt` doesn't exist, Ultralytics tries to download it
- But if YOLO26 isn't available in their model zoo, training fails
- No fallback option

**Fixed:**
```python
try:
    model = YOLO("yolo26n.pt")
except Exception as e:
    print(f"⚠️  Could not load yolo26n.pt: {e}")
    model = YOLO("yolov8n.pt")  # Fallback to standard YOLOv8 Nano
```

**Why this matters:**
- YOLO26 might be a custom/newer version not in the official model zoo
- YOLOv8n is a proven alternative with similar architecture

### ℹ️ Issue 5: Small Validation Set

**Current:**
- 32 validation images (6.8%)

**Impact:**
- Small validation set means validation metrics are less reliable
- One bad prediction affects metrics by 3% (1/32)

**Recommendation:**
- Ideally 10-20% validation split (50-100 images)
- Consider re-splitting if possible

**To re-split:**
```bash
cd labeller
python train_test_split.py --val-ratio 0.15  # 15% validation
```

## Additional Improvements Made

### 1. **Auto-Detect Device**
```python
device = "0" if torch.cuda.is_available() else "cpu"
```
- Automatically uses GPU if available
- Falls back to CPU with warning

### 2. **Added Important Hyperparameters**

**Learning Rate Schedule:**
```python
lr0=0.001          # Initial learning rate
lrf=0.01           # Final LR = 0.001 × 0.01 = 0.00001
warmup_epochs=3.0  # Gradually increase LR over first 3 epochs
```

**HSV Augmentations:**
```python
hsv_h=0.015  # Lighting variations
hsv_s=0.7    # Weather/time-of-day changes
hsv_v=0.4    # Brightness variations
```
These simulate different lighting conditions in aerial photography.

**Loss Weights:**
```python
box=7.5  # Bounding box loss
cls=0.5  # Classification loss (low because only 1 class)
dfl=1.5  # Distribution Focal Loss
```

### 3. **Disabled Inappropriate Augmentations**

```python
mixup=0.0        # Blending images doesn't make sense for aerial
copy_paste=0.0   # Not ideal for bird detection
```

### 4. **Added Close Mosaic**

```python
close_mosaic=10  # Disable mosaic augmentation for last 10 epochs
```
- Allows fine-tuning on real images (no augmentation) at the end
- Improves final model accuracy

### 5. **Better Logging**

```python
exist_ok=False   # Creates run1, run2, etc. instead of overwriting
verbose=True     # Detailed training info
```

## Comparison Summary

| Parameter | Original | Improved | Impact |
|-----------|----------|----------|--------|
| `batch` | 64 | 32 | 🔴 Critical - prevents unstable training |
| `multi_scale` | 0.2 (float) | True (bool) | 🔴 Critical - wrong type |
| `data` | Relative path | Absolute path | ⚠️ Important - prevents errors |
| `model` | No fallback | Try/except | ⚠️ Important - better robustness |
| `lr0` | Not set | 0.001 | ℹ️ Good practice |
| `hsv_*` | Not set | Added | ℹ️ Better generalization |
| `close_mosaic` | Not set | 10 | ℹ️ Better final accuracy |
| `mixup/copy_paste` | Not set | Disabled | ℹ️ Cleaner augmentation |

## Expected Training Time

With your setup (80GB GPU):
- **Per Epoch:** ~30-60 seconds (depends on GPU model)
- **Total Training:** 1-2 hours (with early stopping, likely 80-100 epochs)
- **With Patience=50:** May finish around epoch 80-100 if validation stops improving

## How to Run

```bash
cd /home/olisemeka.dev/Projects/nexus/labeller
.venv/bin/python nanotrain_improved.py
```

## After Training

1. **Find best model:**
   ```
   labeller/nestvision_runs/yolo26n_nano_1024/weights/best.pt
   ```

2. **Convert to ONNX:**
   ```bash
   cd /home/olisemeka.dev/Projects/nexus
   .venv/bin/python convert_to_onnx.py \
     --model labeller/nestvision_runs/yolo26n_nano_1024/weights/best.pt \
     --imgsz 1024
   ```

3. **Update config to use new model:**
   ```yaml
   # server/config.yaml
   cv:
     model_path: models/best.onnx  # Your newly trained model
   ```

4. **Test inference:**
   ```bash
   .venv/bin/python test_nano_inference.py
   ```

## Recommendations

### 1. **Increase Validation Split** (Optional but Recommended)
Current 6.8% validation is small. Consider 15%:
```bash
cd labeller
python train_test_split.py --val-ratio 0.15
```

### 2. **Monitor Training**
Watch for:
- **Validation mAP50** - should reach 0.7+ (70%+) for good model
- **Loss curves** - should steadily decrease
- **Overfitting** - if train loss << val loss, reduce augmentation

### 3. **Try Different Architectures**
If nano is too small:
```python
model = YOLO("yolov8s.pt")  # Small (2x params)
model = YOLO("yolov8m.pt")  # Medium (5x params)
```

### 4. **Data Quality > Quantity**
With 501 images, quality matters more than quantity:
- ✓ Clean, accurate bounding boxes
- ✓ Varied conditions (lighting, altitude, bird poses)
- ✓ No mislabeled images

Use Nestperts to refine annotations if needed!
