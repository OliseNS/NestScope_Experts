# Weak Supervision Pipeline Documentation

## Overview

This pipeline assigns species labels to ~160K+ individual bird crops extracted from high-resolution colony photos. Since we don't have per-bird species labels (only per-image), we use **weak supervision** to propagate image-level labels to individual birds.

### The Core Insight

Some images contain only **one species** — these are our **ground truth**. Every bird in a single-species image IS that species. We use these as anchors and propagate labels to multi-species images through clustering and matching.

## Directory Structure

```
data/weak_supervision/
├── photo_mappings_2015_2021.json          # 6,795 photos with S3 paths and species
├── image_metadata.json                     # Photo metadata (species, counts, paths)
├── downloaded_images/                      # ~6,779 downloaded JPEGs from S3
│
├── pipeline/                               # All pipeline scripts
│   ├── expand_ground_truth.py              # Step 0: Process unprocessed single-species images
│   ├── stage1_generate_embeddings.py       # Step 1: EfficientNet embeddings
│   ├── stage2_ground_truth_prototypes.py   # Step 2: Build species prototypes
│   ├── stage3_classify_multi_species.py    # Step 3: Hungarian matching + PoE
│   ├── stage4_cross_reference.py           # Step 4: Iterative refinement
│   ├── stage5_export.py                    # Step 5: Quality report + export
│   ├── run_full_pipeline.py                # Orchestrator (runs steps 1-5)
│   ├── export_classification_dataset.py    # Export YOLO classification dataset
│   ├── run_detection_pipeline.py           # Original detection pipeline
│   ├── rebuild_after_expansion.sh          # Full rebuild script
│   └── cleanup_old_data.py                 # Clean old pipeline outputs
│
└── bird_crops/                             # All extracted bird crops
    ├── metadata.json                       # Crop metadata (IDs, bboxes, species)
    ├── processing_log.json                 # Processing progress tracker
    ├── pipeline_state.json                 # Pipeline stage completion state
    │
    ├── images/                             # Individual bird JPEGs
    │   ├── bird_000000.jpg                 # crop_id 0
    │   └── bird_NNNNNN.jpg                 # sequential
    │
    ├── embeddings/                         # EfficientNet-B0 feature vectors
    │   ├── embeddings_all.npy              # N x 1280 float32 array
    │   ├── embeddings_index.json           # crop_id → row index mapping
    │   └── embeddings_config.json          # Model info, dimensions
    │
    ├── ground_truth/                       # Species prototypes from single-species images
    │   ├── prototypes.json                 # Cleaned centroid per species
    │   └── excluded_crops.json             # Outliers removed during cleaning
    │
    ├── assignments/                        # Final species assignments
    │   ├── final_assignments.json          # crop_id → species + confidence + method
    │   ├── final_prototypes.json           # Refined prototypes (after iterative rounds)
    │   └── refinement_log.json             # Per-round convergence stats
    │
    └── export/                             # Frontend + training exports
        ├── final_species_labels.json       # Summary labels
        ├── quality_report.json             # Per-species stats
        └── clusters_for_labeling.json      # Frontend visualization data

NestVision/classify/                        # YOLO classification dataset
├── train/                                  # 80% split per species
│   ├── LAGU/                               # Symlinks to crop images
│   ├── BRPE/
│   └── .../
├── val/                                    # 20% split per species
│   ├── LAGU/
│   └── .../
├── dataset.yaml                            # YOLO training config
└── dataset_stats.json                      # Per-species statistics
```

## Pipeline Steps

### Step 0: Expand Ground Truth (`expand_ground_truth.py`)

**Purpose**: Process downloaded single-species images that haven't been cropped yet.

**What it does**:
1. Finds single-species images in `photo_mappings_2015_2021.json` not in `processing_log.json`
2. Runs Swift YOLO detection (0.30 confidence, SAHI for large images)
3. Extracts bird crops with 5% padding, saves as JPEG (95% quality)
4. Appends to existing `metadata.json` (IDs continue from last crop)
5. Updates `image_metadata.json`

**Why**: Original pipeline processed 1,045 images (143 single-species). There were 1,631 more single-species images downloaded but never processed. Processing them expands ground truth from 9 to 30 species.

```bash
python expand_ground_truth.py --dry-run     # Preview
python expand_ground_truth.py               # Run
python expand_ground_truth.py --resume      # Resume after interruption
```

### Step 1: Generate Embeddings (`stage1_generate_embeddings.py`)

**Purpose**: Convert each bird crop into a 1280-dimensional feature vector.

**Model**: EfficientNet-B0 (chosen for CPU + 16GB RAM constraints)
- 1280-dim output per image
- ~5M parameters (lightweight)
- Good enough when combined with Hungarian matching

**Output**: `embeddings_all.npy` (N x 1280), `embeddings_index.json`

### Step 2: Build Ground Truth Prototypes (`stage2_ground_truth_prototypes.py`)

**Purpose**: Create a "representative embedding" for each species using single-species images.

**Algorithm**:
1. For each species with single-species images:
   - Collect all crop embeddings
   - **Intra-image cleaning**: Remove crops that are outliers within their image (>2 std from image mean) — catches detection errors (rocks, water, partial birds)
   - **Inter-image cleaning**: Remove crops far from global centroid (>2 std) — catches unusual specimens
2. Store cleaned centroid + similarity threshold

**Output**: `prototypes.json` with centroid, crop_ids, similarity stats per species

### Step 3: Classify Multi-Species Images (`stage3_classify_multi_species.py`)

**Purpose**: Assign species to each bird in multi-species images.

**Algorithm** (per image with K species candidates):
1. K-means clustering with K clusters
2. **Hungarian matching**: Build cost matrix (negative cosine similarity between cluster centroids and species prototypes), use `scipy.optimize.linear_sum_assignment` for optimal 1-to-1 matching
3. **Process of Elimination (PoE)**: Unmatched clusters (species without prototypes) assigned by exclusion
4. **Per-crop outlier rejection**: Each crop's similarity to its assigned prototype must exceed `min_acceptable_similarity`

**Why Hungarian matching?** The old pipeline assigned clusters to species sequentially (cluster 0 → species[0]) — but K-means cluster IDs are arbitrary. Hungarian algorithm finds the mathematically optimal assignment.

### Step 4: Iterative Refinement (`stage4_cross_reference.py`)

**Purpose**: Bootstrap prototypes for species that lack ground truth through cascading coverage.

**The Key Insight**: Not all species have single-species images. But after Round 1 of matching, PoE assignments give us "soft prototypes" for new species. Round 2 uses these expanded prototypes for better matching, unlocking even more species.

```
Round 0: 9 species from ground truth → ~30 species with expansion
Round 1: Classify with 30 prototypes → high-confidence assignments expand to cover more
Round 2: Re-classify → convergence (<1% assignment changes) → stop
```

**Quality Controls**:
- Ground truth crops are NEVER removed from prototypes
- New crops need confidence >= 0.7 to be included in prototype expansion
- Soft prototypes require >= 10 crops
- Convergence: <1% assignment changes between rounds

### Step 5: Export & Quality Report (`stage5_export.py`)

**Purpose**: Generate final labels, quality metrics, and frontend visualization data.

**Outputs**:
- `final_species_labels.json`: Every crop with species, confidence, method
- `quality_report.json`: Per-species statistics, method distribution
- `clusters_for_labeling.json`: UMAP 2D positions for Nestperts dashboard

### Classification Dataset Export (`export_classification_dataset.py`)

**Purpose**: Create a YOLO-compatible folder structure for training a species classifier.

```bash
python export_classification_dataset.py \
    --output NestVision/classify \
    --min-samples 10 \
    --train-ratio 0.8
```

Uses **symlinks** (saves ~500MB disk space). Splits 80/20 train/val, stratified by species.

## Assignment Methods

Each crop is labeled with one of these methods:

| Method | Description | Confidence Range |
|--------|-------------|-----------------|
| `ground_truth` | From single-species image | 1.0 |
| `hungarian` | Matched to prototype via Hungarian algorithm | 0.5 - 1.0 |
| `poe` | Assigned by Process of Elimination | varies |
| `EXCLUDED` | Below similarity threshold | - |

## Running the Full Pipeline

### Fresh Start
```bash
# Process any unprocessed single-species images first
python data/weak_supervision/pipeline/expand_ground_truth.py

# Clean old outputs and run full pipeline
bash data/weak_supervision/pipeline/rebuild_after_expansion.sh
```

### Rebuild After Changes
```bash
# Delete old pipeline data
rm -rf data/weak_supervision/bird_crops/{embeddings,ground_truth,assignments,export}
rm -f data/weak_supervision/bird_crops/pipeline_state.json

# Re-run
python data/weak_supervision/pipeline/run_full_pipeline.py --force-restart
```

### Train YOLO Classifier

Two classifier models (requires GPU — use RunPod or similar):

```bash
# Apex (accurate, YOLOv8s-cls, 12MB) — recommended
python NestVision/train_classifier.py --data dataset --mode apex

# Swift (fast, YOLOv8n-cls, 3.5MB)
python NestVision/train_classifier.py --data dataset --mode swift

# Both at once
python NestVision/train_classifier.py --data dataset --mode both
```

Output models: `classifier_swift.pt` and `classifier_apex.pt`
Place in `models/` directory (referenced by `server/config.yaml`).

## Key Design Decisions

1. **EfficientNet over DINOv2/SigLIP**: CPU + 16GB RAM constraint. The real accuracy gain comes from Hungarian matching, not embedding quality.

2. **Hungarian matching over sequential assignment**: Mathematically optimal 1-to-1 matching. This was the single biggest accuracy improvement.

3. **Accuracy over completeness**: We exclude ambiguous crops rather than risk mislabeling. A smaller clean dataset is better for training than a large noisy one.

4. **Iterative refinement**: Cascading coverage bootstraps prototypes for species without single-species images. Each round unlocks more species.

5. **Symlinks for classification dataset**: Avoids duplicating 500MB+ of images. The crop images stay in one place (`bird_crops/images/`).
