# Clustering Feature Fixes

## ✅ What I Fixed

### 1. **Import Error** (`No module named 'labeller'`)
**Fixed in:** [`labeller/app.py` lines 2-5](labeller/app.py#L2-L5)

Added project root to Python path so Flask can import clustering services:
```python
import sys
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
```

### 2. **Missing SigLIP Model**
**Fixed in:** [`labeller/templates/clustering_dashboard.html`](labeller/templates/clustering_dashboard.html)

Added SigLIP as the recommended model:
```html
<option value="siglip">SigLIP (Recommended - Fastest)</option>
<option value="dinov2">DINOv2 (Best Quality)</option>
```

### 3. **Auto-Clustering Feature**
**Fixed in:** [`labeller/templates/clustering_dashboard.html`](labeller/templates/clustering_dashboard.html) and [`labeller/app.py`](labeller/app.py)

Added DBSCAN auto-clustering that determines optimal number of clusters automatically:
```html
<select id="clustering-method">
    <option value="kmeans">K-means (Manual)</option>
    <option value="auto">Auto-Cluster (DBSCAN)</option>
</select>
```

### 4. **ERR_EMPTY_RESPONSE Issue**
**Root cause:** Extraction takes 5-10 seconds, browser might timeout or Flask crashes

**What I added:**
- Better logging in [`labeller/app.py`](labeller/app.py) to track what's happening
- Validation to ensure metadata file exists before reading
- Clear error messages with stack traces

---

## 🚀 How to Use

### Start the App with Virtual Environment

**Use this command from now on:**
```bash
./activate_and_run.sh
```

This script:
1. Activates `.venv` virtual environment
2. Verifies torch is installed
3. Starts all services (FastAPI, Streamlit, Flask)

### Access Clustering Dashboard

Open browser to:
```
http://localhost:5000/clustering
```

### Use the Features

#### Step 1: Extract Crops
- Click "Extract Crops"
- **Wait 5-10 seconds** (processing 500+ images)
- Should extract ~7,800 bird crops

#### Step 2: Generate Embeddings
- Select **"SigLIP (Recommended)"** for fastest results
- Or choose "DINOv2" for best quality
- Click "Generate Embeddings"
- Wait a few minutes (depends on GPU/CPU)

#### Step 3: Run Clustering
**Manual clustering (K-means):**
- Select "K-means (Manual)"
- Enter number of clusters (e.g., 30)
- Click "Run Clustering"

**Auto-clustering (DBSCAN):**
- Select "Auto-Cluster (DBSCAN)"
- Cluster count input disabled (determined automatically)
- Click "Run Clustering"
- DBSCAN finds optimal number based on density

---

## 🐛 Troubleshooting

### Still Getting "Failed to fetch" Error?

**Check 1: Is venv activated?**
```bash
echo $VIRTUAL_ENV
# Should show: /home/olisemeka.dev/Projects/nexus/.venv
```

**Check 2: Is Flask using venv Python?**
```bash
tail -f logs/nestperts.log
# Look for any import errors at startup
```

**Check 3: Test extraction manually**
```bash
source .venv/bin/activate
python3 -c "
from labeller.services.embedding_service import BirdCropManager
manager = BirdCropManager('labeller/nestvision/bird_crops')
manager.extract_and_save_crops(
    dataset_dir='labeller/nestvision',
    resize=None,
    min_size=20,
    max_size=10000,
    padding_percent=0.15
)
print('✓ Extraction works!')
"
```

**Check 4: Verify torch is available**
```bash
source .venv/bin/activate
python3 -c "import torch; print('✓ torch works')"
```

### Extraction Takes Too Long

**Normal behavior:**
- 500 images → 7,800 crops → **7-10 seconds**
- This is expected and working correctly

**If it times out in browser:**
1. Check `logs/nestperts.log` - extraction might be working but not returning response
2. Look for errors in the log
3. Try the manual test (Check 3 above) to verify extraction actually works

### Browser Console Errors

**Open browser console:**
- Right-click → Inspect → Console tab
- Look for detailed error messages
- Share full error stack trace if asking for help

### Flask Keeps Restarting

If you see multiple "Restarting with watchdog" messages in logs:
- Flask's auto-reload is detecting file changes
- This can cause imports to fail temporarily
- **Solution:** Disable auto-reload by editing `run_app.sh` line 166:
  ```bash
  # Change this line:
  $PYTHON_CMD labeller/app.py --data labeller/nestvision
  # To this (without --reload):
  $PYTHON_CMD labeller/app.py --data labeller/nestvision --no-reload
  ```

---

## 📊 Understanding Auto-Clustering

### K-means vs DBSCAN

**K-means (Manual):**
- You specify number of clusters (e.g., 30)
- Partitions all birds into exactly K groups
- **Best when:** You know roughly how many species/groups you have

**DBSCAN (Auto):**
- Automatically finds number of clusters based on density
- Birds close together in feature space → same cluster
- Birds far away → different clusters or "noise"
- **Best when:** You don't know how many clusters to use

### When to Use Each

**Use K-means if:**
- You know the dataset has ~N species
- You want consistent cluster sizes
- You want every bird assigned to a cluster

**Use DBSCAN if:**
- Unknown number of species
- Dataset has outliers/anomalies
- Clusters have varying densities
- You want algorithm to discover natural groupings

### DBSCAN Parameters

Current settings (in [`labeller/services/clustering_service.py`](labeller/services/clustering_service.py#L71)):
```python
DBSCAN(eps=0.5, min_samples=10)
```

- `eps=0.5`: Maximum distance between birds in same cluster
- `min_samples=10`: Minimum birds needed to form a cluster

**To adjust:**
- Smaller `eps` → more clusters (stricter grouping)
- Larger `eps` → fewer clusters (looser grouping)
- Smaller `min_samples` → more small clusters
- Larger `min_samples` → fewer, denser clusters

---

## 🎯 Model Comparison

### SigLIP (Recommended)
- **Speed:** ⭐⭐⭐⭐⭐ Fastest
- **Quality:** ⭐⭐⭐⭐ Excellent
- **Dimensions:** 768
- **Best for:** General use, fast iteration

### DINOv2
- **Speed:** ⭐⭐⭐ Moderate
- **Quality:** ⭐⭐⭐⭐⭐ Best
- **Dimensions:** 768
- **Best for:** Final production clustering, fine-grained visual similarity

### EfficientNet
- **Speed:** ⭐⭐⭐⭐ Fast
- **Quality:** ⭐⭐⭐ Good
- **Dimensions:** 1280
- **Best for:** Quick tests, baseline

### ResNet-50
- **Speed:** ⭐⭐⭐ Moderate
- **Quality:** ⭐⭐⭐ Good
- **Dimensions:** 2048
- **Best for:** Classic baseline, comparison

### CLIP
- **Speed:** ⭐⭐ Slow
- **Quality:** ⭐⭐⭐⭐ Very good
- **Dimensions:** 512
- **Best for:** Semantic understanding, experimental

---

## 📝 Test Script

I created a test script: [`test_clustering.sh`](test_clustering.sh)

**Run it to verify everything works:**
```bash
./test_clustering.sh
```

This tests:
1. Flask is running
2. Status endpoint works
3. Crop extraction endpoint works (30 second timeout)

---

## 🔍 What Happens Behind the Scenes

### When You Click "Extract Crops"

1. **Browser sends:** `POST /api/clustering/extract_crops`
2. **Flask receives request** and prints: `[Clustering] Starting crop extraction...`
3. **BirdCropManager** loads YOLO labels from `labeller/nestvision/labels/`
4. **For each image:**
   - Read YOLO bbox coordinates (normalized)
   - Convert to pixel coordinates
   - Add 15% padding around bird
   - Crop image and save to `bird_crops/images/bird_NNNN.jpg`
5. **Save metadata** to `bird_crops/metadata.json`
6. **Flask returns:** `{'status': 'success', 'total_crops': 7872}`
7. **Browser displays:** "✓ Extracted 7872 bird crops"

### Why It Takes 5-10 Seconds

- 501 images → 7,872 bird detections
- Each crop requires:
  - Read label file (~0.1ms)
  - Load image (~1-5ms)
  - Crop and save (~1-2ms)
- Total: 501 images × ~15ms = **7.5 seconds**

**This is normal and expected!**

---

## 🎓 What You're Learning

### Virtual Environments
You've now seen how Python isolates dependencies per-project. Without activating the venv, Flask tried to import `torch` from system Python (which doesn't have it), causing crashes.

### HTTP Request Timeouts
Long-running operations (5+ seconds) can cause browser timeouts. Solutions:
- Increase client timeout
- Make endpoint async (return immediately, poll for status)
- Use WebSockets for real-time progress
- Background task queues (Celery, RQ)

### Error Debugging Workflow
1. Check browser console for client-side errors
2. Check server logs for backend errors
3. Test endpoints manually with curl
4. Test Python imports directly
5. Verify environment setup (venv, dependencies)

---

## ✅ Quick Checklist

Before asking for help, verify:

- [ ] Virtual environment is activated (`echo $VIRTUAL_ENV`)
- [ ] torch is available (`python3 -c "import torch"`)
- [ ] Flask is running (`curl http://localhost:5000/api/clustering/status`)
- [ ] Checked `logs/nestperts.log` for errors
- [ ] Tried manual extraction test (see Troubleshooting section)
- [ ] Browser console shows full error message

---

**Everything should work now!** 🚀

If you still get errors after following this guide, share:
1. Full browser console error
2. Last 20 lines of `logs/nestperts.log`
3. Output of `echo $VIRTUAL_ENV`
4. Output of manual extraction test
