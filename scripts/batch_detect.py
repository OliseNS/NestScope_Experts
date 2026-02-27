"""
Batch Detection Script - Phase 3b

Runs YOLO detection on downloaded images and extracts bird crops with species linkage.

Features:
1. Reads from image_metadata.json (created by batch_download.py)
2. Can process images balanced by species (optional)
3. Each crop linked to species candidates from source image
4. Progress saved incrementally (crash recovery)
5. Can resume from where it left off

Output:
- bird_crops/images/ - Individual bird crop images
- bird_crops/metadata.json - Complete crop metadata with species linkage
"""

import json
import cv2
import numpy as np
from pathlib import Path
from typing import List, Dict, Tuple
from collections import defaultdict
import sys

# Optional import for progress bars
try:
    from tqdm import tqdm
except ImportError:
    def tqdm(iterable, desc=""):
        return iterable
    print("⚠️ tqdm not installed - progress bars disabled")

# Add server directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from server.cv_tools.inference import BirdDetector

# Configuration
PROJECT_ROOT = Path(__file__).parent.parent
IMAGE_METADATA_FILE = PROJECT_ROOT / "data" / "weak_supervision" / "image_metadata.json"
CROPS_DIR = PROJECT_ROOT / "data" / "weak_supervision" / "bird_crops" / "images"
CROP_METADATA_FILE = PROJECT_ROOT / "data" / "weak_supervision" / "bird_crops" / "metadata.json"

CONF_THRESHOLD = 0.25
FAST_MODE = False  # Use SAHI mode for better accuracy
SAVE_INTERVAL = 100  # Save progress every N images


def load_image_metadata(metadata_file: Path) -> dict:
    """Load image metadata from Phase 3a (batch_download.py)"""
    with open(metadata_file, 'r') as f:
        metadata = json.load(f)
    print(f"✓ Loaded metadata for {len(metadata):,} images")
    return metadata


def load_existing_crops(crop_metadata_file: Path) -> set:
    """
    Load existing crop metadata to support resume functionality.

    Returns:
        set of photo_ids that have already been processed
    """
    if not crop_metadata_file.exists():
        return set()

    try:
        with open(crop_metadata_file, 'r') as f:
            existing_crops = json.load(f)

        # Extract photo_ids that have been processed
        processed_photos = set(crop['photo_id'] for crop in existing_crops)
        print(f"✓ Found {len(existing_crops):,} existing crops from {len(processed_photos):,} photos")
        print(f"   Will skip these photos and resume from where we left off")
        return processed_photos
    except Exception as e:
        print(f"⚠️ Error loading existing crops: {e}")
        return set()


def extract_bird_crop(image: np.ndarray, bbox: Tuple[int, int, int, int],
                      padding: float = 0.05) -> np.ndarray:
    """
    Extract bird crop from image with padding.

    Args:
        image: Full image (H, W, C)
        bbox: (x1, y1, x2, y2) in pixel coordinates
        padding: Fraction of bbox size to add as padding (default 5%)

    Returns:
        Cropped image region
    """
    x1, y1, x2, y2 = bbox
    height, width = image.shape[:2]

    # Calculate padding
    bbox_width = x2 - x1
    bbox_height = y2 - y1
    pad_x = int(bbox_width * padding)
    pad_y = int(bbox_height * padding)

    # Apply padding with bounds checking
    x1 = max(0, x1 - pad_x)
    y1 = max(0, y1 - pad_y)
    x2 = min(width, x2 + pad_x)
    y2 = min(height, y2 + pad_y)

    return image[y1:y2, x1:x2]


def process_images(detector: BirdDetector, image_metadata: dict,
                   processed_photos: set) -> List[Dict]:
    """
    Run detection on all images and extract crops.

    Args:
        detector: BirdDetector instance
        image_metadata: Image metadata dict from batch_download.py
        processed_photos: Set of photo_ids already processed (for resume)

    Returns:
        List of crop metadata entries
    """
    crop_metadata = []
    crop_counter = 0

    # Filter out already processed photos
    photos_to_process = {
        photo_id: meta for photo_id, meta in image_metadata.items()
        if photo_id not in processed_photos
    }

    if len(photos_to_process) == 0:
        print("✓ All photos already processed!")
        return crop_metadata

    print(f"\n🔍 Running detection on {len(photos_to_process):,} images...")
    print(f"   Detection mode: {'FAST' if FAST_MODE else 'SAHI (accurate)'}")
    print(f"   Confidence threshold: {CONF_THRESHOLD}")
    print(f"   Saving progress every {SAVE_INTERVAL} images")

    processed_count = 0
    failed_count = 0

    for photo_id, metadata in tqdm(photos_to_process.items(), desc="Detecting"):
        image_path = PROJECT_ROOT / metadata['image_path']

        try:
            # Run detection
            result = detector.predict(
                str(image_path),
                conf_threshold=CONF_THRESHOLD,
                fast_mode=FAST_MODE
            )

            # Load image for crop extraction
            image = cv2.imread(str(image_path))
            if image is None:
                failed_count += 1
                continue

            detections = result['detections']

            # Extract each bird crop
            for detection in detections:
                bbox = detection['bbox']  # [x1, y1, x2, y2]
                confidence = detection['confidence']

                # Extract crop
                crop = extract_bird_crop(image, bbox, padding=0.05)

                # Skip if crop is too small (likely a detection error)
                if crop.shape[0] < 10 or crop.shape[1] < 10:
                    continue

                # Save crop
                crop_id = f"bird_{crop_counter:06d}"
                crop_path = CROPS_DIR / f"{crop_id}.jpg"
                cv2.imwrite(str(crop_path), crop)

                # Build crop metadata entry
                crop_entry = {
                    'crop_id': crop_id,
                    'photo_id': photo_id,
                    'image_path': metadata['image_path'],
                    's3_path': metadata['s3_path'],
                    'bbox': bbox,
                    'confidence': confidence,
                    'species_candidates': metadata['species_codes'],
                    'species_count': metadata['species_count'],
                    'is_single_species': metadata['is_single_species'],
                    'metadata': {
                        'year': metadata['metadata']['year'],
                        'camera': metadata['metadata']['camera'],
                        'card': metadata['metadata']['card'],
                        'colony': metadata['metadata']['colony'],
                        'date': metadata['metadata']['date'],
                        'photo_num': metadata['metadata']['photo_num']
                    }
                }

                crop_metadata.append(crop_entry)
                crop_counter += 1

            processed_count += 1

            # Save progress periodically
            if processed_count % SAVE_INTERVAL == 0:
                save_progress(crop_metadata)
                print(f"   💾 Progress saved: {len(crop_metadata):,} crops from {processed_count:,} images")

        except Exception as e:
            print(f"  ⚠️ Detection failed for {photo_id}: {e}")
            failed_count += 1
            continue

    print(f"\n✓ Detection complete!")
    print(f"   Processed: {processed_count:,} images")
    print(f"   Failed: {failed_count:,} images")
    print(f"   Total crops: {len(crop_metadata):,}")

    return crop_metadata


def save_progress(crop_metadata: List[Dict]):
    """Save crop metadata to disk"""
    with open(CROP_METADATA_FILE, 'w') as f:
        json.dump(crop_metadata, f, indent=2)


def analyze_crop_distribution(crop_metadata: List[Dict]):
    """
    Analyze crop distribution and species balance.

    Returns statistics about crops and species coverage.
    """
    total_crops = len(crop_metadata)

    # Single-species vs multi-species crops
    single_species_crops = [c for c in crop_metadata if c['is_single_species']]
    multi_species_crops = [c for c in crop_metadata if not c['is_single_species']]

    # Species distribution (from single-species crops only - these are ground truth)
    species_crop_count = defaultdict(int)
    for crop in single_species_crops:
        species = crop['species_candidates'][0]
        species_crop_count[species] += 1

    species_sorted = sorted(species_crop_count.items(), key=lambda x: x[1], reverse=True)

    # Confidence distribution
    confidences = [c['confidence'] for c in crop_metadata]
    high_conf = sum(1 for c in confidences if c >= 0.7)
    med_conf = sum(1 for c in confidences if 0.4 <= c < 0.7)
    low_conf = sum(1 for c in confidences if c < 0.4)

    return {
        'total_crops': total_crops,
        'single_species_crops': len(single_species_crops),
        'multi_species_crops': len(multi_species_crops),
        'species_distribution': dict(species_sorted),
        'species_sorted': species_sorted,
        'confidence_stats': {
            'high_conf_count': high_conf,
            'med_conf_count': med_conf,
            'low_conf_count': low_conf,
            'avg_confidence': np.mean(confidences) if confidences else 0
        }
    }


def main():
    """Main detection workflow"""
    print("=" * 70)
    print("🔍 BATCH DETECTION - PHASE 3b")
    print("=" * 70)
    print(f"Source metadata: {IMAGE_METADATA_FILE}")
    print(f"Output directory: {CROPS_DIR}/")

    # Setup
    CROPS_DIR.mkdir(exist_ok=True, parents=True)

    # Step 1: Load image metadata
    print(f"\n[1/4] Loading image metadata...")
    image_metadata = load_image_metadata(IMAGE_METADATA_FILE)

    # Step 2: Check for existing crops (resume support)
    print(f"\n[2/4] Checking for existing crops...")
    processed_photos = load_existing_crops(CROP_METADATA_FILE)

    if len(processed_photos) >= len(image_metadata):
        print("\n✅ All images already processed! No work to do.")
        print(f"   Crop metadata: {CROP_METADATA_FILE}")
        return

    # Step 3: Initialize detector
    print(f"\n[3/4] Initializing YOLO detector...")
    detector = BirdDetector()
    print(f"✓ Detector ready")

    # Step 4: Process images
    print(f"\n[4/4] Running detection and extracting crops...")
    crop_metadata = process_images(detector, image_metadata, processed_photos)

    # Final save
    print(f"\n💾 Saving final crop metadata...")
    save_progress(crop_metadata)

    # Analyze and report
    print(f"\n" + "=" * 70)
    print("📊 DETECTION COMPLETE")
    print("=" * 70)

    stats = analyze_crop_distribution(crop_metadata)

    print(f"Total crops extracted:      {stats['total_crops']:,}")
    print(f"  Single-species crops:     {stats['single_species_crops']:,} (ground truth)")
    print(f"  Multi-species crops:      {stats['multi_species_crops']:,} (need weak supervision)")
    print()

    conf_stats = stats['confidence_stats']
    print(f"Confidence distribution:")
    print(f"  High (≥0.7):              {conf_stats['high_conf_count']:,} ({conf_stats['high_conf_count']/stats['total_crops']*100:.1f}%)")
    print(f"  Medium (0.4-0.7):         {conf_stats['med_conf_count']:,} ({conf_stats['med_conf_count']/stats['total_crops']*100:.1f}%)")
    print(f"  Low (<0.4):               {conf_stats['low_conf_count']:,} ({conf_stats['low_conf_count']/stats['total_crops']*100:.1f}%)")
    print(f"  Average confidence:       {conf_stats['avg_confidence']:.3f}")
    print()

    print(f"Top 10 species (from single-species crops only):")
    for i, (species, count) in enumerate(stats['species_sorted'][:10], 1):
        pct = count / stats['single_species_crops'] * 100 if stats['single_species_crops'] > 0 else 0
        print(f"  {i:2}. {species}: {count:,} crops ({pct:.1f}%)")
    print()

    print(f"💾 Crop metadata: {CROP_METADATA_FILE}")
    print(f"📁 Crops: {CROPS_DIR}/")
    print()
    print("=" * 70)
    print("✅ NEXT STEP: Run Phase 4 (embedding extraction & clustering)")
    print("=" * 70)
    print()


if __name__ == "__main__":
    main()
