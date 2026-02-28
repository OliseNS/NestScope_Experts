# Weak Supervision Pipeline

Complete automated pipeline for extracting, clustering, and labeling bird crops from aerial survey images using weak supervision and computer vision.

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [Step-by-Step Guide](#step-by-step-guide)
4. [Output Structure](#output-structure)
5. [Viewing Results](#viewing-results)
6. [Advanced Options](#advanced-options)
7. [Troubleshooting](#troubleshooting)
8. [How It Works](#how-it-works)

---

## Overview

This pipeline transforms raw aerial survey images into a labeled dataset of bird crops suitable for training species classification models.

### What You'll Get

Starting with:
- ✅ Aerial survey images from S3
- ✅ Database metadata with species information

Ending with:
- 🎯 100,026 individual bird crop images
- 🎯 Species assignments for each crop (via clustering)
- 🎯 Confidence scores for each assignment
- 🎯 Interactive visualization dashboard
- 🎯 Ready-to-use training dataset

### Pipeline Phases

1. **Phase 1**: Detection & Crop Extraction → Extract individual bird crops from images
2. **Phase 2**: Species Assignment → Use clustering to assign species to each crop
3. **Phase 3**: Visualization & Review → Explore results in interactive dashboard

---

## Quick Start

If you want to run the entire pipeline from scratch:

```bash
# Navigate to pipeline directory
cd /home/olisemeka.dev/Projects/nexus/data/weak_supervision/pipeline

# Phase 1: Extract 100K bird crops (4-6 hours)
python run_detection_pipeline.py

# Phase 2: Assign species via clustering (~70 minutes on CPU)
python run_full_pipeline.py

# Phase 3: View results in dashboard
cd ../../labeller
python app.py --data nestvision
# Open: http://localhost:5000/clusters
```

That's it! Continue reading for detailed explanations of each phase.

---

## Step-by-Step Guide

### Prerequisites

**Required:**
- Python 3.8+ with virtual environment activated
- All dependencies installed (`pip install -r requirements.txt`)
- Sufficient disk space (~6 GB for 100K crops + embeddings)

**Check your setup:**
```bash
# Verify you're in the right directory
pwd
# Should show: /home/olisemeka.dev/Projects/nexus/data/weak_supervision/pipeline

# Verify Python environment
which python
# Should point to your .venv or conda environment

# Check GPU availability (optional, but 10x faster)
python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}')"
```

---

### Phase 1: Detection & Crop Extraction

**Goal:** Extract 100,000 individual bird crops from aerial survey images.

**Command:**
```bash
cd /home/olisemeka.dev/Projects/nexus/data/weak_supervision/pipeline
python run_detection_pipeline.py
```

**What happens:**
1. Loads photo metadata from database (6,795 images available)
2. For each image:
   - Downloads from S3 (if not already downloaded)
   - Runs YOLO bird detection (Swift model @ 0.30 confidence)
   - Extracts bounding boxes as individual crop images
   - Links each crop to species candidates from database
3. Saves crops continuously (resume-safe)
4. Stops automatically at 100,000 crops

**Expected runtime:** 4-6 hours

**Output location:** `../bird_crops/`
```
bird_crops/
├── images/                    # 100,026 bird crop images
│   ├── bird_000000.jpg
│   ├── bird_000001.jpg
│   └── ...
├── metadata.json              # Crop metadata with species candidates
└── processing_log.json        # Progress tracking
```

**Verification:**
```bash
# Count crops extracted
ls ../bird_crops/images/ | wc -l
# Should show: 100026

# Check metadata file exists
ls -lh ../bird_crops/metadata.json
# Should be ~57 MB
```

**Resume if interrupted:**
```bash
python run_detection_pipeline.py --resume
```

---

### Phase 2: Species Assignment via Clustering

**Goal:** Assign species labels to all 100K crops using intelligent clustering.

#### Stage 1: Extract Embeddings

Converts each bird image into a 1280-dimensional "fingerprint" that captures visual features.

**What happens:**
- Loads all 100K crop images
- Passes each through EfficientNet-B0 neural network
- Extracts embedding vector (1280 numbers representing the bird's appearance)
- Saves to numpy array for fast access

**Expected runtime:** ~50 minutes (CPU) or ~15 minutes (GPU)

#### Stage 2: Per-Image Clustering

Groups birds within each source image based on visual similarity.

**What happens:**
- Groups crops by their source image (1,045 images)
- For each image:
  - **If single-species**: Direct assignment (confidence = 1.0)
  - **If multi-species**: Run K-means clustering where K = number of species
- Assigns each crop to a cluster → species mapping

**Expected runtime:** ~5 minutes

**Why per-image clustering?**
Instead of clustering all 100K birds globally, we cluster within each image. This preserves the image-level species context from the database metadata, leading to more accurate assignments.

#### Stage 3: Cross-Image Validation

Compares clusters across all images to detect outliers and assign confidence scores.

**What happens:**
- Collects all clusters labeled with same species (e.g., all "GREG" clusters)
- Computes average "prototype" for each species
- Measures similarity of each cluster to its species prototype
- Flags outliers (clusters >2 std deviations from mean)
- Assigns confidence scores

**Expected runtime:** ~2 minutes

#### Stage 4: Export for Visualization

Generates 2D visualization and frontend-compatible JSON.

**What happens:**
- Runs UMAP dimensionality reduction (1280D → 2D)
- Creates scatter plot coordinates for all 100K crops
- Generates species cluster preview images
- Exports JSON for Nestperts dashboard

**Expected runtime:** ~10 minutes

---

**Run All Stages:**
```bash
cd /home/olisemeka.dev/Projects/nexus/data/weak_supervision/pipeline
python run_full_pipeline.py
```

**Total runtime:** ~70 minutes (CPU) or ~30 minutes (GPU)

**Output location:** `../bird_crops/`
```
bird_crops/
├── images/                          # [from Phase 1]
├── metadata.json                    # [from Phase 1]
├── embeddings/                      # NEW: Stage 1 output
│   ├── embeddings_all.npy          # (100026, 1280) array
│   ├── embeddings_index.json       # crop_id → array index
│   └── embeddings_config.json      # Model metadata
└── species_clusters/                # NEW: Stages 2-4 output
    ├── image_clusters/              # Stage 2: Per-image results
    │   ├── 2015_1_1_00094.json
    │   └── ... (1,045 files)
    ├── summary.json                 # Stage 2: Statistics
    ├── global_cluster_map.json      # Stage 3: Cross-image validation
    ├── clusters_for_labeling.json   # Stage 4: Frontend JSON
    └── cluster_GREG/                # Stage 4: Species folders
        ├── preview.jpg              # Grid of sample birds
        └── info.json                # Cluster metadata
```

**Verification:**
```bash
# Check embeddings created
python -c "import numpy as np; e = np.load('../bird_crops/embeddings/embeddings_all.npy'); print(f'Shape: {e.shape}')"
# Should show: Shape: (100026, 1280)

# Check image clusters created
ls ../bird_crops/species_clusters/image_clusters/ | wc -l
# Should show: 1045

# Check frontend JSON created
ls -lh ../bird_crops/species_clusters/clusters_for_labeling.json
# Should exist and be ~100 MB
```

---

## Output Structure

After running both phases, your directory structure will look like:

```
weak_supervision/
├── pipeline/                        # Scripts (you are here)
│   ├── run_detection_pipeline.py
│   ├── run_full_pipeline.py
│   ├── stage1_generate_embeddings.py
│   ├── stage2_per_image_clustering.py
│   ├── stage3_global_species_assignment.py
│   ├── stage4_export_for_frontend.py
│   └── README.md
│
├── bird_crops/                      # All outputs
│   ├── images/                      # 100,026 crop images
│   ├── metadata.json                # Crop metadata
│   ├── embeddings/                  # Stage 1: Embeddings
│   └── species_clusters/            # Stages 2-4: Clustering
│
├── downloaded_images/               # Original survey images
├── image_metadata.json              # Database export
└── photo_mappings_2015_2021.json    # Photo-species mappings
```

---

## Viewing Results

### Interactive Dashboard

After Phase 2 completes, view your clustered birds:

```bash
cd /home/olisemeka.dev/Projects/nexus/labeller
python app.py --data nestvision
```

**Open in browser:** http://localhost:5000/clusters

**What you'll see:**
- **2D scatter plot** with all 100K birds as points
- **67 species clusters** colored by species
- **Click any point** to view the bird crop image
- **Outliers highlighted** for manual review
- **Confidence scores** for each cluster

### Explore the Data

**Check statistics:**
```bash
cd /home/olisemeka.dev/Projects/nexus/data/weak_supervision

# View clustering summary
cat bird_crops/species_clusters/summary.json | jq '.'

# View species distribution
cat bird_crops/species_clusters/global_cluster_map.json | jq '.species_summary'

# Count species
cat bird_crops/species_clusters/global_cluster_map.json | jq '.metadata.total_species'
```

**View specific species:**
```bash
# See all GREG (Great Egret) clusters
cat bird_crops/species_clusters/global_cluster_map.json | jq '.species_summary.GREG'

# List all species
cat bird_crops/species_clusters/global_cluster_map.json | jq '.species_summary | keys'
```

---

## Advanced Options

### Resume After Interruption

Both phases support resume:

```bash
# Phase 1: Resume detection
python run_detection_pipeline.py --resume

# Phase 2: Resume clustering (automatic)
python run_full_pipeline.py
```

The clustering pipeline automatically detects completed stages and skips them.

### Force Restart

To start fresh:

```bash
# Phase 1: Delete output and restart
rm -rf ../bird_crops
python run_detection_pipeline.py

# Phase 2: Clear clustering and restart
python run_full_pipeline.py --force-restart
```

### Run Specific Stages

Skip already-completed stages:

```bash
# Start from Stage 2 (skip embedding extraction)
python run_full_pipeline.py --start-from 2

# Start from Stage 3 (skip embeddings + clustering)
python run_full_pipeline.py --start-from 3
```

### Try Different Models

Use different embedding models for clustering:

```bash
# EfficientNet-B0 (default): Fast, accurate, 1280-dim
python run_full_pipeline.py --model efficientnet

# SigLIP: Faster with semantic understanding, 768-dim
python run_full_pipeline.py --model siglip

# DINOv2: Best for fine-grained similarity, 768-dim
python run_full_pipeline.py --model dinov2

# ResNet-50: Standard baseline, 2048-dim
python run_full_pipeline.py --model resnet50

# CLIP: Vision-language model, 512-dim
python run_full_pipeline.py --model clip
```

### Adjust Detection Parameters

For Phase 1:

```bash
# Lower confidence = more detections (but more false positives)
python run_detection_pipeline.py --conf 0.25

# Extract more crops
python run_detection_pipeline.py --max-crops 150000

# Different model mode (faster vs more accurate)
python run_detection_pipeline.py --fast-mode  # Use Swift model (default)
# or run in non-fast mode for Apex model (slower, more accurate)
```

### Low Memory Mode

If you encounter memory issues during clustering:

```bash
# Enable low-memory mode (Stage 1)
python stage1_generate_embeddings.py --low-memory

# Reduce batch size (Stage 1)
python stage1_generate_embeddings.py --batch-size 4
```

### Speed Up Visualization

Install UMAP for 3x faster Stage 4:

```bash
pip install umap-learn
python run_full_pipeline.py
```

---

## Troubleshooting

### Phase 1 Issues

**Problem:** "S3 download failed"
```bash
# Solution: Skip to next image automatically (built-in)
# Or manually download problem images later
```

**Problem:** "Out of disk space"
```bash
# Check available space
df -h /home/olisemeka.dev/Projects/nexus

# Each crop is ~50KB, 100K crops = ~5GB
# You need ~6GB total (including originals)
```

**Problem:** "Detection very slow"
```bash
# Check if GPU is being used
python -c "import torch; print(torch.cuda.is_available())"

# If False, you're on CPU (10x slower)
# Consider running on GPU machine or reducing --max-crops
```

### Phase 2 Issues

**Problem:** "Module not found: embedding_service"
```bash
# Solution: Run from correct directory
cd /home/olisemeka.dev/Projects/nexus/data/weak_supervision/pipeline
python run_full_pipeline.py
```

**Problem:** "CUDA out of memory"
```bash
# Solution 1: Reduce batch size
python stage1_generate_embeddings.py --batch-size 4

# Solution 2: Force CPU
export CUDA_VISIBLE_DEVICES=""
python run_full_pipeline.py
```

**Problem:** "Stage X failed"
```bash
# Check error message in output
# Then restart from that stage
python run_full_pipeline.py --start-from X
```

**Problem:** "No cluster JSON files found"
```bash
# Make sure Stage 2 completed successfully
ls ../bird_crops/species_clusters/image_clusters/ | wc -l

# If 0, re-run Stage 2
python stage2_per_image_clustering.py
```

**Problem:** "Embeddings file not found"
```bash
# Re-run Stage 1
python stage1_generate_embeddings.py
```

### Dashboard Issues

**Problem:** "Cannot connect to http://localhost:5000"
```bash
# Make sure Flask app is running
cd /home/olisemeka.dev/Projects/nexus/labeller
python app.py --data nestvision

# Check if port is already in use
lsof -i :5000
```

**Problem:** "No clusters shown in dashboard"
```bash
# Verify JSON file exists
ls -lh /home/olisemeka.dev/Projects/nexus/data/weak_supervision/bird_crops/species_clusters/clusters_for_labeling.json

# If missing, re-run Stage 4
cd /home/olisemeka.dev/Projects/nexus/data/weak_supervision/pipeline
python stage4_export_for_frontend.py
```

---

## How It Works

### Phase 1: Why Weak Supervision?

Traditional supervised learning requires manually labeling thousands of birds - prohibitively expensive for 100K images.

**Weak supervision approach:**
- Use database metadata for image-level labels (e.g., "this image contains GREG, BRPE, LAGU")
- Extract individual birds from images
- Use clustering to assign crops to species
- Result: Approximate labels at scale (with confidence scores)

**Trade-off:**
- ✅ Fast: 70 minutes vs weeks of manual labeling
- ✅ Scalable: Works for 100K+ crops
- ⚠️ Less accurate than manual labels (but good enough for training)

### Phase 2: Per-Image Clustering Strategy

**Why not cluster all 100K birds globally?**

Global clustering loses image-level context. Example:
- Image 1 has species: ["GREG", "BRPE"]
- Image 2 has species: ["LAGU", "TRHE"]
- Global clustering might group all white birds together (GREG + LAGU)

**Per-image clustering solution:**
- Cluster crops within each image separately
- Use metadata to know K (number of species per image)
- Assign clusters to species using image-level labels
- Result: Context-aware species assignments

### Understanding Embeddings

**What's an embedding?**

Think of it as a "fingerprint" for each bird image:
- EfficientNet converts image → 1,280 numbers
- Numbers capture: colors, textures, shapes, patterns
- Similar-looking birds = similar numbers

**Why 1,280 dimensions?**

More dimensions = more detail captured. EfficientNet-B0 uses 1,280 as a balance between:
- Enough detail to distinguish species
- Small enough to process quickly

### K-Means Clustering Explained

**The problem:**
- Image has 193 birds
- Metadata says 2 species present
- Which birds belong to which species?

**K-Means solution:**
1. Find 2 "prototype" birds (centroids) that best represent the 2 species
2. Assign each bird to nearest prototype
3. Result: 193 birds split into 2 groups

**Why K-Means vs other methods?**
- We know K (number of species) from metadata
- K-Means guarantees exactly K clusters
- Other methods (DBSCAN) might give 1 or 5 clusters - not what we need

### Cross-Image Validation (Stage 3)

**The challenge:**
After per-image clustering, we have thousands of clusters labeled "GREG". But are they all really Great Egrets?

**The solution:**
1. Collect all "GREG" clusters from all images
2. Compute average prototype for "GREG"
3. Measure similarity of each cluster to prototype
4. Flag outliers (>2 std deviations below average)

**Real-world analogy:**
Imagine sorting dog photos by breed without knowing what breeds look like. You group dogs within each photo, then compare all "Golden Retriever" groups across photos. If one looks totally different (maybe it's a Yellow Lab), you catch the error!

### Visualization with UMAP/t-SNE

**The problem:**
- Embeddings have 1,280 dimensions
- Humans can only see 2D (x, y on screen)

**The solution:**
- UMAP compresses 1,280D → 2D
- Keeps similar birds close together
- Result: Species form visual "islands" on 2D plot

**What you'll see:**
- GREG (Great Egrets) cluster together
- BRPE (Brown Pelicans) form separate island
- Outliers appear as lone points far from their island

---

## Performance Benchmarks

### Phase 1: Detection & Crop Extraction

| Hardware | Time | Notes |
|----------|------|-------|
| GPU (NVIDIA RTX 3080) | 2-3 hours | Recommended |
| GPU (NVIDIA GTX 1080) | 4-5 hours | Good |
| CPU (8-core) | 6-8 hours | Slow but works |
| CPU (4-core) | 10-12 hours | Very slow |

**Bottleneck:** YOLO inference

### Phase 2: Species Assignment

| Stage | GPU Time | CPU Time | Bottleneck |
|-------|----------|----------|------------|
| Stage 1: Embeddings | ~15 min | ~50 min | EfficientNet inference |
| Stage 2: Clustering | ~5 min | ~5 min | K-means |
| Stage 3: Validation | ~2 min | ~2 min | Similarity computation |
| Stage 4: Visualization | ~10 min | ~10 min | UMAP |
| **Total** | **~30 min** | **~70 min** | |

**Memory usage:**
- Peak RAM: ~2GB
- Peak VRAM: ~4GB (GPU)
- Disk space: ~600MB (embeddings + clusters)

---

## Next Steps After Pipeline

### 1. Review Clusters

Open dashboard and explore:
- Do species clusters look correct?
- Are there obvious outliers?
- Do similar-looking species overlap?

### 2. Validate Outliers

Focus on low-confidence clusters:
```bash
# Find low-confidence clusters
cat bird_crops/species_clusters/global_cluster_map.json | jq '.cluster_assignments | to_entries | .[] | select(.value.confidence < 0.5)'
```

### 3. Export Training Dataset

Use validated labels to create training dataset:
```bash
# Coming soon: export_training_dataset.py
python export_training_dataset.py \
    --min-confidence 0.7 \
    --output ../training_dataset
```

### 4. Train Species Classifier

Fine-tune a model on your labeled data:
```bash
cd ../../VisionTrain
# Train classification model on exported dataset
```

### 5. Active Learning

Prioritize labeling low-confidence crops:
- Sort crops by confidence score
- Manually label lowest 10%
- Retrain model with corrected labels
- Repeat until target accuracy reached

---

## Credits

**NestScope Weak Supervision Pipeline**
- Computer vision: YOLO (Ultralytics)
- Embeddings: EfficientNet-B0 (timm)
- Clustering: K-Means (scikit-learn)
- Visualization: UMAP (umap-learn) / t-SNE (scikit-learn)
- Dashboard: Flask + Three.js

**Data:**
- Gulf Coast Avian Monitoring Program (2010-2021)
- 1,045 aerial survey images
- 100,026 bird detections
- 67 species

---

## Support

If you encounter issues:

1. **Check this README** - Most questions are answered above
2. **Check error messages** - Often self-explanatory
3. **Verify paths** - Make sure you're in correct directory
4. **Check disk space** - Need ~6GB free
5. **Try resume** - Both phases support resume after crashes

**Common issues:**
- Module not found → Wrong directory
- Out of memory → Reduce batch size
- Slow performance → Check GPU usage
- Missing files → Re-run previous stage

**File a bug:**
- Include error message
- Include command you ran
- Include system info (GPU/CPU, RAM, OS)
