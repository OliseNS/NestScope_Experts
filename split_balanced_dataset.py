#!/usr/bin/env python3
"""
Train/Val Split with Balanced Over/Under-sampling and Zero Data Leakage

This script creates a balanced training/validation split for the bird classification dataset.
It prevents data leakage by ensuring crops from the same source image stay together.

Key Features:
1. Groups images by source ID (e.g., 2921_0.jpg, 2921_1.jpg stay together)
2. Stratified split at source level (not individual image level)
3. OVERsampling minority classes (augmentation) + UNDERsampling majority classes (random selection)
4. Skips classes with insufficient data (< 5 sources or < 10 images)
5. Never touches validation set (keeps it pure for unbiased evaluation)

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


class BalancedDatasetSplitter:
    """Handles train/val splitting with balanced over/under-sampling."""

    def __init__(
        self,
        dataset_path,
        output_path,
        val_split=0.2,
        random_state=42,
        target_samples=500,
        min_images=50
    ):
        """
        Args:
            dataset_path: Path to original dataset (class folders)
            output_path: Where to save train/ and val/ splits
            val_split: Fraction of sources for validation (default: 0.2 = 20%)
            random_state: Random seed for reproducibility
            target_samples: Target number of samples per class (default: 500)
            min_images: Minimum total images required to include a class (default: 50)
        """
        self.dataset_path = Path(dataset_path)
        self.output_path = Path(output_path)
        self.val_split = val_split
        self.random_state = random_state
        self.target_samples = target_samples
        self.min_images = min_images

        np.random.seed(random_state)

        # Augmentation pipeline for oversampling
        # Optimized for YOLO classification training
        self.augmentation = A.Compose([
            A.HorizontalFlip(p=0.5),
            A.RandomBrightnessContrast(brightness_limit=0.2, contrast_limit=0.2, p=0.6),
            A.HueSaturationValue(hue_shift_limit=10, sat_shift_limit=20, val_shift_limit=10, p=0.4),
            A.GaussianBlur(blur_limit=(3, 5), p=0.2),
            A.GaussNoise(mean=0, var_limit=(10.0, 50.0), p=0.2),
            A.Rotate(limit=15, p=0.4),
            A.ShiftScaleRotate(shift_limit=0.1, scale_limit=0.1, rotate_limit=15, p=0.3),
        ])

    def parse_image_name(self, filename):
        """Extract source ID from image filename."""
        stem = Path(filename).stem
        parts = stem.split('_')
        if len(parts) >= 2:
            return parts[0]
        return stem

    def group_images_by_source(self):
        """Group all images by their source ID within each class."""
        print("\n📂 Grouping images by source ID to prevent data leakage...")
        class_sources = {}
        skipped_classes = []

        for class_dir in sorted(self.dataset_path.iterdir()):
            if not class_dir.is_dir() or class_dir.name.startswith('.'):
                continue

            class_name = class_dir.name
            sources = defaultdict(list)

            # Group all images by source ID
            for img_path in class_dir.glob('*.jpg'):
                source_id = self.parse_image_name(img_path.name)
                sources[source_id].append(img_path)

            num_sources = len(sources)
            num_images = sum(len(imgs) for imgs in sources.values())

            # Check if class has enough images (ignore source count)
            if num_images < self.min_images:
                skipped_classes.append({
                    'class': class_name,
                    'sources': num_sources,
                    'images': num_images,
                    'reason': f"only {num_images} images (need {self.min_images}+)"
                })
                print(f"  ⚠️  {class_name}: {num_images} images from {num_sources} sources - SKIPPED (< {self.min_images} images)")
                continue

            class_sources[class_name] = dict(sources)
            print(f"  ✓ {class_name}: {num_images} images from {num_sources} sources")

        if skipped_classes:
            print(f"\n⚠️  Skipped {len(skipped_classes)} classes with insufficient data")

        return class_sources, skipped_classes

    def split_sources_stratified(self, class_sources):
        """Split source IDs into train/val sets with stratification."""
        print(f"\n✂️  Splitting sources into train ({100*(1-self.val_split):.0f}%) / val ({100*self.val_split:.0f}%)...")

        train_sources = defaultdict(dict)
        val_sources = defaultdict(dict)

        for class_name, sources in class_sources.items():
            source_ids = list(sources.keys())

            if len(source_ids) < 5:
                # For very small classes, ensure at least one in val
                n_val = max(1, int(len(source_ids) * self.val_split))
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

    def calculate_target_size(self, train_sources):
        """
        Calculate target number of samples per class.

        Uses the specified target (default: 500) to balance all classes.
        """
        print("\n📊 Calculating target size for balancing...")

        class_counts = {}
        for class_name, sources in train_sources.items():
            count = sum(len(imgs) for imgs in sources.values())
            class_counts[class_name] = count

        target = self.target_samples
        print(f"  Target: {target} samples/class")

        # Show distribution
        counts = sorted(class_counts.values())
        print(f"  Current distribution: min={counts[0]}, median={int(np.median(counts))}, mean={int(np.mean(counts))}, max={counts[-1]}")
        print(f"  Classes to oversample: {sum(1 for c in counts if c < target)}")
        print(f"  Classes to undersample: {sum(1 for c in counts if c > target)}")
        print(f"  Classes at target: {sum(1 for c in counts if c == target)}")

        return target

    def copy_images(self, sources_dict, split_name):
        """Copy images to output directory structure."""
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

    def undersample_class(self, class_dir, target_count):
        """
        Randomly remove images from a class to reach target count.

        Returns:
            Number of images removed
        """
        existing_images = list(class_dir.glob('*.jpg'))
        current_count = len(existing_images)

        if current_count <= target_count:
            return 0

        # How many to remove
        n_remove = current_count - target_count

        # Randomly select images to remove
        images_to_remove = np.random.choice(existing_images, size=n_remove, replace=False)

        # Delete them
        for img_path in images_to_remove:
            img_path.unlink()

        return n_remove

    def oversample_class(self, class_dir, target_count):
        """
        Create synthetic images via augmentation to reach target count.

        Returns:
            Number of synthetic images created
        """
        existing_images = list(class_dir.glob('*.jpg'))
        current_count = len(existing_images)

        if current_count >= target_count:
            return 0

        # If no training images, can't augment
        if current_count == 0:
            return 0

        # How many synthetic images needed
        n_synthetic = target_count - current_count

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
            synthetic_name = f"aug_{i:05d}.jpg"
            synthetic_path = class_dir / synthetic_name
            Image.fromarray(aug_img_array).save(synthetic_path, quality=95)

        return n_synthetic

    def balance_dataset(self, train_sources, target_size):
        """
        Balance the training dataset using over/under-sampling.

        For each class:
        - If below target: oversample with augmentation
        - If above target: undersample by random removal
        - If at target: keep as is
        """
        print("\n⚖️  Balancing training dataset...")

        train_dir = self.output_path / 'train'
        balance_stats = {}

        for class_name in tqdm(sorted(train_sources.keys()), desc="Balancing"):
            class_dir = train_dir / class_name
            existing_images = list(class_dir.glob('*.jpg'))
            current_count = len(existing_images)

            # Skip classes with no training images
            if current_count == 0:
                balance_stats[class_name] = {
                    'original': 0,
                    'final': 0,
                    'action': 'skipped',
                    'changed': 0
                }
                continue

            if current_count < target_size:
                # OVERSAMPLE
                n_added = self.oversample_class(class_dir, target_size)
                balance_stats[class_name] = {
                    'original': current_count,
                    'final': current_count + n_added,
                    'action': 'oversample',
                    'changed': n_added
                }
            elif current_count > target_size:
                # UNDERSAMPLE
                n_removed = self.undersample_class(class_dir, target_size)
                balance_stats[class_name] = {
                    'original': current_count,
                    'final': target_size,
                    'action': 'undersample',
                    'changed': n_removed
                }
            else:
                # KEEP AS IS
                balance_stats[class_name] = {
                    'original': current_count,
                    'final': current_count,
                    'action': 'none',
                    'changed': 0
                }

        # Summary
        print("\n  Balancing summary:")
        oversampled = sum(1 for s in balance_stats.values() if s['action'] == 'oversample')
        undersampled = sum(1 for s in balance_stats.values() if s['action'] == 'undersample')
        unchanged = sum(1 for s in balance_stats.values() if s['action'] == 'none')
        skipped = sum(1 for s in balance_stats.values() if s['action'] == 'skipped')
        total_added = sum(s['changed'] for s in balance_stats.values() if s['action'] == 'oversample')
        total_removed = sum(s['changed'] for s in balance_stats.values() if s['action'] == 'undersample')

        print(f"    Oversampled: {oversampled} classes (+{total_added} synthetic images)")
        print(f"    Undersampled: {undersampled} classes (-{total_removed} images)")
        print(f"    Unchanged: {unchanged} classes")
        if skipped > 0:
            print(f"    Skipped (0 train images): {skipped} classes")

        return balance_stats

    def generate_report(self, train_sources, val_sources, balance_stats, skipped_classes):
        """Generate a detailed report of the split and balancing."""
        print("\n" + "="*70)
        print("📈 FINAL DATASET STATISTICS")
        print("="*70)

        report = {
            'split_config': {
                'val_split': self.val_split,
                'random_state': self.random_state,
                'target_samples': list(balance_stats.values())[0]['final'] if balance_stats else None,
                'min_images': self.min_images,
            },
            'skipped_classes': skipped_classes,
            'classes': {}
        }

        # Count actual final images
        train_dir = self.output_path / 'train'
        val_dir = self.output_path / 'val'

        total_train = 0
        total_val = 0

        print(f"\n{'Class':<35} {'Train':>10} {'Val':>8} {'Action':>12}")
        print("-" * 70)

        all_classes = sorted(set(train_sources.keys()) | set(val_sources.keys()))

        for class_name in all_classes:
            train_class_dir = train_dir / class_name
            val_class_dir = val_dir / class_name

            train_imgs = len(list(train_class_dir.glob('*.jpg'))) if train_class_dir.exists() else 0
            val_imgs = len(list(val_class_dir.glob('*.jpg'))) if val_class_dir.exists() else 0

            total_train += train_imgs
            total_val += val_imgs

            balance_info = balance_stats.get(class_name, {})
            action = balance_info.get('action', 'unknown')
            changed = balance_info.get('changed', 0)

            if action == 'oversample':
                action_str = f"+{changed} aug"
            elif action == 'undersample':
                action_str = f"-{changed} imgs"
            elif action == 'skipped':
                action_str = "0 train"
            else:
                action_str = "unchanged"

            print(f"{class_name:<35} {train_imgs:>10} {val_imgs:>8} {action_str:>12}")

            report['classes'][class_name] = {
                'train_images': train_imgs,
                'val_images': val_imgs,
                'balance_action': action,
                'balance_changed': changed
            }

        print("-" * 70)
        print(f"{'TOTAL':<35} {total_train:>10} {total_val:>8}")

        report['summary'] = {
            'total_train_images': total_train,
            'total_val_images': total_val,
            'total_classes': len(all_classes),
            'skipped_classes': len(skipped_classes),
        }

        print(f"\n✅ Dataset balanced to {list(balance_stats.values())[0]['final'] if balance_stats else 0} samples/class")
        print(f"✅ Classes included: {len(all_classes)}")
        print(f"✅ Classes skipped: {len(skipped_classes)}")
        print(f"✅ Train/val ratio: {total_train / (total_train + total_val) * 100:.1f}% / {total_val / (total_train + total_val) * 100:.1f}%")

        # Save report
        report_path = self.output_path / 'split_report.json'
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"\n📄 Report saved to: {report_path}")

        return report

    def run(self, apply_balancing=True):
        """Execute the complete pipeline."""
        print("="*70)
        print("🚀 Starting Balanced Dataset Split (Over + Under-sampling)")
        print("="*70)

        # Step 1: Group images by source
        class_sources, skipped_classes = self.group_images_by_source()

        if not class_sources:
            print("\n❌ Error: No classes with sufficient data found!")
            return

        # Step 2: Split sources into train/val
        train_sources, val_sources = self.split_sources_stratified(class_sources)

        # Step 3: Calculate target size
        target_size = self.calculate_target_size(train_sources)

        # Step 4: Copy images to output directories
        self.copy_images(train_sources, 'train')
        self.copy_images(val_sources, 'val')

        balance_stats = {}

        # Step 5: Balance training set
        if apply_balancing:
            balance_stats = self.balance_dataset(train_sources, target_size)

        # Step 6: Generate report
        self.generate_report(train_sources, val_sources, balance_stats, skipped_classes)

        print("\n✨ Done! Your dataset is ready for training.")
        print(f"   Train: {self.output_path / 'train'}")
        print(f"   Val:   {self.output_path / 'val'}")

        # YOLO training recommendations
        print("\n" + "="*70)
        print("📐 RECOMMENDED YOLO TRAINING SETTINGS")
        print("="*70)
        print("\n🎯 For YOLO Classification (Species Identification):")
        print("   Image size: 224x224 (matches your classifier models)")
        print("   Batch size: 32-64 (depending on GPU memory)")
        print("   Epochs: 100-200")
        print("   Example command:")
        print("   yolo classify train data=bird_classification_dataset_split/train \\")
        print("                         imgsz=224 batch=32 epochs=100")
        print("\n💡 Your classifier models (classifier_swift.onnx, classifier_apex.onnx)")
        print("   expect 224×224 RGB input, so train at this resolution for best results.")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description='Split and balance bird classification dataset',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage (500 images per class, min 50 images)
  python split_balanced_dataset.py

  # Custom target size (e.g., 300 samples per class)
  python split_balanced_dataset.py --target 300

  # Include only classes with 100+ images
  python split_balanced_dataset.py --min-images 100

  # No balancing (just split)
  python split_balanced_dataset.py --no-balance
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
        '--target',
        type=int,
        default=500,
        help='Target samples per class (default: 500)'
    )
    parser.add_argument(
        '--min-images',
        type=int,
        default=50,
        help='Minimum total images required to include a class (default: 50)'
    )
    parser.add_argument(
        '--random-state',
        type=int,
        default=42,
        help='Random seed for reproducibility (default: 42)'
    )
    parser.add_argument(
        '--no-balance',
        action='store_true',
        help='Skip balancing (just split the dataset)'
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
    splitter = BalancedDatasetSplitter(
        dataset_path=input_path,
        output_path=Path(args.output),
        val_split=args.val_split,
        random_state=args.random_state,
        target_samples=args.target,
        min_images=args.min_images
    )

    splitter.run(apply_balancing=not args.no_balance)

    return 0


if __name__ == '__main__':
    exit(main())
