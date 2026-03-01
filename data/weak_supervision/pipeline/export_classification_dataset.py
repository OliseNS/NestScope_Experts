"""
Export YOLO Classification Dataset

Creates a folder structure for YOLO classification training:
  NestVision/classify/
  ├── train/
  │   ├── BRPE/
  │   │   ├── bird_000123.jpg
  │   │   └── ...
  │   ├── LAGU/
  │   └── ...
  ├── val/
  │   ├── BRPE/
  │   └── ...
  └── dataset.yaml

Uses symlinks to crop images (saves ~500MB disk space).
Splits 80% train / 20% val, stratified by species.
"""

import sys
from pathlib import Path
import json
import os
import random
from collections import defaultdict
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))


def export_classification_dataset(
    assignments_path: str,
    crops_dir: str,
    output_dir: str,
    train_ratio: float = 0.8,
    min_samples_per_species: int = 0,
    seed: int = 42,
    ground_truth_only: bool = False
):
    """
    Export crop images organized by species for YOLO classification training.

    Args:
        assignments_path: Path to final_assignments.json
        crops_dir: Path to bird_crops directory (contains images/)
        output_dir: Path to output directory (e.g., NestVision/classify)
        train_ratio: Fraction of data for training (rest goes to val)
        min_samples_per_species: Skip species with fewer samples than this
        seed: Random seed for reproducible splits
        ground_truth_only: If True, only include crops from single-species images
                           (method == "ground_truth", confidence == 1.0)
    """
    random.seed(seed)

    crops_dir = Path(crops_dir)
    output_dir = Path(output_dir)
    images_dir = crops_dir / "images"

    mode_label = "GROUND TRUTH ONLY" if ground_truth_only else "ALL ASSIGNMENTS"
    print(f"Mode: {mode_label}")

    # Load assignments
    print("Loading assignments...")
    with open(assignments_path, 'r') as f:
        data = json.load(f)
    assignments = data['assignments']
    print(f"  {len(assignments)} total labeled crops")

    # Filter to ground truth only if requested
    if ground_truth_only:
        assignments = {
            crop_id: a for crop_id, a in assignments.items()
            if a['method'] == 'ground_truth'
        }
        print(f"  {len(assignments)} ground truth crops (filtered)")

    # Load crop metadata for filenames
    print("Loading crop metadata...")
    with open(crops_dir / "metadata.json", 'r') as f:
        metadata = json.load(f)
    crop_lookup = {str(c['crop_id']): c for c in metadata['crops']}

    # Group by species
    species_crops = defaultdict(list)
    for crop_id_str, assignment in assignments.items():
        species_crops[assignment['species']].append({
            'crop_id': crop_id_str,
            'species': assignment['species'],
            'confidence': assignment['confidence'],
            'method': assignment['method'],
            'filename': crop_lookup[crop_id_str]['crop_filename']
        })

    # Filter species by minimum sample count
    skipped_species = []
    for sp in list(species_crops.keys()):
        if len(species_crops[sp]) < min_samples_per_species:
            skipped_species.append((sp, len(species_crops[sp])))
            del species_crops[sp]

    if skipped_species:
        print(f"\n  Skipped {len(skipped_species)} species below minimum ({min_samples_per_species}):")
        for sp, count in skipped_species:
            print(f"    {sp}: {count} crops")

    # Create output directories
    train_dir = output_dir / "train"
    val_dir = output_dir / "val"

    # Clean previous export if exists
    if output_dir.exists():
        import shutil
        shutil.rmtree(output_dir)

    print(f"\nCreating dataset at: {output_dir}")
    print(f"  Train/Val split: {train_ratio:.0%} / {1-train_ratio:.0%}")

    total_train = 0
    total_val = 0
    species_stats = []

    for species_code in sorted(species_crops.keys()):
        crops = species_crops[species_code]

        # Shuffle and split
        random.shuffle(crops)
        split_idx = int(len(crops) * train_ratio)
        train_crops = crops[:split_idx]
        val_crops = crops[split_idx:]

        # Create species directories
        species_train_dir = train_dir / species_code
        species_val_dir = val_dir / species_code
        species_train_dir.mkdir(parents=True, exist_ok=True)
        species_val_dir.mkdir(parents=True, exist_ok=True)

        # Symlink images
        for crop in train_crops:
            src = (images_dir / crop['filename']).resolve()
            dst = species_train_dir / crop['filename']
            os.symlink(src, dst)

        for crop in val_crops:
            src = (images_dir / crop['filename']).resolve()
            dst = species_val_dir / crop['filename']
            os.symlink(src, dst)

        total_train += len(train_crops)
        total_val += len(val_crops)

        # Count methods in this species
        gt_count = sum(1 for c in crops if c['method'] == 'ground_truth')
        hun_count = sum(1 for c in crops if c['method'] == 'hungarian')
        poe_count = sum(1 for c in crops if c['method'] == 'poe')
        mean_conf = sum(c['confidence'] for c in crops) / len(crops)

        species_stats.append({
            'species': species_code,
            'total': len(crops),
            'train': len(train_crops),
            'val': len(val_crops),
            'ground_truth': gt_count,
            'hungarian': hun_count,
            'poe': poe_count,
            'mean_confidence': round(mean_conf, 3)
        })

    # Create dataset.yaml for YOLO
    class_names = sorted(species_crops.keys())
    dataset_type = "Ground Truth Only" if ground_truth_only else "All Assignments"
    yaml_content = f"""# NestScope Bird Species Classification Dataset
# Type: {dataset_type}
# Generated: {datetime.now().isoformat()}
# Total: {total_train + total_val} images ({total_train} train, {total_val} val)
# Species: {len(class_names)}

path: {output_dir.resolve()}
train: train
val: val

# Number of classes
nc: {len(class_names)}

# Class names
names:
"""
    for i, name in enumerate(class_names):
        count = len(species_crops[name])
        yaml_content += f"  {i}: {name}  # {count} images\n"

    yaml_path = output_dir / "dataset.yaml"
    with open(yaml_path, 'w') as f:
        f.write(yaml_content)

    # Save detailed stats
    stats = {
        'total_images': total_train + total_val,
        'train_images': total_train,
        'val_images': total_val,
        'n_species': len(class_names),
        'species': class_names,
        'train_ratio': train_ratio,
        'seed': seed,
        'per_species': species_stats,
        'generated_at': datetime.now().isoformat()
    }

    stats_path = output_dir / "dataset_stats.json"
    with open(stats_path, 'w') as f:
        json.dump(stats, f, indent=2)

    # Print summary
    print(f"\n{'='*60}")
    print(f"CLASSIFICATION DATASET READY")
    print(f"{'='*60}")
    print(f"  Path: {output_dir}")
    print(f"  Species: {len(class_names)}")
    print(f"  Train: {total_train}")
    print(f"  Val: {total_val}")
    print(f"  Total: {total_train + total_val}")
    print(f"\nPer species:")
    print(f"  {'Species':<8} {'Total':>7} {'Train':>7} {'Val':>5} {'GT':>6} {'Hung':>7} {'PoE':>5} {'Conf':>6}")
    print(f"  {'-'*55}")
    for s in sorted(species_stats, key=lambda x: -x['total']):
        print(f"  {s['species']:<8} {s['total']:>7} {s['train']:>7} {s['val']:>5} "
              f"{s['ground_truth']:>6} {s['hungarian']:>7} {s['poe']:>5} {s['mean_confidence']:>6.3f}")

    print(f"\nFiles:")
    print(f"  {yaml_path}")
    print(f"  {stats_path}")
    print(f"\nTo train with YOLO:")
    print(f"  yolo classify train data={yaml_path} model=yolov8n-cls.pt epochs=50 imgsz=224")


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Export YOLO classification dataset')
    parser.add_argument('--assignments', type=str,
                        default='data/weak_supervision/bird_crops/assignments/final_assignments.json',
                        help='Path to final assignments')
    parser.add_argument('--crops-dir', type=str,
                        default='data/weak_supervision/bird_crops',
                        help='Path to bird_crops directory')
    parser.add_argument('--output', type=str,
                        default='NestVision/classify',
                        help='Output directory for dataset')
    parser.add_argument('--train-ratio', type=float, default=0.8,
                        help='Train split ratio (default 0.8)')
    parser.add_argument('--min-samples', type=int, default=0,
                        help='Minimum samples per species (skip species with fewer)')
    parser.add_argument('--seed', type=int, default=42,
                        help='Random seed')
    parser.add_argument('--ground-truth-only', action='store_true',
                        help='Only include ground truth crops (from single-species images, confidence=1.0)')

    args = parser.parse_args()

    export_classification_dataset(
        assignments_path=args.assignments,
        crops_dir=args.crops_dir,
        output_dir=Path(args.output),
        train_ratio=args.train_ratio,
        min_samples_per_species=args.min_samples,
        seed=args.seed,
        ground_truth_only=args.ground_truth_only
    )


if __name__ == '__main__':
    main()
