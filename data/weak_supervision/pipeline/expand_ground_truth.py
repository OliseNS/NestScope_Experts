#!/usr/bin/env python3
"""
Expand Ground Truth: Process Unprocessed Single-Species Images

This script detects and crops birds from the 1,631 single-species images
that were downloaded but never processed. These provide high-quality ground
truth labels because each image contains only one species.

Why this matters:
  - Original pipeline processed 1,045 images → 100,026 crops
  - Only 143 of those were single-species → ground truth for 9 species
  - There are 1,631 MORE single-species images already downloaded
  - Processing them expands ground truth from 9 → 30 species
  - More ground truth = better Hungarian matching = more accurate labels

What this script does:
  1. Finds all single-species images that haven't been processed yet
  2. Runs Swift YOLO detection on each (same settings as original pipeline)
  3. Extracts bird crops with 5% padding
  4. Appends new crops to existing metadata.json (crop IDs continue from 100,026)
  5. Updates processing_log.json and image_metadata.json

Usage:
    python expand_ground_truth.py                    # Process all unprocessed single-species images
    python expand_ground_truth.py --dry-run           # Preview what would be processed
    python expand_ground_truth.py --resume            # Resume if interrupted
"""

import json
import cv2
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import sys
import argparse
from datetime import datetime
from collections import Counter

# Add project root to Python path
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.append(str(PROJECT_ROOT))

from server.cv_tools.inference import BirdDetector

try:
    from tqdm import tqdm
    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False

# Paths
DATA_DIR = PROJECT_ROOT / "data" / "weak_supervision"
MAPPINGS_FILE = DATA_DIR / "photo_mappings_2015_2021.json"
IMAGE_METADATA_FILE = DATA_DIR / "image_metadata.json"
DOWNLOAD_DIR = DATA_DIR / "downloaded_images"
CROPS_DIR = DATA_DIR / "bird_crops" / "images"
METADATA_FILE = DATA_DIR / "bird_crops" / "metadata.json"
PROGRESS_LOG = DATA_DIR / "bird_crops" / "processing_log.json"

# How often to save progress (in case of interruption)
SAVE_INTERVAL = 25


def load_unprocessed_single_species() -> Tuple[List[Dict], set]:
    """
    Find single-species images that haven't been processed yet.

    Returns:
        Tuple of (list of unprocessed photo mappings, set of already-processed IDs)
    """
    # Load all photo mappings
    with open(MAPPINGS_FILE, 'r') as f:
        mappings = json.load(f)

    # Load processing log to see what's done
    with open(PROGRESS_LOG, 'r') as f:
        log = json.load(f)
    processed_ids = set(log.get('processed_photos', []))

    # Filter: single-species AND not yet processed
    unprocessed = [
        m for m in mappings
        if m['species_count'] == 1 and m['photo_id'] not in processed_ids
    ]

    return unprocessed, processed_ids


def extract_crop(image: np.ndarray, bbox: Tuple[int, int, int, int],
                 padding: float = 0.05) -> Optional[np.ndarray]:
    """
    Extract a bird crop from the full image with padding.

    Same logic as the original pipeline for consistency.

    Args:
        image: Full image array (H, W, C)
        bbox: (x1, y1, x2, y2) pixel coordinates from YOLO
        padding: Extra space around the bird (5% of bbox size)

    Returns:
        Cropped image, or None if too small (< 50x50 pixels)
    """
    x1, y1, x2, y2 = bbox
    height, width = image.shape[:2]

    bbox_width = x2 - x1
    bbox_height = y2 - y1

    pad_x = int(bbox_width * padding)
    pad_y = int(bbox_height * padding)

    # Clamp to image bounds
    x1_padded = max(0, x1 - pad_x)
    y1_padded = max(0, y1 - pad_y)
    x2_padded = min(width, x2 + pad_x)
    y2_padded = min(height, y2 + pad_y)

    crop = image[y1_padded:y2_padded, x1_padded:x2_padded]

    # Reject tiny crops (likely false positives)
    if crop.shape[0] < 50 or crop.shape[1] < 50:
        return None

    return crop


def run_expansion(dry_run: bool = False, resume: bool = False):
    """
    Main function: process all unprocessed single-species images.

    Args:
        dry_run: If True, just show what would be processed without doing it
        resume: If True, check for partially-completed expansion
    """
    print("=" * 70)
    print("EXPAND GROUND TRUTH: Process Unprocessed Single-Species Images")
    print("=" * 70)

    # Find what needs processing
    unprocessed, processed_ids = load_unprocessed_single_species()

    # Show breakdown by species
    species_counts = Counter()
    for m in unprocessed:
        species_counts[m['species_codes'][0]] += 1

    print(f"\nUnprocessed single-species images: {len(unprocessed)}")
    print(f"Already processed: {len(processed_ids)} images total")
    print(f"\nSpecies breakdown ({len(species_counts)} species):")
    for sp, count in species_counts.most_common():
        print(f"  {sp}: {count} images")

    if dry_run:
        print("\n[DRY RUN] Would process these images. Exiting.")
        return

    if not unprocessed:
        print("\nNothing to process - all single-species images are done!")
        return

    # Load existing metadata to append to
    print("\nLoading existing crop metadata...")
    with open(METADATA_FILE, 'r') as f:
        existing_data = json.load(f)
    existing_crops = existing_data.get('crops', [])
    start_crop_id = len(existing_crops)

    with open(PROGRESS_LOG, 'r') as f:
        processing_log = json.load(f)

    print(f"  Existing crops: {len(existing_crops):,}")
    print(f"  New crops will start at ID: {start_crop_id}")

    # Initialize detector
    print("\nInitializing YOLO detector (Swift model)...")
    detector = BirdDetector()
    print("  Detector ready")

    # Process images
    print(f"\nProcessing {len(unprocessed)} images...")
    current_crop_id = start_crop_id
    new_crops = []
    images_processed = 0
    images_failed = 0
    total_detections = 0

    if HAS_TQDM:
        pbar = tqdm(unprocessed, desc="Processing images", unit="img")
    else:
        pbar = unprocessed

    for mapping in pbar:
        photo_id = mapping['photo_id']
        species = mapping['species_codes']
        s3_key = mapping['s3_key']

        # Find the downloaded image
        extension = Path(s3_key).suffix
        image_path = DOWNLOAD_DIR / f"{photo_id}{extension}"

        if not image_path.exists():
            if not HAS_TQDM:
                print(f"  SKIP {photo_id}: image not found at {image_path}")
            images_failed += 1
            continue

        # Load image
        image = cv2.imread(str(image_path))
        if image is None:
            if not HAS_TQDM:
                print(f"  SKIP {photo_id}: failed to read image")
            images_failed += 1
            continue

        height, width = image.shape[:2]

        # Run detection (Swift model, 0.30 confidence, SAHI for large images)
        result = detector.predict(
            str(image_path),
            conf_threshold=0.30,
            use_sliding_window=True,
            fast_mode=True,
            verbose=False
        )

        detections = result.get('detections', [])
        total_detections += len(detections)

        # Extract crops
        for det in detections:
            bbox = det.get('bbox')
            confidence = det.get('confidence')

            if bbox is None or len(bbox) != 4:
                continue

            x1, y1, x2, y2 = bbox
            crop = extract_crop(image, (int(x1), int(y1), int(x2), int(y2)))
            if crop is None:
                continue

            # Save crop image
            crop_filename = f"bird_{current_crop_id:06d}.jpg"
            crop_path = CROPS_DIR / crop_filename
            cv2.imwrite(str(crop_path), crop, [cv2.IMWRITE_JPEG_QUALITY, 95])

            # Store metadata (same format as original pipeline)
            crop_metadata = {
                'crop_id': current_crop_id,
                'crop_filename': crop_filename,
                'source_photo_id': photo_id,
                'bbox_pixel': [int(x1), int(y1), int(x2), int(y2)],
                'bbox_yolo': [
                    float((x1 + x2) / 2 / width),
                    float((y1 + y2) / 2 / height),
                    float((x2 - x1) / width),
                    float((y2 - y1) / height)
                ],
                'confidence': float(confidence),
                'species_candidates': species,
                'is_single_species': True,
                'image_size': [width, height]
            }
            new_crops.append(crop_metadata)
            current_crop_id += 1

        # Mark as processed
        processing_log['processed_photos'].append(photo_id)
        images_processed += 1

        # Update progress bar
        if HAS_TQDM:
            pbar.set_postfix({
                'crops': len(new_crops),
                'det': total_detections,
                'species': species[0]
            })

        # Save periodically
        if images_processed % SAVE_INTERVAL == 0:
            _save_progress(existing_crops, new_crops, processing_log)

    if HAS_TQDM:
        pbar.close()

    # Final save
    print("\nSaving final results...")
    _save_progress(existing_crops, new_crops, processing_log)

    # Update image_metadata.json to include newly-processed images
    _update_image_metadata(unprocessed)

    # Summary
    print("\n" + "=" * 70)
    print("EXPANSION COMPLETE")
    print("=" * 70)
    print(f"  Images processed:    {images_processed}")
    print(f"  Images failed:       {images_failed}")
    print(f"  New crops extracted:  {len(new_crops):,}")
    print(f"  Total detections:    {total_detections:,}")
    print(f"  Total crops now:     {len(existing_crops) + len(new_crops):,}")
    print(f"    Old crops:         {len(existing_crops):,}")
    print(f"    New crops:         {len(new_crops):,}")

    # New species breakdown
    new_species_counts = Counter()
    for crop in new_crops:
        new_species_counts[crop['species_candidates'][0]] += 1

    print(f"\nNew crops by species ({len(new_species_counts)} species):")
    for sp, count in new_species_counts.most_common():
        print(f"  {sp}: {count:,} crops")

    print(f"\nCrop IDs: {start_crop_id} → {current_crop_id - 1}")
    print(f"\nNext steps:")
    print(f"  1. Delete old embeddings, ground_truth, assignments, export:")
    print(f"     rm -rf data/weak_supervision/bird_crops/{{embeddings,ground_truth,assignments,export}}")
    print(f"  2. Re-run full pipeline:")
    print(f"     python data/weak_supervision/pipeline/run_full_pipeline.py --force-restart")
    print(f"  3. Export classification dataset:")
    print(f"     python data/weak_supervision/pipeline/export_classification_dataset.py --min-samples 10")


def _save_progress(existing_crops: list, new_crops: list, processing_log: dict):
    """Save metadata and processing log to disk."""
    all_crops = existing_crops + new_crops
    output_data = {
        'total_crops': len(all_crops),
        'total_images_processed': len(processing_log['processed_photos']),
        'conf_threshold': 0.3,
        'generated_at': datetime.now().isoformat(),
        'crops': all_crops
    }
    with open(METADATA_FILE, 'w') as f:
        json.dump(output_data, f, indent=2)

    processing_log['last_updated'] = datetime.now().isoformat()
    processing_log['total_crops'] = len(all_crops)
    processing_log['last_crop_id'] = len(all_crops) - 1
    with open(PROGRESS_LOG, 'w') as f:
        json.dump(processing_log, f, indent=2)


def _update_image_metadata(newly_processed: List[Dict]):
    """
    Update image_metadata.json to include newly-processed images.

    The clustering pipeline reads this file to know which images exist
    and what species they contain.
    """
    print("Updating image_metadata.json...")

    with open(IMAGE_METADATA_FILE, 'r') as f:
        image_metadata = json.load(f)

    existing_ids = set(image_metadata.keys())
    added = 0

    for mapping in newly_processed:
        photo_id = mapping['photo_id']
        if photo_id not in existing_ids:
            image_metadata[photo_id] = {
                'photo_id': photo_id,
                'species_codes': mapping['species_codes'],
                'species_count': mapping['species_count'],
                'is_single_species': True,
                's3_key': mapping['s3_key'],
                'metadata': mapping.get('metadata', {})
            }
            added += 1

    with open(IMAGE_METADATA_FILE, 'w') as f:
        json.dump(image_metadata, f, indent=2)

    print(f"  Added {added} new entries to image_metadata.json")
    print(f"  Total images in metadata: {len(image_metadata)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Expand ground truth by processing unprocessed single-species images',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Preview what would be processed
  python expand_ground_truth.py --dry-run

  # Process all unprocessed single-species images
  python expand_ground_truth.py

  # Resume if interrupted
  python expand_ground_truth.py --resume
        """
    )
    parser.add_argument('--dry-run', action='store_true',
                        help='Preview without processing')
    parser.add_argument('--resume', action='store_true',
                        help='Resume from interruption')

    args = parser.parse_args()
    run_expansion(dry_run=args.dry_run, resume=args.resume)
