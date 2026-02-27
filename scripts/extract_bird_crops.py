#!/usr/bin/env python3
"""
Extract Bird Crops from YOLO Dataset

This script extracts individual bird images from labeled dataset by cropping
bounding boxes and saving them to a structured folder.

Output structure:
    bird_crops/
        ├── bird_0000.jpg (first bird)
        ├── bird_0001.jpg
        ├── ...
        └── metadata.json (contains source image, bbox info)

This prepares data for:
- Feature extraction and clustering
- t-SNE visualization
- Classification model training
"""

import cv2
import numpy as np
import json
from pathlib import Path
from typing import List, Dict
import argparse
from tqdm import tqdm


class BirdCropExtractor:
    """
    Extracts individual bird crops from YOLO-labeled images.

    Workflow:
    1. Read YOLO labels (normalized bbox coordinates)
    2. Load corresponding images
    3. Crop each bird using bbox
    4. Save crops with metadata
    5. Generate statistics
    """

    def __init__(self, data_dir: str, output_dir: str = None,
                 min_size: int = 20, max_size: int = 10000):
        """
        Args:
            data_dir: Path to YOLO dataset (contains images/ and labels/)
            output_dir: Where to save bird crops (default: data_dir/bird_crops)
            min_size: Minimum crop size in pixels (filters out tiny boxes)
            max_size: Maximum crop size in pixels (filters out whole-image boxes)
        """
        self.data_dir = Path(data_dir)
        self.images_dir = self.data_dir / "images"
        self.labels_dir = self.data_dir / "labels"

        # Output directory
        if output_dir:
            self.output_dir = Path(output_dir)
        else:
            self.output_dir = self.data_dir / "bird_crops"

        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.min_size = min_size
        self.max_size = max_size

        # Track metadata for each crop
        self.metadata = []

    def extract_all_crops(self, resize: int = None):
        """
        Extract all bird crops from the dataset.

        Args:
            resize: If specified, resize all crops to this size (e.g., 224 for ResNet)
        """
        print("=" * 60)
        print("🦅 EXTRACTING BIRD CROPS")
        print("=" * 60)
        print(f"Dataset: {self.data_dir}")
        print(f"Output: {self.output_dir}")
        print(f"Min size: {self.min_size}px")
        print(f"Max size: {self.max_size}px")
        if resize:
            print(f"Resize to: {resize}x{resize}px")
        print()

        # Find all label files
        label_files = list(self.labels_dir.glob("*.txt"))
        print(f"Found {len(label_files)} labeled images\n")

        crop_count = 0
        skipped_count = 0

        # Process each image
        for label_file in tqdm(label_files, desc="Extracting crops"):
            # Find corresponding image
            image_name = label_file.stem
            image_file = self._find_image_file(image_name)

            if not image_file:
                continue

            # Load image
            image = cv2.imread(str(image_file))
            if image is None:
                continue

            height, width = image.shape[:2]

            # Read YOLO labels
            with open(label_file, 'r') as f:
                lines = f.readlines()

            # Extract each bird
            for bbox_idx, line in enumerate(lines):
                parts = line.strip().split()
                if len(parts) < 5:
                    continue

                # YOLO format: class_id x_center y_center width height [species]
                try:
                    class_id = int(parts[0])
                    x_center, y_center, box_w, box_h = map(float, parts[1:5])
                    species = parts[5] if len(parts) > 5 else None
                except (ValueError, IndexError):
                    continue

                # Convert normalized coords to pixel coords
                x_center_px = int(x_center * width)
                y_center_px = int(y_center * height)
                box_w_px = int(box_w * width)
                box_h_px = int(box_h * height)

                # Get bbox corners
                x1 = max(0, x_center_px - box_w_px // 2)
                y1 = max(0, y_center_px - box_h_px // 2)
                x2 = min(width, x_center_px + box_w_px // 2)
                y2 = min(height, y_center_px + box_h_px // 2)

                # Filter by size
                crop_width = x2 - x1
                crop_height = y2 - y1

                if crop_width < self.min_size or crop_height < self.min_size:
                    skipped_count += 1
                    continue

                if crop_width > self.max_size or crop_height > self.max_size:
                    skipped_count += 1
                    continue

                # Crop bird
                crop = image[y1:y2, x1:x2]

                # Resize if requested
                if resize:
                    crop = cv2.resize(crop, (resize, resize),
                                    interpolation=cv2.INTER_AREA)

                # Save crop
                crop_filename = f"bird_{crop_count:06d}.jpg"
                crop_path = self.output_dir / crop_filename
                cv2.imwrite(str(crop_path), crop,
                           [cv2.IMWRITE_JPEG_QUALITY, 95])

                # Store metadata
                self.metadata.append({
                    'crop_id': crop_count,
                    'crop_filename': crop_filename,
                    'source_image': image_name,
                    'source_image_path': str(image_file),
                    'bbox_index': bbox_idx,
                    'class_id': class_id,
                    'bbox_pixel': [x1, y1, x2, y2],
                    'bbox_yolo': [x_center, y_center, box_w, box_h],
                    'crop_size': [crop_width, crop_height],
                    'species': species
                })

                crop_count += 1

        # Save metadata
        metadata_file = self.output_dir / "metadata.json"
        with open(metadata_file, 'w') as f:
            json.dump({
                'total_crops': crop_count,
                'skipped_crops': skipped_count,
                'source_dataset': str(self.data_dir),
                'min_size': self.min_size,
                'max_size': self.max_size,
                'resize': resize,
                'crops': self.metadata
            }, f, indent=2)

        print()
        print("=" * 60)
        print("✅ EXTRACTION COMPLETE")
        print("=" * 60)
        print(f"Total crops: {crop_count}")
        print(f"Skipped (too small/large): {skipped_count}")
        print(f"Output directory: {self.output_dir}")
        print(f"Metadata: {metadata_file}")
        print("=" * 60)

        # Generate statistics
        self._generate_statistics()

    def _find_image_file(self, image_name: str):
        """Find image file with various extensions"""
        for ext in ['.jpg', '.jpeg', '.png', '.JPG', '.JPEG', '.PNG']:
            image_file = self.images_dir / f"{image_name}{ext}"
            if image_file.exists():
                return image_file
        return None

    def _generate_statistics(self):
        """Generate statistics about extracted crops"""
        if not self.metadata:
            return

        # Count by source image
        images = set(m['source_image'] for m in self.metadata)

        # Size distribution
        widths = [m['crop_size'][0] for m in self.metadata]
        heights = [m['crop_size'][1] for m in self.metadata]

        # Species distribution (if available)
        species_counts = {}
        for m in self.metadata:
            if m['species']:
                species_counts[m['species']] = species_counts.get(m['species'], 0) + 1

        print("\n📊 STATISTICS")
        print("-" * 60)
        print(f"Source images: {len(images)}")
        print(f"Birds per image (avg): {len(self.metadata) / len(images):.1f}")
        print(f"\nCrop sizes:")
        print(f"  Width:  {np.mean(widths):.1f}px ± {np.std(widths):.1f}")
        print(f"  Height: {np.mean(heights):.1f}px ± {np.std(heights):.1f}")
        print(f"  Min:    {min(widths)}x{min(heights)}px")
        print(f"  Max:    {max(widths)}x{max(heights)}px")

        if species_counts:
            print(f"\nSpecies labels found: {len(species_counts)}")
            print("Top 10 species:")
            for species, count in sorted(species_counts.items(),
                                        key=lambda x: x[1], reverse=True)[:10]:
                print(f"  {species:10s}: {count:5d} birds")
        else:
            print("\nNo species labels found in dataset")


def main():
    parser = argparse.ArgumentParser(
        description="Extract individual bird crops from YOLO dataset",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic extraction
  python extract_bird_crops.py --data labeller/nestvision

  # Extract and resize for classification model
  python extract_bird_crops.py --data labeller/nestvision --resize 224

  # Custom output directory
  python extract_bird_crops.py --data labeller/nestvision --output /tmp/crops

  # Filter by size
  python extract_bird_crops.py --data labeller/nestvision --min-size 50 --max-size 500
        """
    )

    parser.add_argument('--data', type=str, required=True,
                       help='Path to YOLO dataset directory (contains images/ and labels/)')
    parser.add_argument('--output', type=str, default=None,
                       help='Output directory for crops (default: data/bird_crops)')
    parser.add_argument('--resize', type=int, default=None,
                       help='Resize all crops to NxN pixels (e.g., 224 for ResNet)')
    parser.add_argument('--min-size', type=int, default=20,
                       help='Minimum crop size in pixels (default: 20)')
    parser.add_argument('--max-size', type=int, default=10000,
                       help='Maximum crop size in pixels (default: 10000)')

    args = parser.parse_args()

    # Create extractor
    extractor = BirdCropExtractor(
        data_dir=args.data,
        output_dir=args.output,
        min_size=args.min_size,
        max_size=args.max_size
    )

    # Extract crops
    extractor.extract_all_crops(resize=args.resize)

    print("\n🎯 NEXT STEPS:")
    print("-" * 60)
    print("1. Run feature extraction and clustering:")
    print("   python scripts/cluster_birds.py --data labeller/nestvision --clusters 30")
    print()
    print("2. Explore clusters in visualization:")
    print("   python labeller/app.py --data labeller/nestvision")
    print("   Then open: http://localhost:5000/clusters")
    print()
    print("3. Train classification model:")
    print("   python scripts/train_classifier.py --crops labeller/nestvision/bird_crops")
    print("-" * 60)


if __name__ == '__main__':
    main()
