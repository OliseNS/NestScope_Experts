#!/usr/bin/env python3
"""
Detection Pipeline - Phase 3

Processes images with YOLO detection (Swift model @ 0.30 confidence) until reaching 100,000 crops.
Each crop is linked to species candidates from the source image.

Features:
- Resume support (crash recovery)
- Progress tracking with crop count
- Automatic stop at 100K threshold
- Memory efficient (process one image at a time)
- Links each crop to species candidates from database

Usage:
    python run_detection_pipeline.py [--conf 0.30] [--max-crops 100000] [--resume]

Educational Note:
    This script processes images sequentially, running bird detection on each one.
    We extract individual bird "crops" (small images of just the bird) from the full photo.
    Each crop stores which species MIGHT be in it (based on database metadata).
    Later, we'll use clustering to figure out which bird is which species.
"""

import json
import cv2
import numpy as np
import boto3
from botocore import UNSIGNED
from botocore.config import Config
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import sys
import argparse
from datetime import datetime

# Add project root to Python path
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.append(str(PROJECT_ROOT))

from server.cv_tools.inference import BirdDetector

# Optional progress bar
try:
    from tqdm import tqdm
    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False
    print("⚠️  tqdm not installed - progress bars disabled")
    print("   Install with: pip install tqdm")

# Configuration
DATA_DIR = PROJECT_ROOT / "data" / "weak_supervision"
MAPPINGS_FILE = DATA_DIR / "photo_mappings_2015_2021.json"
IMAGE_METADATA_FILE = DATA_DIR / "image_metadata.json"
DOWNLOAD_DIR = DATA_DIR / "downloaded_images"
CROPS_DIR = DATA_DIR / "bird_crops" / "images"
METADATA_FILE = DATA_DIR / "bird_crops" / "metadata.json"
PROGRESS_LOG = DATA_DIR / "bird_crops" / "processing_log.json"

BUCKET_NAME = "twi-aviandata"
SAVE_INTERVAL = 50  # Save progress every N images


class DetectionPipeline:
    """
    Manages the detection pipeline workflow.

    This class handles:
    1. Loading photo mappings (which photos to process)
    2. Downloading images from S3 if needed
    3. Running YOLO detection on each image
    4. Extracting bird crops with metadata
    5. Tracking progress toward 100K crop goal
    6. Resume support for crash recovery
    """

    def __init__(self, conf_threshold: float = 0.30, max_crops: int = 100000):
        """
        Initialize the detection pipeline.

        Args:
            conf_threshold: YOLO confidence threshold (0.30 = 30% confidence)
            max_crops: Stop after reaching this many crops (default: 100,000)
        """
        self.conf_threshold = conf_threshold
        self.max_crops = max_crops

        # Initialize S3 client (public bucket, no auth needed)
        self.s3_client = boto3.client('s3', config=Config(signature_version=UNSIGNED))

        # Initialize YOLO detector (Swift model for speed)
        print("\n🔧 Initializing YOLO detector...")
        self.detector = BirdDetector()
        print("✓ Detector ready (Swift model)")

        # Create output directories
        CROPS_DIR.mkdir(parents=True, exist_ok=True)
        DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

        # Load or initialize metadata
        self.crops_metadata = []
        self.processing_log = {
            'processed_photos': [],
            'total_crops': 0,
            'last_crop_id': -1,
            'started_at': None,
            'last_updated': None
        }

    def load_existing_progress(self) -> bool:
        """
        Load existing progress for resume support.

        Returns:
            True if existing progress was found, False otherwise
        """
        if METADATA_FILE.exists() and PROGRESS_LOG.exists():
            print("\n📂 Found existing progress - loading...")

            # Load crop metadata
            with open(METADATA_FILE, 'r') as f:
                data = json.load(f)
                self.crops_metadata = data.get('crops', [])

            # Load processing log
            with open(PROGRESS_LOG, 'r') as f:
                self.processing_log = json.load(f)

            total_crops = len(self.crops_metadata)
            total_photos = len(self.processing_log['processed_photos'])

            print(f"✓ Loaded {total_crops:,} existing crops from {total_photos:,} photos")
            print(f"  Will resume from crop ID {total_crops}")

            return True

        return False

    def load_photo_mappings(self) -> List[Dict]:
        """
        Load photo mappings from Phase 2.

        Returns:
            List of photo mapping dictionaries
        """
        print(f"\n📋 Loading photo mappings from: {MAPPINGS_FILE.name}")

        with open(MAPPINGS_FILE, 'r') as f:
            mappings = json.load(f)

        print(f"✓ Loaded {len(mappings):,} photo mappings")

        return mappings

    def filter_unprocessed_photos(self, mappings: List[Dict]) -> List[Dict]:
        """
        Filter out photos that have already been processed.

        Args:
            mappings: All photo mappings

        Returns:
            List of unprocessed photo mappings
        """
        if not self.processing_log['processed_photos']:
            return mappings

        processed_set = set(self.processing_log['processed_photos'])
        remaining = [m for m in mappings if m['photo_id'] not in processed_set]

        print(f"📊 Photos already processed: {len(processed_set):,}")
        print(f"📊 Photos remaining: {len(remaining):,}")

        return remaining

    def download_image_if_needed(self, photo_mapping: Dict) -> Optional[Path]:
        """
        Download image from S3 if not already downloaded.

        Args:
            photo_mapping: Photo mapping with S3 key

        Returns:
            Path to local image file, or None if download failed
        """
        photo_id = photo_mapping['photo_id']
        s3_key = photo_mapping['s3_key']

        # Determine file extension
        extension = Path(s3_key).suffix
        local_path = DOWNLOAD_DIR / f"{photo_id}{extension}"

        # Skip if already exists
        if local_path.exists():
            return local_path

        # Download from S3
        try:
            self.s3_client.download_file(BUCKET_NAME, s3_key, str(local_path))
            return local_path
        except Exception as e:
            print(f"  ⚠️  Failed to download {s3_key}: {e}")
            return None

    def run_detection(self, image_path: Path, verbose: bool = False) -> List[Dict]:
        """
        Run YOLO detection on image.

        Args:
            image_path: Path to image file
            verbose: Whether to print detection progress (default: False for batch processing)

        Returns:
            List of detection dictionaries with 'bbox', 'confidence', 'class_id'
        """
        # Run detection with Swift model (fast_mode=True) at specified confidence
        result = self.detector.predict(
            str(image_path),
            conf_threshold=self.conf_threshold,
            use_sliding_window=True,  # Use SAHI for large images
            fast_mode=True,  # Use Swift model
            verbose=verbose  # Suppress output during batch processing
        )

        # Extract detections list from result dictionary
        return result.get('detections', [])

    def extract_crop(self, image: np.ndarray, bbox: Tuple[int, int, int, int],
                     padding: float = 0.05) -> Optional[np.ndarray]:
        """
        Extract bird crop from image with padding.

        Args:
            image: Full image (H, W, C)
            bbox: (x1, y1, x2, y2) in pixel coordinates
            padding: Fraction of bbox size to add as padding (default 5%)

        Returns:
            Cropped image region, or None if invalid
        """
        x1, y1, x2, y2 = bbox
        height, width = image.shape[:2]

        # Calculate padding
        bbox_width = x2 - x1
        bbox_height = y2 - y1

        pad_x = int(bbox_width * padding)
        pad_y = int(bbox_height * padding)

        # Apply padding and clamp to image bounds
        x1_padded = max(0, x1 - pad_x)
        y1_padded = max(0, y1 - pad_y)
        x2_padded = min(width, x2 + pad_x)
        y2_padded = min(height, y2 + pad_y)

        # Extract crop
        crop = image[y1_padded:y2_padded, x1_padded:x2_padded]

        # Validate crop size
        if crop.shape[0] < 50 or crop.shape[1] < 50:
            return None

        return crop

    def process_image(self, photo_mapping: Dict, current_crop_id: int) -> Tuple[int, int]:
        """
        Process a single image: download, detect, extract crops.

        Args:
            photo_mapping: Photo mapping dictionary
            current_crop_id: Starting crop ID for this image

        Returns:
            Tuple of (crops_extracted, next_crop_id)
        """
        photo_id = photo_mapping['photo_id']
        species_candidates = photo_mapping['species_codes']
        is_single_species = len(species_candidates) == 1

        # Download image if needed
        image_path = self.download_image_if_needed(photo_mapping)
        if image_path is None:
            return 0, current_crop_id

        # Load image
        image = cv2.imread(str(image_path))
        if image is None:
            print(f"  ⚠️  Failed to read image: {image_path}")
            return 0, current_crop_id

        height, width = image.shape[:2]

        # Run detection (silent mode for batch processing)
        detections = self.run_detection(image_path, verbose=False)

        if not detections:
            return 0, current_crop_id

        # Extract crops
        crops_extracted = 0
        for detection in detections:
            # Parse detection dictionary
            # Format: {'bbox': [x1, y1, x2, y2], 'confidence': float, 'class_id': int}
            bbox = detection.get('bbox')
            confidence = detection.get('confidence')

            if bbox is None or len(bbox) != 4:
                continue

            x1, y1, x2, y2 = bbox

            # Extract crop
            crop = self.extract_crop(image, (int(x1), int(y1), int(x2), int(y2)))
            if crop is None:
                continue

            # Save crop
            crop_filename = f"bird_{current_crop_id:06d}.jpg"
            crop_path = CROPS_DIR / crop_filename
            cv2.imwrite(str(crop_path), crop, [cv2.IMWRITE_JPEG_QUALITY, 95])

            # Store metadata
            crop_metadata = {
                'crop_id': current_crop_id,
                'crop_filename': crop_filename,
                'source_photo_id': photo_id,
                'bbox_pixel': [int(x1), int(y1), int(x2), int(y2)],
                'bbox_yolo': [
                    float((x1 + x2) / 2 / width),   # x_center
                    float((y1 + y2) / 2 / height),  # y_center
                    float((x2 - x1) / width),        # width
                    float((y2 - y1) / height)        # height
                ],
                'confidence': float(confidence),
                'species_candidates': species_candidates,
                'is_single_species': is_single_species,
                'image_size': [width, height]
            }

            self.crops_metadata.append(crop_metadata)

            current_crop_id += 1
            crops_extracted += 1

        return crops_extracted, current_crop_id

    def save_progress(self):
        """Save current progress to disk."""
        # Save crop metadata
        output_data = {
            'total_crops': len(self.crops_metadata),
            'total_images_processed': len(self.processing_log['processed_photos']),
            'conf_threshold': self.conf_threshold,
            'generated_at': datetime.now().isoformat(),
            'crops': self.crops_metadata
        }

        with open(METADATA_FILE, 'w') as f:
            json.dump(output_data, f, indent=2)

        # Save processing log
        self.processing_log['last_updated'] = datetime.now().isoformat()
        with open(PROGRESS_LOG, 'w') as f:
            json.dump(self.processing_log, f, indent=2)

    def run(self, resume: bool = False):
        """
        Run the complete detection pipeline.

        Args:
            resume: If True, resume from existing progress
        """
        print("=" * 70)
        print("🦅 DETECTION PIPELINE - PHASE 3")
        print("=" * 70)
        print(f"Goal: Extract {self.max_crops:,} bird crops")
        print(f"Confidence threshold: {self.conf_threshold}")
        print(f"Model: Swift (fast mode)")
        print(f"Output directory: {CROPS_DIR}")
        print("=" * 70)

        # Load existing progress if resuming
        if resume:
            self.load_existing_progress()

        # Initialize start time if new run
        if self.processing_log['started_at'] is None:
            self.processing_log['started_at'] = datetime.now().isoformat()

        # Load photo mappings
        photo_mappings = self.load_photo_mappings()

        # Filter out already processed photos
        remaining_photos = self.filter_unprocessed_photos(photo_mappings)

        if not remaining_photos:
            print("\n✅ All photos already processed!")
            return

        # Current crop ID
        current_crop_id = len(self.crops_metadata)

        print(f"\n🚀 Starting processing...")
        print(f"   Starting crop ID: {current_crop_id}")
        print(f"   Target: {self.max_crops:,} crops")
        print(f"   Remaining to process: {self.max_crops - current_crop_id:,} crops")
        print()

        # Progress tracking
        images_processed = 0

        # Create progress bar if available
        if HAS_TQDM:
            pbar = tqdm(
                total=self.max_crops,
                initial=current_crop_id,
                desc="Extracting crops",
                unit="crops",
                position=0,
                leave=True,
                dynamic_ncols=True,
                mininterval=0.5  # Update every 0.5 seconds max
            )

        # Process images
        for photo_mapping in remaining_photos:
            photo_id = photo_mapping['photo_id']

            # Process this image
            crops_extracted, current_crop_id = self.process_image(
                photo_mapping,
                current_crop_id
            )

            # Update progress
            if crops_extracted > 0:
                images_processed += 1
                self.processing_log['processed_photos'].append(photo_id)

                if HAS_TQDM:
                    pbar.update(crops_extracted)
                else:
                    total_crops = len(self.crops_metadata)
                    print(f"  [{total_crops:,}/{self.max_crops:,}] Processed {photo_id}: +{crops_extracted} crops")

                # Save progress periodically
                if images_processed % SAVE_INTERVAL == 0:
                    self.save_progress()

            # Check if we've reached the goal
            if len(self.crops_metadata) >= self.max_crops:
                print(f"\n🎯 Goal reached! Extracted {len(self.crops_metadata):,} crops")
                break

        if HAS_TQDM:
            pbar.close()

        # Final save
        print("\n💾 Saving final results...")
        self.save_progress()

        # Generate statistics
        total_crops = len(self.crops_metadata)
        total_photos = len(self.processing_log['processed_photos'])
        single_species = sum(1 for c in self.crops_metadata if c['is_single_species'])
        multi_species = total_crops - single_species

        print("\n" + "=" * 70)
        print("✅ PIPELINE COMPLETE!")
        print("=" * 70)
        print(f"Total crops extracted:     {total_crops:,}")
        print(f"Total images processed:    {total_photos:,}")
        print(f"Average crops per image:   {total_crops / total_photos:.1f}")
        print()
        print(f"Single-species crops:      {single_species:,} ({single_species/total_crops*100:.1f}%)")
        print(f"Multi-species crops:       {multi_species:,} ({multi_species/total_crops*100:.1f}%)")
        print()
        print(f"📁 Crops saved to:         {CROPS_DIR}/")
        print(f"📄 Metadata saved to:      {METADATA_FILE}")
        print(f"📊 Processing log:         {PROGRESS_LOG}")
        print("=" * 70)
        print()
        print("🎯 Next step: Run species assignment pipeline")
        print("   python pipeline/run_species_assignment.py")
        print()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Detection Pipeline - Extract bird crops with species linkage",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Start fresh run (default: 0.30 confidence, 100K crops)
  python run_detection_pipeline.py

  # Resume from interruption
  python run_detection_pipeline.py --resume

  # Custom settings
  python run_detection_pipeline.py --conf 0.25 --max-crops 150000
        """
    )

    parser.add_argument('--conf', type=float, default=0.30,
                       help='YOLO confidence threshold (default: 0.30)')
    parser.add_argument('--max-crops', type=int, default=100000,
                       help='Stop after extracting this many crops (default: 100000)')
    parser.add_argument('--resume', action='store_true',
                       help='Resume from existing progress')

    args = parser.parse_args()

    # Validate arguments
    if args.conf < 0.1 or args.conf > 0.9:
        print("⚠️  Warning: Confidence threshold should be between 0.1 and 0.9")
        print(f"   You specified: {args.conf}")
        response = input("   Continue anyway? (y/n): ")
        if response.lower() != 'y':
            return

    # Create and run pipeline
    pipeline = DetectionPipeline(
        conf_threshold=args.conf,
        max_crops=args.max_crops
    )

    try:
        pipeline.run(resume=args.resume)
    except KeyboardInterrupt:
        print("\n\n⚠️  Pipeline interrupted by user")
        print("💾 Saving progress...")
        pipeline.save_progress()
        print("✓ Progress saved. Run with --resume to continue from here.")
    except Exception as e:
        print(f"\n\n❌ Pipeline failed with error: {e}")
        print("💾 Attempting to save progress...")
        try:
            pipeline.save_progress()
            print("✓ Progress saved. Run with --resume to continue from here.")
        except:
            print("⚠️  Could not save progress")
        raise


if __name__ == "__main__":
    main()
