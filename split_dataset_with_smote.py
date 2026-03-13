#!/usr/bin/env python3
"""
Train/Val Split with Balanced Oversampling and Zero Data Leakage

This script creates a balanced training/validation split for the bird classification dataset.
It prevents data leakage by ensuring crops from the same source image stay together.

Key Features:
1. Groups images by source ID (e.g., 2921_0.jpg, 2921_1.jpg stay together)
2. Stratified split at source level (not individual image level)
3. SMOTE-style oversampling with data augmentation for minority classes
4. Never touches validation set (keeps it pure for unbiased evaluation)

Author: Claude Sonnet 4.5
"""

import os
import shutil
from pathlib import Path
from collections import defaultdict, Counter
import numpy as np
from PIL import Image
import json
from sklearn.model_selection import train_test_split
from tqdm import tqdm
import albumentations as A


class DatasetSplitter:
    """Handles train/val splitting with source-based grouping to prevent leakage."""

    def __init__(self, dataset_path, output_path, val_split=0.2, random_state=42):
        """
        Args:
            dataset_path: Path to original dataset (class folders)
            output_path: Where to save train/ and val/ splits
            val_split: Fraction of sources to use for validation (default: 0.2 = 20%)
            random_state: Random seed for reproducibility
        """
        self.dataset_path = Path(dataset_path)
        self.output_path = Path(output_path)
        self.val_split = val_split
        self.random_state = random_state

        # Augmentation pipeline for oversampling
        # These transforms create realistic variations without destroying bird features
        self.augmentation = A.Compose([
            A.HorizontalFlip(p=0.5),
            A.RandomBrightnessContrast(brightness_limit=0.2, contrast_limit=0.2, p=0.5),
            A.HueSaturationValue(hue_shift_limit=10, sat_shift_limit=20, val_shift_limit=10, p=0.3),
            A.GaussianBlur(blur_limit=(3, 5), p=0.2),
            A.GaussNoise(var_limit=(10.0, 50.0), p=0.2),
            A.Rotate(limit=15, p=0.4),
        ])

    def parse_image_name(self, filename):
        """
        Extract source ID from image filename.

        Examples:
            '2921_0.jpg' -> source_id = '2921'
            '131_5.jpg' -> source_id = '131'

        This groups crops from the same source image together.
        """
        stem = Path(filename).stem  # Remove .jpg
        parts = stem.split('_')
        if len(parts) >= 2:
            return parts[0]  # Source ID
        return stem  # Fallback if no underscore

    def group_images_by_source(self):
        """
        Group all images by their source ID within each class.

        Returns:
            dict: {class_name: {source_id: [image_paths]}}

        Example:
            {
                'australian_pelican': {
                    '2921': ['2921_0.jpg', '2921_1.jpg', '2921_2.jpg'],
                    '2922': ['2922_0.jpg', '2922_1.jpg'],
                    ...
                }
            }
        """
        print("\n📂 Grouping images by source ID to prevent data leakage...")
        class_sources = {}

        for class_dir in sorted(self.dataset_path.iterdir()):
            if not class_dir.is_dir() or class_dir.name == '.git':
                continue

            class_name = class_dir.name
            sources = defaultdict(list)

            # Group all images by source ID
            for img_path in class_dir.glob('*.jpg'):
                source_id = self.parse_image_name(img_path.name)
                sources[source_id].append(img_path)

            class_sources[class_name] = dict(sources)

            # Show stats
            num_sources = len(sources)
            num_images = sum(len(imgs) for imgs in sources.values())
            print(f"  {class_name}: {num_images} images from {num_sources} sources")

        return class_sources

    def split_sources_stratified(self, class_sources):
        """
        Split source IDs into train/val sets with stratification.

        This ensures:
        1. All crops from a source stay together (no leakage)
        2. Class distribution is roughly maintained in both splits

        Args:
            class_sources: Output from group_images_by_source()

        Returns:
            tuple: (train_sources, val_sources)
        """
        print(f"\n✂️  Splitting sources into train ({100*(1-self.val_split):.0f}%) / val ({100*self.val_split:.0f}%)...")

        train_sources = defaultdict(dict)
        val_sources = defaultdict(dict)

        for class_name, sources in class_sources.items():
            source_ids = list(sources.keys())

            # If class has too few sources, put at least one in val
            if len(source_ids) < 5:
                # For very small classes, do simple split
                n_val = max(1, int(len(source_ids) * self.val_split))
                np.random.seed(self.random_state)
                val_ids = list(np.random.choice(source_ids, size=n_val, replace=False))
                train_ids = [sid for sid in source_ids if sid not in val_ids]
            else:
                # Stratified split
                train_ids, val_ids = train_test_split(
                    source_ids,
                    test_size=self.val_split,
                    random_state=self.random_state,
                    shuffle=True
                )

            # Assign sources to splits
            for sid in train_ids:
                train_sources[class_name][sid] = sources[sid]
            for sid in val_ids:
                val_sources[class_name][sid] = sources[sid]

            # Stats
            train_imgs = sum(len(imgs) for imgs in train_sources[class_name].values())
            val_imgs = sum(len(imgs) for imgs in val_sources[class_name].values())
            print(f"  {class_name}: {train_imgs} train, {val_imgs} val")

        return train_sources, val_sources

    def copy_images(self, sources_dict, split_name):
        """
        Copy images to output directory structure.

        Args:
            sources_dict: {class_name: {source_id: [image_paths]}}
            split_name: 'train' or 'val'
        """
        split_dir = self.output_path / split_name
        split_dir.mkdir(parents=True, exist_ok=True)

        print(f"\n📋 Copying {split_name} images...")

        for class_name, sources in tqdm(sources_dict.items(), desc="Classes"):
            class_dir = split_dir / class_name
            class_dir.mkdir(exist_ok=True)

            for source_id, img_paths in sources.items():
                for img_path in img_paths:
                    dest = class_dir / img_path.name
                    shutil.copy2(img_path, dest)

    def calculate_target_distribution(self, train_sources):
        """
        Calculate how many samples each class should have after balancing.

        Strategy:
        - Find median class size
        - Classes below median: oversample to median
        - Classes above median: keep as is

        This balances small classes without creating too many synthetic samples.
        """
        print("\n📊 Calculating target distribution for balancing...")

        class_counts = {}
        for class_name, sources in train_sources.items():
            count = sum(len(imgs) for imgs in sources.values())
            class_counts[class_name] = count

        counts = sorted(class_counts.values())
        median_count = int(np.median(counts))

        # Set target: bring small classes up to median
        target_counts = {}
        for class_name, count in class_counts.items():
            if count < median_count:
                target_counts[class_name] = median_count
            else:
                target_counts[class_name] = count  # Keep as is

        # Show what will happen
        print(f"\n  Median class size: {median_count}")
        print(f"  Classes to oversample: {sum(1 for c in class_counts.values() if c < median_count)}")
        print(f"  Classes to keep as is: {sum(1 for c in class_counts.values() if c >= median_count)}")

        return target_counts

    def oversample_with_augmentation(self, train_sources, target_counts):
        """
        Apply SMOTE-style oversampling using data augmentation.

        For each minority class:
        1. Calculate how many synthetic samples needed
        2. Randomly select real images to augment
        3. Apply random transforms to create variations
        4. Save synthetic images to training set

        This is more appropriate for images than traditional SMOTE (which interpolates pixels).
        """
        print("\n🔄 Oversampling minority classes with data augmentation...")

        train_dir = self.output_path / 'train'
        synthetic_counts = {}

        for class_name, sources in tqdm(train_sources.items(), desc="Classes"):
            current_count = sum(len(imgs) for imgs in sources.values())
            target_count = target_counts[class_name]

            if current_count >= target_count:
                synthetic_counts[class_name] = 0
                continue

            # How many synthetic images needed?
            n_synthetic = target_count - current_count
            synthetic_counts[class_name] = n_synthetic

            # Get all existing images for this class
            class_dir = train_dir / class_name
            existing_images = list(class_dir.glob('*.jpg'))

            if len(existing_images) == 0:
                print(f"  ⚠️  {class_name}: No images found, skipping")
                continue

            # Create synthetic images
            for i in range(n_synthetic):
                # Randomly pick a source image
                source_img_path = np.random.choice(existing_images)

                # Load image
                img = Image.open(source_img_path)
                img_array = np.array(img)

                # Apply augmentation
                augmented = self.augmentation(image=img_array)
                aug_img_array = augmented['image']

                # Save synthetic image
                synthetic_name = f"synthetic_{i:05d}.jpg"
                synthetic_path = class_dir / synthetic_name
                Image.fromarray(aug_img_array).save(synthetic_path, quality=95)

        # Show summary
        print("\n  Synthetic samples created per class:")
        for class_name in sorted(synthetic_counts.keys()):
            count = synthetic_counts[class_name]
            if count > 0:
                print(f"    {class_name}: +{count} synthetic images")

        return synthetic_counts

    def generate_report(self, train_sources, val_sources, synthetic_counts):
        """Generate a detailed report of the split."""
        print("\n" + "="*70)
        print("📈 FINAL DATASET STATISTICS")
        print("="*70)

        report = {
            'split_config': {
                'val_split': self.val_split,
                'random_state': self.random_state,
            },
            'classes': {}
        }

        total_train = 0
        total_val = 0
        total_train_sources = 0
        total_val_sources = 0

        print(f"\n{'Class':<35} {'Train':>12} {'Val':>8} {'Sources (T/V)':>15}")
        print("-" * 70)

        all_classes = sorted(set(train_sources.keys()) | set(val_sources.keys()))

        for class_name in all_classes:
            train_imgs = sum(len(imgs) for imgs in train_sources.get(class_name, {}).values())
            val_imgs = sum(len(imgs) for imgs in val_sources.get(class_name, {}).values())
            train_srcs = len(train_sources.get(class_name, {}))
            val_srcs = len(val_sources.get(class_name, {}))
            synthetic = synthetic_counts.get(class_name, 0)

            total_train += train_imgs
            total_val += val_imgs
            total_train_sources += train_srcs
            total_val_sources += val_srcs

            train_display = f"{train_imgs}"
            if synthetic > 0:
                train_display += f" (+{synthetic})"

            print(f"{class_name:<35} {train_display:>12} {val_imgs:>8} {train_srcs:>7}/{val_srcs:<7}")

            report['classes'][class_name] = {
                'train_images': train_imgs,
                'val_images': val_imgs,
                'train_sources': train_srcs,
                'val_sources': val_srcs,
                'synthetic_images': synthetic
            }

        print("-" * 70)
        print(f"{'TOTAL':<35} {total_train:>12} {total_val:>8} {total_train_sources:>7}/{total_val_sources:<7}")

        report['summary'] = {
            'total_train_images': total_train,
            'total_val_images': total_val,
            'total_train_sources': total_train_sources,
            'total_val_sources': total_val_sources,
            'total_classes': len(all_classes),
            'total_synthetic': sum(synthetic_counts.values())
        }

        print(f"\n✅ Total synthetic images created: {sum(synthetic_counts.values())}")
        print(f"✅ No data leakage: All crops from {total_train_sources + total_val_sources} sources kept together")
        print(f"✅ Train/val ratio: {total_train / (total_train + total_val) * 100:.1f}% / {total_val / (total_train + total_val) * 100:.1f}%")

        # Save report
        report_path = self.output_path / 'split_report.json'
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"\n📄 Report saved to: {report_path}")

        return report

    def run(self, apply_oversampling=True):
        """Execute the complete pipeline."""
        print("="*70)
        print("🚀 Starting Dataset Split with Balanced Oversampling")
        print("="*70)

        # Step 1: Group images by source
        class_sources = self.group_images_by_source()

        # Step 2: Split sources (not images) into train/val
        train_sources, val_sources = self.split_sources_stratified(class_sources)

        # Step 3: Copy images to output directories
        self.copy_images(train_sources, 'train')
        self.copy_images(val_sources, 'val')

        synthetic_counts = {}

        # Step 4: Apply oversampling to training set only
        if apply_oversampling:
            target_counts = self.calculate_target_distribution(train_sources)
            synthetic_counts = self.oversample_with_augmentation(train_sources, target_counts)

        # Step 5: Generate report
        self.generate_report(train_sources, val_sources, synthetic_counts)

        print("\n✨ Done! Your dataset is ready for training.")
        print(f"   Train: {self.output_path / 'train'}")
        print(f"   Val:   {self.output_path / 'val'}")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description='Split bird classification dataset with SMOTE-style oversampling',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage (20% validation)
  python split_dataset_with_smote.py

  # Custom validation split (30%)
  python split_dataset_with_smote.py --val-split 0.3

  # No oversampling (just split)
  python split_dataset_with_smote.py --no-oversample

  # Custom paths
  python split_dataset_with_smote.py --input ./data --output ./split_data
        """
    )

    parser.add_argument(
        '--input',
        type=str,
        default='bird_classification_dataset',
        help='Path to original dataset (default: bird_classification_dataset)'
    )
    parser.add_argument(
        '--output',
        type=str,
        default='bird_classification_dataset_split',
        help='Path to save train/val splits (default: bird_classification_dataset_split)'
    )
    parser.add_argument(
        '--val-split',
        type=float,
        default=0.2,
        help='Fraction of sources for validation (default: 0.2 = 20%%)'
    )
    parser.add_argument(
        '--random-state',
        type=int,
        default=42,
        help='Random seed for reproducibility (default: 42)'
    )
    parser.add_argument(
        '--no-oversample',
        action='store_true',
        help='Skip oversampling (just split the dataset)'
    )

    args = parser.parse_args()

    # Validate inputs
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"❌ Error: Input directory not found: {input_path}")
        return 1

    if not (0 < args.val_split < 1):
        print(f"❌ Error: --val-split must be between 0 and 1 (got {args.val_split})")
        return 1

    # Run the split
    splitter = DatasetSplitter(
        dataset_path=input_path,
        output_path=Path(args.output),
        val_split=args.val_split,
        random_state=args.random_state
    )

    splitter.run(apply_oversampling=not args.no_oversample)

    return 0


if __name__ == '__main__':
    exit(main())
