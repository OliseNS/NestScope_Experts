# DINOv2 3D Bird Clustering Guide

This guide explains the new DINOv2-based 3D clustering system that replaced the old hand-crafted feature approach.

## 🎯 What Changed

### Before (Old System)
- ❌ Used hand-crafted features (color histograms, textures, size)
- ❌ Downscaled bird crops to 224×224 (lost detail)
- ❌ 2D visualization (flat scatter plot)
- ❌ Could only see colored dots, not actual birds

### After (New System)
- ✅ Uses **DINOv2** (state-of-the-art self-supervised vision model)
- ✅ Preserves **original image resolution** (no downscaling)
- ✅ **3D interactive visualization** with rotation, zoom, pan
- ✅ See **actual bird images** in 3D space (like Google's t-SNE projector)
- ✅ **Lazy loading** for instant page load (images load on demand)

---

## 🧠 What is DINOv2?

**DINOv2** (Distillation with No Labels v2) is a **self-supervised vision transformer** from Meta AI.

### Why It's Perfect for Bird Clustering

1. **Self-Supervised Learning**
   - Trained on 142 million images WITHOUT labels
   - Learns pure visual similarity (not classification)
   - Perfect for finding "birds that look alike"

2. **Fine-Grained Detail Recognition**
   - Captures subtle differences in feather patterns
   - Recognizes body shapes, colors, textures
   - Works at high resolution (518×518 native)

3. **Comparison to Other Models**
   - **EfficientNet**: Trained for classification → biased toward class boundaries
   - **ResNet50**: Older architecture, less fine-grained
   - **DINOv2**: Learns similarity directly → better for clustering

### Technical Details
- Model: `dinov2_vitl14` (Large ViT with 14×14 patches)
- Embedding Dimension: **1024** (very rich feature representation)
- Input Resolution: **518×518** (preserves bird details)

---

## 📐 3D Dimensionality Reduction

### What is Dimensionality Reduction?

DINOv2 creates **1024-dimensional embeddings** for each bird. Humans can't visualize 1024 dimensions, so we use techniques to "squash" it down to 3D while preserving similarity relationships.

### UMAP vs t-SNE

The system uses **UMAP** (if available), otherwise falls back to **t-SNE**.

| Method | Speed | Quality | Best For |
|--------|-------|---------|----------|
| **UMAP** | Fast | Excellent | 3D visualization (preserves global + local structure) |
| **t-SNE** | Slower | Good | 2D visualization (preserves local structure) |

**Why UMAP for 3D?**
- t-SNE was designed for 2D (gets "crowded" in 3D)
- UMAP preserves both global structure (cluster separation) and local structure (similarity within clusters)
- Much faster for large datasets

**What You See:**
- Similar-looking birds cluster together in 3D space
- Different species form separate "clouds"
- You can rotate the 3D view to see relationships from all angles

---

## 🚀 How to Use

### 1. Run Clustering Pipeline

```bash
# Basic usage with DINOv2 (recommended)
python scripts/cluster_birds.py --data labeller/nestvision --model dinov2 --clusters 30

# Options:
#   --model: dinov2 (recommended), efficientnet, resnet50, clip
#   --clusters: Number of clusters (30 is a good starting point)
#   --method: kmeans (default) or dbscan (auto-finds clusters)
#   --force: Re-extract crops and embeddings (useful after adding new images)
```

**What Happens:**
1. **Extract crops**: Reads bird bounding boxes from YOLO labels
2. **Generate embeddings**: DINOv2 processes each bird crop (takes a few minutes)
3. **Cluster**: K-means groups similar birds
4. **3D reduction**: UMAP creates 3D coordinates
5. **Export**: Saves visualization data to `bird_crops/clusters/`

### 2. Start Nestperts

```bash
python labeller/app.py --data labeller/nestvision
```

### 3. Open 3D Cluster Explorer

Navigate to: **http://localhost:5000/clusters**

---

## 🎮 Using the 3D Viewer

### Navigation
- **Rotate**: Click and drag
- **Zoom**: Scroll or pinch
- **Pan**: Right-click and drag
- **Reset View**: Click "🎥 Reset Camera" button

### Interactions
- **Hover over a point**: See the bird image in a tooltip
- **Click a point**: Select the entire cluster and see preview images in sidebar
- **Adjust point size/opacity**: Use sliders in sidebar

### Lazy Loading
- Images load **only when needed** (when you hover or select)
- Page loads instantly (no waiting for thousands of images)
- **Preloading**: Nearby birds in the same cluster load in background for smooth navigation

---

## 📊 Understanding the Visualization

### What Do the Colors Mean?
Each color represents a **cluster** (group of visually similar birds).

### What Does Distance Mean?
- **Close together** = Visually similar (same species, or very similar appearance)
- **Far apart** = Visually different (different species, colors, sizes)

### Why Are Some Clusters Tight, Others Spread Out?
- **Tight cluster** = Birds in this cluster look very similar (e.g., all white pelicans)
- **Spread cluster** = More variability within the cluster (might need to split into more clusters)

---

## 🛠️ Architecture Changes

### Files Modified

1. **`labeller/services/embedding_service.py`**
   - Updated DINOv2 to use `vitl14` (large model, 1024-dim)
   - Changed resolution to 518×518 (native DINOv2 size)
   - Removed default downscaling (preserves original crop quality)
   - Changed interpolation to LANCZOS4 (higher quality)

2. **`labeller/services/clustering_service.py`**
   - Changed t-SNE to 3D (n_components=3)
   - Added UMAP support (with fallback to t-SNE)
   - Updated plots to 3D scatter + 2D projections
   - Export now includes `z` coordinate

3. **`labeller/templates/cluster_explorer_3d.html`**
   - NEW: 3D interactive visualization using Plotly 3D scatter
   - Lazy loading system with image caching
   - Hover tooltips showing bird images
   - Click-to-select cluster exploration
   - Staggered image loading for previews

4. **`labeller/app.py`**
   - Updated `/clusters` route to serve 3D template
   - Modified `/api/cluster_data` to handle 3D coordinates

5. **`scripts/cluster_birds.py`**
   - NEW: Simplified script using clustering service
   - Supports all models (dinov2, efficientnet, resnet50, clip)
   - Better CLI with examples and help text

### Data Flow

```
YOLO Dataset (images + labels)
    ↓
Extract bird crops (original resolution preserved)
    ↓
DINOv2 embeddings (1024-dim, 518×518 input)
    ↓
K-means clustering
    ↓
UMAP dimensionality reduction (3D)
    ↓
Export to JSON (x, y, z coordinates)
    ↓
3D web visualization (Plotly + lazy loading)
```

---

## 🎓 Educational Notes

### Why Self-Supervised Learning?

Traditional supervised learning requires:
- Labeled data (expensive, time-consuming)
- Model learns to predict specific classes
- Biased toward training classes

Self-supervised learning (DINOv2):
- No labels needed during training
- Model learns general visual similarity
- Works for ANY bird species (even ones not in training data)

### Why High Resolution Matters

Bird species differ in subtle ways:
- Feather patterns (stripes, spots)
- Beak shape and color
- Eye rings
- Leg color

Downscaling to 224×224 loses these details. DINOv2's 518×518 captures them.

### Why 3D Visualization?

- **2D**: Can't show all relationships (some clusters overlap)
- **3D**: Extra dimension reveals hidden structure
- **Interactive**: Rotate to see from all angles

Similar to how Google's t-SNE projector visualizes word embeddings in 3D space.

---

## 🧪 Performance Tips

### Speed vs Quality Trade-offs

| Model | Speed | Quality | When to Use |
|-------|-------|---------|-------------|
| **DINOv2** | Slow (1-2 hours for 10k birds) | Excellent | Final clustering, research |
| **EfficientNet** | Fast (10-20 min) | Good | Quick tests, prototyping |
| **ResNet50** | Medium | Okay | Baseline comparisons |

### Hardware Recommendations

- **GPU**: Highly recommended (10-20× faster)
- **CPU**: Works but slow (use EfficientNet if no GPU)
- **RAM**: 8GB minimum, 16GB+ recommended for large datasets

### Optimizing Clustering

```bash
# Start with fewer clusters to test
python scripts/cluster_birds.py --data labeller/nestvision --model dinov2 --clusters 15

# Use DBSCAN to auto-find optimal number
python scripts/cluster_birds.py --data labeller/nestvision --model dinov2 --method dbscan

# Force re-run after adding new images
python scripts/cluster_birds.py --data labeller/nestvision --model dinov2 --force
```

---

## 🐛 Troubleshooting

### "ModuleNotFoundError: No module named 'umap'"

UMAP is optional but recommended. Install it:

```bash
pip install umap-learn
```

If not installed, the system automatically uses t-SNE instead.

### "CUDA out of memory"

DINOv2 is memory-intensive. Solutions:

1. Close other GPU programs
2. Reduce batch size in `embedding_service.py` (line 354): `batch_size=16` → `batch_size=8`
3. Use CPU: The code auto-detects GPU/CPU

### "Clustering takes too long"

1. Use fewer clusters: `--clusters 15` instead of `--clusters 30`
2. Use EfficientNet instead: `--model efficientnet`
3. Sample your dataset (reduce number of images)

### "3D visualization is blank"

1. Check browser console for errors (F12)
2. Verify clustering completed: Look for `bird_crops/clusters/clusters_for_labeling.json`
3. Restart Flask app: `python labeller/app.py --data labeller/nestvision`

---

## 📚 Further Reading

- **DINOv2 Paper**: [DINOv2: Learning Robust Visual Features without Supervision](https://arxiv.org/abs/2304.07193)
- **UMAP**: [How UMAP Works](https://umap-learn.readthedocs.io/en/latest/how_umap_works.html)
- **t-SNE**: [How to Use t-SNE Effectively](https://distill.pub/2016/misread-tsne/)
- **Vision Transformers**: [An Image is Worth 16x16 Words](https://arxiv.org/abs/2010.11929)

---

## 🎯 Next Steps

1. **Run clustering** with DINOv2
2. **Explore 3D visualization** to understand cluster quality
3. **Label cluster representatives** in Nestperts
4. **Train species classifier** using cluster labels

---

**Last Updated:** 2026-02-25
