import os
import shutil
import random
import math
import numpy as np
from pathlib import Path
from collections import defaultdict, Counter
from tqdm import tqdm  # optional

# ================= CONFIGURATION =================
DATASET_DIR = "yolo_det"
OUTPUT_DIR = "licksplit"
# Ratios (Must sum to 1.0)
TRAIN_RATIO = 0.8
VAL_RATIO = 0.2
TEST_RATIO = 0

# Background Image Cap (as percentage of annotated images)
# Set to 0.10 for 10%, 0.20 for 20%, etc.
# Set to None or 1.0 to include ALL background images
BG_IMAGE_CAP = 0.10

SEED = 42

# !!! UPDATED: Single class configuration
CLASS_NAMES = ['bird']
# =================================================

def setup_dirs():
    """Creates the output directory structure."""
    splits = ['train', 'val', 'test']
    sub_dirs = ['images', 'labels']

    for split in splits:
        for sub in sub_dirs:
            os.makedirs(os.path.join(OUTPUT_DIR, sub, split), exist_ok=True)

def get_image_label_pairs(dataset_dir):
    """
    Scans the dataset and pairs images with their label files.
    Returns list of dicts.
    """
    images_root = Path(dataset_dir) / "images"
    labels_root = Path(dataset_dir) / "labels"

    exts = {".jpg", ".jpeg", ".png", ".bmp", ".tif"}
    data = []

    all_images = [p for p in images_root.rglob("*") if p.suffix.lower() in exts]
    print(f"Scanning {len(all_images)} images for class instances...")

    for img_path in all_images:
        try:
            rel_path = img_path.relative_to(images_root)
        except ValueError:
            rel_path = Path(img_path.name)

        label_path = labels_root / rel_path.with_suffix(".txt")

        class_counts = Counter()
        if label_path.exists():
            with open(label_path, 'r') as f:
                for line in f:
                    parts = line.strip().split()
                    if parts:
                        try:
                            cls = int(parts[0])
                            class_counts[cls] += 1
                        except ValueError:
                            continue

        data.append({
            'image': img_path,
            'label': label_path,
            'rel_path': rel_path,
            'class_counts': class_counts
        })

    return data

def compute_instance_targets(global_counts, ratios):
    """
    For each class compute integer target counts per split.
    """
    splits = list(ratios.keys())
    targets = {s: {} for s in splits}

    for cls, tot in global_counts.items():
        exact = {s: tot * ratios[s] for s in splits}
        floored = {s: math.floor(exact[s]) for s in splits}
        assigned = sum(floored.values())
        remaining = tot - assigned

        fracs = sorted(splits, key=lambda s: exact[s] - floored[s], reverse=True)
        add = {s: 0 for s in splits}
        for i in range(remaining):
            add[fracs[i % len(fracs)]] += 1

        for s in splits:
            targets[s][cls] = floored[s] + add[s]

    return targets

def apply_bg_cap(empty_images, annotated_count, cap_ratio):
    """
    Caps background images based on annotated image count.

    Args:
        empty_images: List of background image items
        annotated_count: Number of annotated images
        cap_ratio: Maximum ratio of bg images to annotated images (e.g., 0.10 for 10%)

    Returns:
        Tuple of (included_bg_images, excluded_count)
    """
    if cap_ratio is None or cap_ratio >= 1.0:
        print(f"\n📊 Background Images: Including ALL {len(empty_images)} images (no cap applied)")
        return empty_images, 0

    max_bg_images = int(annotated_count * cap_ratio)

    if len(empty_images) <= max_bg_images:
        print(f"\n📊 Background Images: {len(empty_images)} found ({len(empty_images)/annotated_count*100:.1f}% of annotated)")
        print(f"   ✓ Within {cap_ratio*100:.0f}% cap ({max_bg_images} max) - including all")
        return empty_images, 0

    # Randomly sample to meet the cap
    random.seed(SEED)
    included = random.sample(empty_images, max_bg_images)
    excluded_count = len(empty_images) - max_bg_images

    print(f"\n📊 Background Images: {len(empty_images)} found ({len(empty_images)/annotated_count*100:.1f}% of annotated)")
    print(f"   ⚠️  Exceeds {cap_ratio*100:.0f}% cap ({max_bg_images} max)")
    print(f"   → Including {max_bg_images} background images")
    print(f"   → Excluding {excluded_count} background images")

    return included, excluded_count

def distribute_files(data):
    """
    Distributes images into Train/Val/Test attempting to match instance-level targets.
    """
    random.seed(SEED)
    random.shuffle(data)

    global_counts = Counter()
    for item in data:
        global_counts.update(item['class_counts'])

    print(f"Total Instances Found: {dict(global_counts)}")

    ratios = {'train': TRAIN_RATIO, 'val': VAL_RATIO, 'test': TEST_RATIO}
    targets = compute_instance_targets(global_counts, ratios)

    splits = {
        'train': {'items': [], 'counts': Counter(), 'target': targets['train']},
        'val':   {'items': [], 'counts': Counter(), 'target': targets['val']},
        'test':  {'items': [], 'counts': Counter(), 'target': targets['test']}
    }

    active_images = [x for x in data if sum(x['class_counts'].values()) > 0]
    empty_images = [x for x in data if sum(x['class_counts'].values()) == 0]

    print(f"\n📸 Dataset Composition:")
    print(f"   Annotated images: {len(active_images)}")
    print(f"   Background images: {len(empty_images)}")

    # Apply background image cap
    empty_images, excluded_bg = apply_bg_cap(empty_images, len(active_images), BG_IMAGE_CAP)

    # Sort active images by rarity (less critical for 1 class but keeps logic robust)
    def rarity_key(item):
        if not item['class_counts']: return float('inf')
        return min(global_counts[c] for c in item['class_counts'].keys())

    active_images.sort(key=rarity_key)

    for item in active_images:
        cls_counts = item['class_counts']
        best_split = None
        best_gain = -1
        best_overfill_penalty = None

        for split_name, state in splits.items():
            gain = 0
            for cls, cnt in cls_counts.items():
                remaining_needed = state['target'].get(cls, 0) - state['counts'].get(cls, 0)
                if remaining_needed > 0:
                    gain += min(cnt, remaining_needed)

            overfill_penalty = 0.0
            for cls, cnt in cls_counts.items():
                after = state['counts'].get(cls, 0) + cnt
                target = state['target'].get(cls, 0)
                if target > 0:
                    over = max(0, after - target) / target
                    overfill_penalty += over

            if gain > best_gain or (gain == best_gain and (best_overfill_penalty is None or overfill_penalty < best_overfill_penalty)):
                best_split = split_name
                best_gain = gain
                best_overfill_penalty = overfill_penalty

        if best_gain == 0:
            best_split = None
            best_penalty = float('inf')
            for split_name, state in splits.items():
                penalty = 0.0
                for cls, cnt in cls_counts.items():
                    after = state['counts'].get(cls, 0) + cnt
                    target = state['target'].get(cls, 0)
                    if target > 0:
                        penalty += max(0, after - target) / target
                if penalty < best_penalty or (abs(penalty - best_penalty) < 1e-9 and split_name == 'train'):
                    best_penalty = penalty
                    best_split = split_name

        splits[best_split]['items'].append(item)
        splits[best_split]['counts'].update(cls_counts)

    # Distribute empty images (after cap applied)
    random.shuffle(empty_images)
    n_empty = len(empty_images)
    n_train = int(n_empty * TRAIN_RATIO)
    n_val = int(n_empty * VAL_RATIO)

    splits['train']['items'].extend(empty_images[:n_train])
    splits['val']['items'].extend(empty_images[n_train:n_train + n_val])
    splits['test']['items'].extend(empty_images[n_train + n_val:])

    return splits, global_counts, targets, excluded_bg

def copy_files(splits):
    """Copies images and labels while preserving relative paths."""
    print("\nStarting Copy Process...")

    for split_name, split_data in splits.items():
        print(f"Processing {split_name} ({len(split_data['items'])} images)...")

        for item in split_data['items']:
            rel_path = item['rel_path']
            img_dest = Path(OUTPUT_DIR) / "images" / split_name / rel_path
            lbl_dest = Path(OUTPUT_DIR) / "labels" / split_name / rel_path.with_suffix('.txt')

            img_dest.parent.mkdir(parents=True, exist_ok=True)
            lbl_dest.parent.mkdir(parents=True, exist_ok=True)

            shutil.copy2(item['image'], img_dest)
            if item['label'].exists():
                shutil.copy2(item['label'], lbl_dest)
            else:
                lbl_dest.write_text("")

def create_yaml():
    """Generates the data.yaml file required for YOLO training."""
    yaml_path = os.path.join(OUTPUT_DIR, "data.yaml")

    # Get absolute path for robustness
    abs_path = os.path.abspath(OUTPUT_DIR)

    print(f"\nGenerating {yaml_path}...")

    # Define YAML content with dynamic class names
    content = [
        f"path: {abs_path}  # dataset root dir",
        "train: images/train  # train images (relative to 'path')",
        "val: images/val  # val images (relative to 'path')",
        "test: images/test  # test images (optional)",
        "",
        f"nc: {len(CLASS_NAMES)}  # number of classes",
        f"names: {CLASS_NAMES}  # class names"
    ]

    with open(yaml_path, 'w') as f:
        f.write("\n".join(content))

def print_stats(splits, global_counts, targets, excluded_bg):
    """Prints a comparison table of actual vs target instance counts per class."""
    print("\n" + "=" * 72)
    print(f"{'Class':<8} | {'Total':<8} | {'Target T/V/Te':<20} | {'Actual T/V/Te':<20} | {'T err%':<8}")
    print("-" * 72)

    all_classes = sorted(global_counts.keys())

    for cls in all_classes:
        total = global_counts[cls]
        tgt_train = targets['train'].get(cls, 0)
        tgt_val = targets['val'].get(cls, 0)
        tgt_test = targets['test'].get(cls, 0)

        act_train = splits['train']['counts'].get(cls, 0)
        act_val = splits['val']['counts'].get(cls, 0)
        act_test = splits['test']['counts'].get(cls, 0)

        train_err_pct = ((act_train - tgt_train) / tgt_train * 100) if tgt_train else 0.0

        print(f"{cls:<8} | {total:<8} | {tgt_train:>4}/{tgt_val:>4}/{tgt_test:>4} {'':<2} | "
              f"{act_train:>4}/{act_val:>4}/{act_test:>4} {'':<2} | {train_err_pct:>7.1f}%")
    print("=" * 72)

    if excluded_bg > 0:
        print(f"\n⚠️  Note: {excluded_bg} background images were excluded due to BG_IMAGE_CAP={BG_IMAGE_CAP}")

def main():
    if not os.path.exists(DATASET_DIR):
        print(f"Error: Dataset directory '{DATASET_DIR}' not found.")
        return

    setup_dirs()

    # 1. Parse
    data = get_image_label_pairs(DATASET_DIR)

    # 2. Stratify aiming for instance-level targets (with bg cap)
    splits, global_counts, targets, excluded_bg = distribute_files(data)

    # 3. Copy
    copy_files(splits)

    # 4. Create YAML
    create_yaml()

    # 5. Report
    print_stats(splits, global_counts, targets, excluded_bg)
    print(f"\n✔ Dataset successfully saved to '{OUTPUT_DIR}'")

if __name__ == "__main__":
    main()
