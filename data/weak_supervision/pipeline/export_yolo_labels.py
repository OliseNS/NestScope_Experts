#!/usr/bin/env python3
"""
Export YOLO Labels for Bird Detection Training

Reads the crop metadata and generates YOLO format label files for the parent images.
All birds are labeled as class 0 (single "bird" class for detection, not classification).

Output:
- labels/PHOTO_ID.txt - YOLO label files (one per parent image)
- classes.txt - Class mapping (just "bird")
- dataset.yaml - YOLO dataset configuration

Usage:
    python export_yolo_labels.py [--min-confidence 0.3] [--output labels/]
"""

import json
from pathlib import Path
from collections import defaultdict
from typing import Dict, List
import argparse

# Configuration
DATA_DIR = Path(__file__).parent.parent
METADATA_FILE = DATA_DIR / "bird_crops" / "metadata.json"
DEFAULT_OUTPUT_DIR = DATA_DIR / "yolo_labels"


class YOLOExporter:
    """
    Exports YOLO format labels from crop metadata.

    YOLO format (one line per object):
    <class_id> <x_center> <y_center> <width> <height>

    All coordinates are normalized (0-1 range).
    For bird detection, class_id is always 0.
    """

    def __init__(self, metadata_file: Path, min_confidence: float = 0.0):
        """
        Initialize the YOLO exporter.

        Args:
            metadata_file: Path to metadata.json from detection pipeline
            min_confidence: Minimum detection confidence to include (default: 0.0 = include all)
        """
        self.metadata_file = metadata_file
        self.min_confidence = min_confidence
        self.crops_metadata = []
        self.grouped_by_image = defaultdict(list)

    def load_metadata(self):
        """Load crop metadata from JSON file."""
        print(f"\n📂 Loading metadata from: {self.metadata_file.name}")

        with open(self.metadata_file, 'r') as f:
            data = json.load(f)
            self.crops_metadata = data.get('crops', [])

        print(f"✓ Loaded {len(self.crops_metadata):,} crop records")

        # Filter by confidence if needed
        if self.min_confidence > 0:
            before_count = len(self.crops_metadata)
            self.crops_metadata = [
                crop for crop in self.crops_metadata
                if crop.get('confidence', 0) >= self.min_confidence
            ]
            after_count = len(self.crops_metadata)
            filtered_count = before_count - after_count
            print(f"✓ Filtered out {filtered_count:,} low-confidence detections (< {self.min_confidence})")
            print(f"✓ Remaining: {after_count:,} crops")

    def group_by_parent_image(self):
        """Group crops by their source parent image."""
        print(f"\n📊 Grouping crops by parent image...")

        for crop in self.crops_metadata:
            source_photo_id = crop['source_photo_id']
            self.grouped_by_image[source_photo_id].append(crop)

        num_images = len(self.grouped_by_image)
        avg_birds_per_image = len(self.crops_metadata) / num_images if num_images > 0 else 0

        print(f"✓ Found {num_images:,} unique parent images")
        print(f"✓ Average birds per image: {avg_birds_per_image:.1f}")

        # Show distribution stats
        bird_counts = [len(crops) for crops in self.grouped_by_image.values()]
        print(f"✓ Bird count range: {min(bird_counts)} - {max(bird_counts)} birds per image")

    def export_labels(self, output_dir: Path):
        """
        Export YOLO label files.

        Args:
            output_dir: Directory to save label files
        """
        print(f"\n📝 Exporting YOLO labels to: {output_dir}/")

        # Create output directory
        output_dir.mkdir(parents=True, exist_ok=True)

        # Export one label file per parent image
        exported_count = 0
        total_birds = 0

        for photo_id, crops in self.grouped_by_image.items():
            label_file = output_dir / f"{photo_id}.txt"

            with open(label_file, 'w') as f:
                for crop in crops:
                    # Get YOLO format bbox (already normalized)
                    bbox_yolo = crop['bbox_yolo']
                    x_center, y_center, width, height = bbox_yolo

                    # Class ID is always 0 for "bird"
                    class_id = 0

                    # Write YOLO format line
                    f.write(f"{class_id} {x_center:.6f} {y_center:.6f} {width:.6f} {height:.6f}\n")
                    total_birds += 1

            exported_count += 1

        print(f"✓ Exported {exported_count:,} label files")
        print(f"✓ Total bird annotations: {total_birds:,}")

    def export_classes_file(self, output_dir: Path):
        """
        Export classes.txt file.

        For bird detection (not classification), we only have one class: "bird"

        Args:
            output_dir: Directory to save classes.txt
        """
        classes_file = output_dir / "classes.txt"

        with open(classes_file, 'w') as f:
            f.write("bird\n")

        print(f"✓ Created classes.txt (1 class: bird)")

    def export_dataset_yaml(self, output_dir: Path):
        """
        Export dataset.yaml configuration file for YOLO training.

        Args:
            output_dir: Directory to save dataset.yaml
        """
        yaml_file = output_dir / "dataset.yaml"

        # Count images and annotations
        num_images = len(self.grouped_by_image)
        num_annotations = len(self.crops_metadata)

        yaml_content = f"""# YOLO Bird Detection Dataset
# Generated from weak supervision pipeline
# All birds labeled as class 0 (single detection class)

# Paths (relative to this file)
path: ../downloaded_images  # Parent directory containing images
train: train.txt            # List of training image paths (you'll need to create this)
val: val.txt                # List of validation image paths (you'll need to create this)

# Classes
nc: 1  # Number of classes
names:
  0: bird

# Dataset Statistics
# Total images: {num_images:,}
# Total annotations: {num_annotations:,}
# Average birds per image: {num_annotations / num_images:.1f}
# Minimum confidence threshold: {self.min_confidence}

# Note: You need to create train.txt and val.txt files containing
# the paths to your training and validation images (one per line).
# Example:
#   images/TX_2015_12345.jpg
#   images/TX_2016_67890.jpg
"""

        with open(yaml_file, 'w') as f:
            f.write(yaml_content)

        print(f"✓ Created dataset.yaml")

    def export_image_list(self, output_dir: Path):
        """
        Export a list of all parent image IDs.

        This helps you split the dataset into train/val later.

        Args:
            output_dir: Directory to save image list
        """
        image_list_file = output_dir / "image_list.txt"

        with open(image_list_file, 'w') as f:
            for photo_id in sorted(self.grouped_by_image.keys()):
                num_birds = len(self.grouped_by_image[photo_id])
                f.write(f"{photo_id}  # {num_birds} birds\n")

        print(f"✓ Created image_list.txt ({len(self.grouped_by_image):,} images)")

    def export_statistics(self, output_dir: Path):
        """
        Export detailed statistics about the dataset.

        Args:
            output_dir: Directory to save statistics
        """
        stats_file = output_dir / "dataset_stats.json"

        # Calculate statistics
        bird_counts = [len(crops) for crops in self.grouped_by_image.values()]
        confidences = [crop['confidence'] for crop in self.crops_metadata]

        stats = {
            'total_images': len(self.grouped_by_image),
            'total_annotations': len(self.crops_metadata),
            'avg_birds_per_image': sum(bird_counts) / len(bird_counts) if bird_counts else 0,
            'min_birds_per_image': min(bird_counts) if bird_counts else 0,
            'max_birds_per_image': max(bird_counts) if bird_counts else 0,
            'min_confidence': min(confidences) if confidences else 0,
            'max_confidence': max(confidences) if confidences else 0,
            'avg_confidence': sum(confidences) / len(confidences) if confidences else 0,
            'confidence_threshold': self.min_confidence,
        }

        with open(stats_file, 'w') as f:
            json.dump(stats, f, indent=2)

        print(f"✓ Created dataset_stats.json")

    def run(self, output_dir: Path):
        """
        Run the complete export process.

        Args:
            output_dir: Directory to save exported files
        """
        print("=" * 70)
        print("🦅 YOLO LABEL EXPORTER - Bird Detection")
        print("=" * 70)
        print(f"Input: {self.metadata_file}")
        print(f"Output: {output_dir}/")
        print(f"Min confidence: {self.min_confidence}")
        print("=" * 70)

        # Load and process
        self.load_metadata()
        self.group_by_parent_image()

        # Export files
        self.export_labels(output_dir)
        self.export_classes_file(output_dir)
        self.export_dataset_yaml(output_dir)
        self.export_image_list(output_dir)
        self.export_statistics(output_dir)

        print("\n" + "=" * 70)
        print("✅ EXPORT COMPLETE!")
        print("=" * 70)
        print(f"📁 Labels directory: {output_dir}/")
        print(f"📄 Label files: {len(self.grouped_by_image):,} .txt files")
        print(f"🏷️  Classes file: classes.txt (1 class: bird)")
        print(f"⚙️  Config file: dataset.yaml")
        print(f"📋 Image list: image_list.txt")
        print(f"📊 Statistics: dataset_stats.json")
        print("=" * 70)
        print()
        print("🎯 Next steps:")
        print("   1. Split image_list.txt into train/val sets")
        print("   2. Create train.txt and val.txt with image paths")
        print("   3. Update dataset.yaml paths if needed")
        print("   4. Train YOLO model with: yolo train data=dataset.yaml")
        print()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Export YOLO labels for bird detection training",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Export all detections
  python export_yolo_labels.py

  # Only export high-confidence detections (>= 0.5)
  python export_yolo_labels.py --min-confidence 0.5

  # Custom output directory
  python export_yolo_labels.py --output my_labels/

Notes:
  - All birds are labeled as class 0 (single "bird" class)
  - YOLO format: <class_id> <x_center> <y_center> <width> <height>
  - Coordinates are normalized to [0, 1] range
  - One label file per parent image
        """
    )

    parser.add_argument('--min-confidence', type=float, default=0.0,
                       help='Minimum detection confidence to include (default: 0.0)')
    parser.add_argument('--output', type=str, default=None,
                       help=f'Output directory (default: {DEFAULT_OUTPUT_DIR})')
    parser.add_argument('--metadata', type=str, default=None,
                       help=f'Path to metadata.json (default: {METADATA_FILE})')

    args = parser.parse_args()

    # Resolve paths
    metadata_file = Path(args.metadata) if args.metadata else METADATA_FILE
    output_dir = Path(args.output) if args.output else DEFAULT_OUTPUT_DIR

    # Check if metadata exists
    if not metadata_file.exists():
        print(f"❌ Error: Metadata file not found: {metadata_file}")
        print(f"\nRun the detection pipeline first:")
        print(f"  python run_detection_pipeline.py")
        return

    # Create and run exporter
    exporter = YOLOExporter(
        metadata_file=metadata_file,
        min_confidence=args.min_confidence
    )

    exporter.run(output_dir)


if __name__ == "__main__":
    main()
