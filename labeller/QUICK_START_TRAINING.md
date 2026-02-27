# Quick Start: Training Your Nano Bird Detection Model

## 🚀 Ready to Train? Use This!

### Option 1: Use Improved Script (Recommended)

```bash
cd /home/olisemeka.dev/Projects/nexus/labeller
../.venv/bin/python nanotrain_improved.py
```

**What it does:**
- ✅ Auto-detects GPU/CPU
- ✅ Uses correct batch size for your dataset (32 instead of 64)
- ✅ Proper multi-scale training
- ✅ Optimized augmentations for aerial imagery
- ✅ Better error handling

### Option 2: Fix Original Script

If you prefer to fix your original `nanotrain.py`, make these changes:

```python
# CHANGE 1: Reduce batch size
batch=32,  # Changed from 64 (better for 469 training images)

# CHANGE 2: Fix multi_scale
multi_scale=True,  # Changed from 0.2 (should be boolean)

# CHANGE 3: Use absolute path
from pathlib import Path
script_dir = Path(__file__).parent
data=str(script_dir / "donesplit/data.yaml"),  # Instead of "donesplit/data.yaml"
```

## 📊 What to Expect

| Stage | Time | What Happens |
|-------|------|--------------|
| Setup | 1-2 min | Downloads model, loads dataset |
| Training | 1-2 hours | 80-150 epochs (early stopping) |
| Validation | Auto | Runs every epoch |
| Saving | Auto | Checkpoints every 10 epochs |

## 🎯 Success Metrics

Watch these in the training output:

| Metric | Good | Excellent | What It Means |
|--------|------|-----------|---------------|
| **mAP50** | >0.60 | >0.80 | Detection accuracy at 50% IoU |
| **mAP50-95** | >0.40 | >0.60 | Stricter accuracy metric |
| **Precision** | >0.70 | >0.85 | How many detections are correct |
| **Recall** | >0.70 | >0.85 | How many birds are found |

## 📁 Output Structure

After training, you'll have:

```
labeller/nestvision_runs/yolo26n_nano_1024/
├── weights/
│   ├── best.pt          ← 🏆 USE THIS ONE!
│   └── last.pt          ← Last epoch (not always best)
├── results.csv          ← All metrics per epoch
├── results.png          ← Training curves graph
├── confusion_matrix.png ← Detection quality
├── val_batch0_pred.jpg  ← Validation predictions
└── args.yaml            ← Training config used
```

## ⚡ After Training

### Step 1: Convert to ONNX

```bash
cd /home/olisemeka.dev/Projects/nexus
.venv/bin/python convert_to_onnx.py \
  --model labeller/nestvision_runs/yolo26n_nano_1024/weights/best.pt \
  --output models/nano_trained.onnx \
  --imgsz 1024
```

### Step 2: Update Config

Edit `server/config.yaml`:
```yaml
cv:
  model_path: models/nano_trained.onnx  # Your new model!
```

### Step 3: Test It

```bash
.venv/bin/python test_nano_inference.py
```

You should see individual birds detected (not colony regions)!

## 🐛 Troubleshooting

### "CUDA out of memory"

Reduce batch size:
```python
batch=16,  # Or even 8
```

### "No improvement in validation"

- Check if validation set is too small (32 images)
- Verify labels are correct in `labeller/donesplit/labels/val/`
- Try longer training: `patience=75`

### "Model not learning (loss not decreasing)"

- Reduce learning rate: `lr0=0.0005`
- Check data.yaml paths are correct
- Verify labels match images (same filenames)

### "Training very slow"

Running on CPU? Training on CPU takes 10-20x longer:
```
⚠️  WARNING: Training on CPU will be VERY slow!
```

Consider using Google Colab with GPU or cloud GPU instance.

## 🎓 Understanding Training Output

### Example output:
```
Epoch   GPU_mem   box_loss   cls_loss   dfl_loss   Instances   Size
1/150    1.2G      1.234      0.876      1.567      128        1024
```

- **Epoch**: Current epoch / total
- **GPU_mem**: VRAM usage
- **box_loss**: Bounding box accuracy (should decrease)
- **cls_loss**: Classification loss (low for 1-class)
- **dfl_loss**: Distribution focal loss (should decrease)
- **Instances**: Number of birds in batch
- **Size**: Image size

### What "good" training looks like:

```
Epoch 1:  box_loss=1.234  cls_loss=0.876  ✓ Starting high
Epoch 20: box_loss=0.845  cls_loss=0.432  ✓ Decreasing
Epoch 50: box_loss=0.456  cls_loss=0.234  ✓ Still improving
Epoch 80: box_loss=0.423  cls_loss=0.221  ✓ Plateauing (good!)
```

## 💡 Pro Tips

### 1. Monitor with TensorBoard (Optional)

```bash
pip install tensorboard
tensorboard --logdir labeller/nestvision_runs
# Open http://localhost:6006
```

### 2. Compare Multiple Runs

The script won't overwrite - it creates run1, run2, etc:
```
nestvision_runs/
├── yolo26n_nano_1024/       ← First run
├── yolo26n_nano_1024_2/     ← Second run
└── yolo26n_nano_1024_3/     ← Third run
```

### 3. Resume Interrupted Training

```python
model = YOLO("labeller/nestvision_runs/yolo26n_nano_1024/weights/last.pt")
model.train(resume=True)  # Continues from last checkpoint
```

### 4. Hyperparameter Tuning

Try different values:
```python
# More aggressive augmentation
degrees=360.0,   # Full rotation
mosaic=1.0,      # Always use mosaic

# Or less aggressive
degrees=90.0,    # Limited rotation
mosaic=0.5,      # 50% mosaic
```

## 🎯 Goal

Your nano model should:
- ✅ Detect **individual birds** (not colonies)
- ✅ Have **similar accuracy** to seconditer.onnx (~70-80% mAP)
- ✅ Be **much faster** (nano is 3-5x faster than larger models)
- ✅ Work with the **existing inference code** (format auto-detection!)

Good luck with training! 🚀🐦
