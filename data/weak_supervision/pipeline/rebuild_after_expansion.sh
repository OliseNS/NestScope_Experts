#!/bin/bash
# ============================================================================
# Rebuild Pipeline After Ground Truth Expansion
# ============================================================================
#
# Run this AFTER expand_ground_truth.py completes.
# It cleans old pipeline outputs and re-runs everything from scratch
# with the expanded dataset (100K original + ~60K new single-species crops).
#
# Steps:
#   1. Delete old pipeline outputs (embeddings, prototypes, assignments, export)
#   2. Regenerate embeddings for ALL crops (EfficientNet, 1280-dim)
#   3. Build ground truth prototypes (now ~30 species instead of 9)
#   4. Classify + iterative refinement (Hungarian matching + PoE)
#   5. Export quality report + frontend data
#   6. Export clean YOLO classification dataset
#
# Usage:
#   bash rebuild_after_expansion.sh
#
# Expected runtime: ~30-60 minutes on CPU (mainly embedding generation)
# ============================================================================

set -e  # Exit on any error

PYTHON="/home/olisemeka.dev/Projects/nexus/.venv/bin/python"
PROJECT_ROOT="/home/olisemeka.dev/Projects/nexus"
CROPS_DIR="$PROJECT_ROOT/data/weak_supervision/bird_crops"

cd "$PROJECT_ROOT"

echo "============================================================"
echo "REBUILD PIPELINE AFTER GROUND TRUTH EXPANSION"
echo "============================================================"
echo ""

# Step 0: Verify expansion completed
echo "[Step 0] Verifying expanded dataset..."
$PYTHON -c "
import json
with open('data/weak_supervision/bird_crops/metadata.json') as f:
    data = json.load(f)
total = data['total_crops']
single = sum(1 for c in data['crops'] if c['is_single_species'])
multi = total - single
print(f'  Total crops: {total:,}')
print(f'  Single-species (ground truth): {single:,} ({100*single/total:.1f}%)')
print(f'  Multi-species: {multi:,} ({100*multi/total:.1f}%)')
if total <= 100026:
    print('  WARNING: Dataset not expanded! Run expand_ground_truth.py first.')
    exit(1)
print('  Dataset looks expanded. Proceeding...')
"
echo ""

# Step 1: Clean old pipeline outputs
echo "[Step 1] Cleaning old pipeline outputs..."
rm -rf "$CROPS_DIR/embeddings"
rm -rf "$CROPS_DIR/ground_truth"
rm -rf "$CROPS_DIR/assignments"
rm -rf "$CROPS_DIR/export"
rm -f  "$CROPS_DIR/pipeline_state.json"
echo "  Deleted: embeddings/, ground_truth/, assignments/, export/, pipeline_state.json"
echo ""

# Step 2-5: Run full pipeline
echo "[Step 2-5] Running full pipeline (embeddings → prototypes → classify → export)..."
echo "  This will take 30-60 minutes on CPU..."
echo ""
$PYTHON data/weak_supervision/pipeline/run_full_pipeline.py --force-restart
echo ""

# Step 6: Export classification dataset
echo "[Step 6] Exporting YOLO classification dataset..."
$PYTHON data/weak_supervision/pipeline/export_classification_dataset.py \
    --output NestVision/classify \
    --min-samples 10
echo ""

echo "============================================================"
echo "REBUILD COMPLETE"
echo "============================================================"
echo ""
echo "Outputs:"
echo "  Embeddings:      $CROPS_DIR/embeddings/"
echo "  Ground truth:    $CROPS_DIR/ground_truth/"
echo "  Assignments:     $CROPS_DIR/assignments/"
echo "  Export:          $CROPS_DIR/export/"
echo "  Classification:  $PROJECT_ROOT/NestVision/classify/"
echo ""
echo "Next: Train YOLO classifier"
echo "  yolo classify train data=NestVision/classify/dataset.yaml model=yolov8n-cls.pt epochs=50 imgsz=224"
