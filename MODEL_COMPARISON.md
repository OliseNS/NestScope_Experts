# Model Comparison Report

## Issue Summary

The `nano1024.onnx` model was drawing "random boxes" because it was trained for a **different detection task** than expected.

## Test Results

Tested on image: `server/cv_tools/images/15May2022_Cam1Card1_1027.jpg`

| Model | Output Format | Detections | Detection Type | Box Size | Inference Time |
|-------|---------------|------------|----------------|----------|----------------|
| **seconditer.onnx** | `[1, 5, 21504]` | 84 | Individual birds | 60-70px | 1.4s |
| **nano1024.onnx** | `[1, 300, 6]` | 4 | Colony regions | 3000-4000px | 0.4s |

## Key Differences

### seconditer.onnx (Individual Bird Detection)
✓ **Use this for:** Counting individual birds
✓ **Detections:** Each bird gets its own bounding box
✓ **Box size:** ~60-70 pixels per bird
✓ **Accuracy:** High confidence (0.6-0.7)
✗ **Speed:** Slower (1.4s)

**Example detection:**
```
bbox=[4010.8, 3011.0, 4074.3, 3091.6]
size=63.5x80.7px
conf=0.689
```

### nano1024.onnx (Colony Region Detection)
✓ **Use this for:** Identifying nesting areas/colonies
✓ **Speed:** Much faster (0.4s)
✗ **Detections:** Detects large regions, not individual birds
✗ **Box size:** Covers thousands of pixels
✗ **Accuracy:** Lower confidence (0.3-0.5)

**Example detection:**
```
bbox=[1583.9, 614.9, 4949.8, 3843.9]
size=3365.9x3229.0px (HUGE!)
conf=0.463
```

## Root Cause: Different Training Data

The models were trained on different annotation types:

- **seconditer**: Trained with individual bird bounding boxes
- **nano1024**: Likely trained with colony-level annotations or different dataset

## Solutions

### ✅ Current Fix (Applied)

Switched `server/config.yaml` back to `seconditer.onnx`:

```yaml
cv:
  model_path: models/seconditer.onnx  # Individual bird detection
```

### Option 2: Retrain nano1024

To make nano1024 detect individual birds:

1. Use training data with individual bird annotations
2. Check `labeller/nestvision/` for proper annotation format
3. Retrain using the VisionTrain pipeline
4. Convert to ONNX: `python convert_to_onnx.py --model models/new_model.pt`

### Option 3: Keep Both Models

Add a detection mode parameter to switch between models based on use case:

```python
# In server/main.py or frontend
detection_mode = "individual"  # or "colony"
model_path = "seconditer.onnx" if detection_mode == "individual" else "nano1024.onnx"
```

## Technical Fix Applied

Updated `server/cv_tools/inference.py` to automatically detect output format:

```python
def _load_model(self):
    # Detect output format by checking shape
    output_shape = self.model.get_outputs()[0].shape
    if len(output_shape) == 3 and output_shape[2] == 6:
        self.output_format = 'max_det'  # [batch, num_detections, 6]
    else:
        self.output_format = 'standard'  # [batch, classes, anchors]
```

Added separate postprocessing functions:
- `_postprocess_max_det_format()` for nano1024 format
- `_postprocess_standard_format()` for seconditer format
- `_postprocess()` router that picks the correct function

## Recommendation

**For counting individual birds:** Use `seconditer.onnx` (current setting ✓)

**For fast colony detection:** Consider training a dedicated colony detection model if needed

## Conversion Script

The `convert_to_onnx.py` script works for any YOLO model:

```bash
.venv/bin/python convert_to_onnx.py --model models/your_model.pt --imgsz 1024
```

This creates `models/your_model.onnx` automatically.
