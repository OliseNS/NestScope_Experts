# Clustering Features - Quick Start Guide

## ✅ Fixed: Import Error

**Problem:** When clicking buttons in the clustering dashboard, you got the error:
```
Error: No module named 'labeller'
```

**Cause:** The Flask app's clustering endpoints were using absolute imports (`from labeller.services.*`) but Python didn't know where to find the "labeller" module.

**Solution:** Added the project root to Python's path in `labeller/app.py` so Python can find all modules correctly.

---

## 🚀 How to Use Clustering Features

### Step 1: Start All Services

Run the startup script from the project root:

```bash
./run_app.sh
```

This starts three services:
- **FastAPI Backend:** http://localhost:8000 (for NestChat/NestVision)
- **Streamlit Frontend:** http://localhost:8501 (main UI)
- **Nestperts Flask App:** http://localhost:5000 (labeling & clustering)

### Step 2: Access the Clustering Dashboard

Open your browser and go to:
```
http://localhost:5000/clustering
```

### Step 3: Run the Complete Pipeline

The dashboard has 3 steps you run in order:

#### 📸 Step 1: Extract Bird Crops
- Extracts individual bird images from your YOLO dataset
- Saves cropped images to `labeller/nestvision/bird_crops/`
- Adds 15% padding around each bird for better context
- **Click:** "Extract Bird Crops" button
- **Wait:** This processes all labeled images (can take a few minutes)

#### 🧠 Step 2: Generate Embeddings
- Uses deep learning models to create feature vectors for each bird
- **Recommended Model:** SigLIP (fastest with great accuracy)
- **Alternative:** DINOv2 (best for fine-grained visual similarity)
- **Click:** "Generate Embeddings" button (optionally select model)
- **Output:** Creates `embeddings.npy` file with 768-dimensional vectors

#### 🎯 Step 3: Run Clustering
- Groups similar-looking birds together using K-means
- Creates interactive 3D visualization (t-SNE)
- **Default:** 30 clusters (you can adjust)
- **Click:** "Run Clustering" button
- **Output:**
  - `clusters_for_labeling.json` - cluster assignments
  - `clustering_3d.html` - interactive 3D explorer

### Step 4: Explore Your Clusters

After clustering completes, you can:

1. **View 3D Visualization:**
   - Open `labeller/nestvision/bird_crops/clusters/clustering_3d.html`
   - Interactive 3D plot showing clusters
   - Each point is a bird, colored by cluster
   - Hover to see which image/bird

2. **Label Clusters:**
   - Click "Open Cluster Explorer" in dashboard
   - Assign species to each cluster
   - Labels propagate to all birds in that cluster

3. **Export Labels:**
   - Updates YOLO label files with species codes
   - Saves to `cluster_labels.json`

---

## 🔍 What Happens Behind the Scenes

### Extract Crops (Step 1)
```python
# Reads YOLO labels (normalized coordinates)
# For each bird detection:
#   1. Convert normalized bbox to pixel coordinates
#   2. Add 15% padding (captures more context)
#   3. Crop bird from original image
#   4. Save to bird_crops/crops/bird_<N>.jpg
#   5. Record metadata (source image, bbox index)
```

**Files Created:**
- `bird_crops/crops/bird_0000.jpg`, `bird_0001.jpg`, etc.
- `bird_crops/metadata.json` - links crops to source images

### Generate Embeddings (Step 2)
```python
# For each bird crop:
#   1. Load image and preprocess (resize, normalize)
#   2. Pass through neural network
#   3. Extract feature vector from last layer
#   4. Save 768-dimensional embedding
```

**Models Available:**
- **SigLIP** (Recommended): Vision-language model, 768-dim, fastest
- **DINOv2**: Self-supervised ViT, 768-dim, best visual similarity
- **EfficientNet**: CNN, 1280-dim, good balance
- **ResNet-50**: Classic CNN, 2048-dim, baseline

**Files Created:**
- `bird_crops/embeddings.npy` - NumPy array (N_birds x 768)
- `bird_crops/config.json` - embedding configuration

### Run Clustering (Step 3)
```python
# 1. Load embeddings
# 2. Run K-means clustering (default: 30 clusters)
# 3. Assign each bird to nearest cluster center
# 4. Run t-SNE to reduce 768-dim → 3-dim for visualization
# 5. Generate interactive 3D plot
# 6. Export cluster assignments
```

**Algorithms:**
- **K-means**: Partitions birds into K clusters (you specify K)
- **t-SNE**: Reduces dimensions for visualization (preserves local structure)

**Files Created:**
- `bird_crops/clusters/clusters_for_labeling.json`
- `bird_crops/clusters/clustering_3d.html`
- `bird_crops/clusters/tsne_3d.npy` - 3D coordinates

---

## ⚡ Pro Tips

### Speed Up Processing

**For Large Datasets:**
```bash
# Use smaller crops (faster but less detail)
# Edit labeller/services/embedding_service.py:
# Change max_size from 10000 to 640
```

**Use Faster Model:**
```json
// In clustering dashboard, select "efficientnet"
// Trade-off: slightly less accurate clusters
```

**Batch Size:**
```python
# If you have a powerful GPU, increase batch size
# Edit embedding_service.py: batch_size=64 (default: 32)
```

### Better Clustering Results

**Increase Number of Clusters:**
- Default: 30 clusters
- For more diverse dataset: try 40-50 clusters
- For very similar birds: try 15-20 clusters

**Try Different Models:**
- **DINOv2**: Best for fine-grained visual differences (plumage patterns)
- **SigLIP**: Best balance of speed and accuracy (recommended)

**Filter Low-Quality Crops:**
```python
# Edit extract_and_save_crops() parameters:
# min_size=50 (larger = removes tiny/blurry birds)
```

---

## 🐛 Troubleshooting

### Error: "No module named 'torch'"
**Solution:** Install dependencies:
```bash
pip install -r requirements.txt
```

### Error: "CUDA out of memory"
**Solution:** Use CPU or smaller batch size:
```python
# Edit embedding_service.py:
# device = 'cpu'  # Force CPU
# batch_size = 8  # Smaller batches
```

### Clustering Takes Too Long
**Solution:**
1. Use SigLIP instead of DINOv2
2. Enable GPU if available (much faster)
3. Reduce number of crops (only use subset of images)

### Empty Clusters / Bad Results
**Solution:**
1. Check if crops look good (`bird_crops/crops/`)
2. Try different embedding model (DINOv2 vs SigLIP)
3. Adjust number of clusters (K)
4. Ensure YOLO labels are accurate

### Can't Access Dashboard
**Check if Flask app is running:**
```bash
curl http://localhost:5000/clustering
# Should return HTML, not error
```

**Check logs:**
```bash
tail -f logs/nestperts.log
```

---

## 📊 Understanding Your Results

### Cluster Quality Indicators

**Good Clustering:**
- Birds in same cluster look similar (same species/pose)
- Clear visual separation between clusters in 3D plot
- Clusters have reasonable sizes (not too big/small)

**Poor Clustering:**
- Mixed species in same cluster
- One huge cluster with tiny outlier clusters
- Clusters don't match visual similarity

**If Clustering is Poor:**
1. Try different embedding model
2. Adjust number of clusters
3. Check if YOLO detections are accurate
4. Ensure enough variety in training data

### Labeling Efficiency

**Traditional Approach:**
- 50,000 birds × 30 seconds = 416 hours (17 days!)

**Cluster-Based Approach:**
- 30 clusters × 10 minutes = 5 hours
- **98.8% time savings!** 🎉

**Why it Works:**
- Similar-looking birds cluster together
- Label entire cluster at once (hundreds of birds)
- Expert reviews representative samples per cluster
- Labels propagate to all birds in cluster

---

## 🎓 What You're Learning

### Computer Vision Concepts

**Embeddings:**
- Neural networks convert images → numerical vectors
- Similar images have similar vectors (close in embedding space)
- Captures semantic features (shape, texture, color patterns)

**Dimensionality Reduction (t-SNE):**
- Maps high-dimensional data (768-dim) → 3D for visualization
- Preserves local structure (similar birds stay close)
- Non-linear projection (better than PCA for complex data)

**Clustering (K-means):**
- Unsupervised learning (no labels needed)
- Finds K cluster centers that minimize within-cluster variance
- Assigns each point to nearest center

### Why Deep Learning?

**Hand-Crafted Features** (old approach):
- Color histograms, edge detection, SIFT keypoints
- Required expert domain knowledge
- Brittle to lighting changes, angles, occlusion

**Learned Features** (modern approach):
- Neural networks learn features from data
- Captures hierarchical patterns (edges → textures → objects)
- More robust and generalizable
- Transfer learning: pre-trained models work well on new data

### Model Architecture Differences

**CNNs (EfficientNet, ResNet):**
- Convolutional layers detect local patterns
- Good for texture, shape, object recognition
- Efficient but limited semantic understanding

**Vision Transformers (DINOv2, SigLIP):**
- Attention mechanisms capture global context
- Better at fine-grained visual distinctions
- Self-supervised learning (no labels during pre-training)
- SigLIP adds language understanding (vision-language model)

---

## 📚 Further Reading

- **DINOv2 Paper:** [Self-Supervised Vision Transformers](https://arxiv.org/abs/2304.07193)
- **SigLIP Paper:** [Sigmoid Loss for Language-Image Pre-Training](https://arxiv.org/abs/2303.15343)
- **t-SNE:** [Visualizing Data using t-SNE](https://jmlr.org/papers/v9/vandermaaten08a.html)
- **K-means Clustering:** [scikit-learn Documentation](https://scikit-learn.org/stable/modules/clustering.html#k-means)

---

## 🎯 Quick Command Reference

```bash
# Start all services
./run_app.sh

# Access clustering dashboard
open http://localhost:5000/clustering

# View logs
tail -f logs/nestperts.log

# Run clustering from command line (alternative)
python scripts/cluster_birds.py --data labeller/nestvision --model siglip --clusters 30

# Check clustering status
curl http://localhost:5000/api/clustering/status

# Stop all services
# Press Ctrl+C in terminal running ./run_app.sh
```

---

**You're all set!** 🚀

The import error is fixed, and you can now run the full clustering pipeline from the frontend dashboard at http://localhost:5000/clustering.
