#!/usr/bin/env python3
"""
SAHI Training Dataset Builder - Memory Efficient Version

Creates a 1024x1024 tiled dataset from variable-sized bird detection images.
Uses 20% overlap to ensure birds on tile boundaries are fully captured.
Limits background tiles to 10% of final dataset.

Memory efficient: Uses two-pass approach and streams tiles to disk immediately.
"""

import os
from pathlib import Path
from PIL import Image
from tqdm import tqdm
import random
import argparse


def parse_yolo_label(label_path):
    """
    Parse YOLO format label file.
    Returns list of (class_id, x_center, y_center, width, height) in normalized coords.
    """
    if not os.path.exists(label_path):
        return []

    annotations = []
    with open(label_path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            if len(parts) == 5:
                class_id = int(parts[0])
                x_center = float(parts[1])
                y_center = float(parts[2])
                width = float(parts[3])
                height = float(parts[4])
                annotations.append((class_id, x_center, y_center, width, height))
    return annotations


def save_yolo_label(annotations, label_path):
    """Save annotations in YOLO format."""
    with open(label_path, 'w') as f:
        for class_id, x_center, y_center, width, height in annotations:
            f.write(f"{class_id} {x_center:.6f} {y_center:.6f} {width:.6f} {height:.6f}\n")


def get_tile_coordinates(img_width, img_height, tile_size=1024, overlap_ratio=0.2):
    """
    Calculate tile coordinates with overlap.

    Returns list of (x_min, y_min, x_max, y_max) tuples.
    """
    tiles = []
    stride = int(tile_size * (1 - overlap_ratio))  # 20% overlap = 80% stride

    # Calculate tile positions
    x_positions = list(range(0, img_width - tile_size + 1, stride))
    y_positions = list(range(0, img_height - tile_size + 1, stride))

    # Add final tiles if we didn't cover the full image
    if not x_positions or x_positions[-1] + tile_size < img_width:
        x_positions.append(max(0, img_width - tile_size))
    if not y_positions or y_positions[-1] + tile_size < img_height:
        y_positions.append(max(0, img_height - tile_size))

    for y in y_positions:
        for x in x_positions:
            tiles.append((x, y, x + tile_size, y + tile_size))

    return tiles


def transform_annotations_to_tile(annotations, tile_coords, img_width, img_height):
    """
    Transform annotations from original image coordinates to tile coordinates.
    Returns list of annotations that overlap with the tile.
    """
    x_min, y_min, x_max, y_max = tile_coords
    tile_width = x_max - x_min
    tile_height = y_max - y_min

    transformed = []

    for class_id, x_center_norm, y_center_norm, width_norm, height_norm in annotations:
        # Convert to absolute pixel coordinates
        x_center_abs = x_center_norm * img_width
        y_center_abs = y_center_norm * img_height
        width_abs = width_norm * img_width
        height_abs = height_norm * img_height

        # Calculate bbox boundaries
        bbox_x_min = x_center_abs - width_abs / 2
        bbox_y_min = y_center_abs - height_abs / 2
        bbox_x_max = x_center_abs + width_abs / 2
        bbox_y_max = y_center_abs + height_abs / 2

        # Check overlap with tile
        if bbox_x_max < x_min or bbox_x_min > x_max:
            continue
        if bbox_y_max < y_min or bbox_y_min > y_max:
            continue

        # Clip to tile boundaries
        clipped_x_min = max(bbox_x_min, x_min)
        clipped_y_min = max(bbox_y_min, y_min)
        clipped_x_max = min(bbox_x_max, x_max)
        clipped_y_max = min(bbox_y_max, y_max)

        # Calculate clipped dimensions
        new_width_abs = clipped_x_max - clipped_x_min
        new_height_abs = clipped_y_max - clipped_y_min
        new_x_center_abs = (clipped_x_min + clipped_x_max) / 2
        new_y_center_abs = (clipped_y_min + clipped_y_max) / 2

        # Convert to tile-relative coordinates
        tile_x_center = new_x_center_abs - x_min
        tile_y_center = new_y_center_abs - y_min

        # Normalize to tile dimensions
        tile_x_center_norm = tile_x_center / tile_width
        tile_y_center_norm = tile_y_center / tile_height
        tile_width_norm = new_width_abs / tile_width
        tile_height_norm = new_height_abs / tile_height

        # Filter out very small slivers
        if tile_width_norm > 0.01 and tile_height_norm > 0.01:
            transformed.append((
                class_id,
                tile_x_center_norm,
                tile_y_center_norm,
                tile_width_norm,
                tile_height_norm
            ))

    return transformed


def count_tiles_pass(image_files, source_labels_dir, tile_size, overlap_ratio):
    """
    Pass 1: Count tiles without loading images into memory.
    Returns counts and tile metadata for each image.
    """
    tile_metadata = []  # List of (img_path, img_name, tile_idx, has_birds)

    print("Pass 1/2: Counting tiles...")
    for img_path in tqdm(image_files, desc="Analyzing images"):
        img_name = img_path.stem
        label_path = source_labels_dir / f"{img_name}.txt"

        # Get image dimensions without loading full image
        with Image.open(img_path) as img:
            img_width, img_height = img.size

        # Load annotations
        annotations = parse_yolo_label(label_path)

        # Get tile coordinates
        tile_coords_list = get_tile_coordinates(img_width, img_height, tile_size, overlap_ratio)

        # For each tile, check if it contains birds
        for tile_idx, tile_coords in enumerate(tile_coords_list):
            tile_annotations = transform_annotations_to_tile(
                annotations, tile_coords, img_width, img_height
            )
            has_birds = len(tile_annotations) > 0

            tile_metadata.append({
                'img_path': img_path,
                'img_name': img_name,
                'tile_idx': tile_idx,
                'tile_coords': tile_coords,
                'has_birds': has_birds,
                'img_width': img_width,
                'img_height': img_height
            })

    return tile_metadata


def process_tiles_pass(
    tile_metadata,
    source_labels_dir,
    output_images_dir,
    output_labels_dir,
    background_sample_prob
):
    """
    Pass 2: Process and save tiles immediately (streaming).
    Uses sampling probability for background tiles.
    """
    tiles_saved = {'with_birds': 0, 'background': 0}

    print("\nPass 2/2: Processing and saving tiles...")

    # Group tiles by image to minimize image loading
    from collections import defaultdict
    tiles_by_image = defaultdict(list)
    for tile_info in tile_metadata:
        tiles_by_image[str(tile_info['img_path'])].append(tile_info)

    # Process each image
    for img_path_str, tiles in tqdm(tiles_by_image.items(), desc="Processing images"):
        img_path = Path(img_path_str)
        img_name = tiles[0]['img_name']
        img_width = tiles[0]['img_width']
        img_height = tiles[0]['img_height']

        # Load image once for all tiles
        img = Image.open(img_path)

        # Load annotations once
        label_path = source_labels_dir / f"{img_name}.txt"
        annotations = parse_yolo_label(label_path)

        # Process each tile from this image
        for tile_info in tiles:
            tile_idx = tile_info['tile_idx']
            tile_coords = tile_info['tile_coords']
            has_birds = tile_info['has_birds']

            # Skip background tiles based on sampling probability
            if not has_birds and random.random() > background_sample_prob:
                continue

            # Crop tile
            x_min, y_min, x_max, y_max = tile_coords
            tile_img = img.crop((x_min, y_min, x_max, y_max))

            # Transform annotations
            tile_annotations = transform_annotations_to_tile(
                annotations, tile_coords, img_width, img_height
            )

            # Generate tile name
            tile_name = f"{img_name}_tile_{tile_idx}"

            # Save image immediately
            img_output_path = output_images_dir / f"{tile_name}.jpg"
            tile_img.save(img_output_path, quality=95)

            # Save label immediately
            label_output_path = output_labels_dir / f"{tile_name}.txt"
            save_yolo_label(tile_annotations, label_output_path)

            # Track statistics
            if has_birds:
                tiles_saved['with_birds'] += 1
            else:
                tiles_saved['background'] += 1

        # Close image to free memory
        img.close()

    return tiles_saved


def build_sahi_dataset(
    source_dir,
    output_dir,
    tile_size=1024,
    overlap_ratio=0.2,
    max_background_ratio=0.1
):
    """
    Build SAHI training dataset using memory-efficient two-pass approach.
    """
    source_dir = Path(source_dir)
    output_dir = Path(output_dir)

    # Create output directories
    output_images_dir = output_dir / 'images'
    output_labels_dir = output_dir / 'labels'
    output_images_dir.mkdir(parents=True, exist_ok=True)
    output_labels_dir.mkdir(parents=True, exist_ok=True)

    # Get all source images
    source_images_dir = source_dir / 'images'
    source_labels_dir = source_dir / 'labels'

    image_files = sorted(source_images_dir.glob('*.jpg')) + sorted(source_images_dir.glob('*.png'))

    print(f"╔═══════════════════════════════════════════════════════╗")
    print(f"║         SAHI Training Dataset Builder                ║")
    print(f"╚═══════════════════════════════════════════════════════╝")
    print(f"\nConfiguration:")
    print(f"  Source images: {len(image_files)}")
    print(f"  Tile size: {tile_size}×{tile_size}")
    print(f"  Overlap: {int(overlap_ratio * 100)}%")
    print(f"  Max background ratio: {int(max_background_ratio * 100)}%")
    print()

    # Pass 1: Count tiles (lightweight)
    tile_metadata = count_tiles_pass(image_files, source_labels_dir, tile_size, overlap_ratio)

    # Calculate statistics
    tiles_with_birds = sum(1 for t in tile_metadata if t['has_birds'])
    total_background = sum(1 for t in tile_metadata if not t['has_birds'])

    # Calculate background sampling probability
    # We want: background_kept / (tiles_with_birds + background_kept) = max_background_ratio
    # Solving: background_kept = tiles_with_birds * max_background_ratio / (1 - max_background_ratio)
    background_to_keep = int(tiles_with_birds * max_background_ratio / (1 - max_background_ratio))
    background_sample_prob = min(1.0, background_to_keep / total_background if total_background > 0 else 0)

    print(f"\nTile Statistics:")
    print(f"  Tiles with birds: {tiles_with_birds:,}")
    print(f"  Background tiles (total): {total_background:,}")
    print(f"  Background tiles (to keep): ~{background_to_keep:,}")
    print(f"  Background sampling probability: {background_sample_prob:.2%}")
    print()

    # Pass 2: Process and save tiles (streaming)
    tiles_saved = process_tiles_pass(
        tile_metadata,
        source_labels_dir,
        output_images_dir,
        output_labels_dir,
        background_sample_prob
    )

    total_tiles = tiles_saved['with_birds'] + tiles_saved['background']

    # Create data.yaml
    data_yaml_path = output_dir / 'data.yaml'
    with open(data_yaml_path, 'w') as f:
        f.write(f"# SAHI Bird Detection Dataset\n")
        f.write(f"# Generated from {source_dir}\n")
        f.write(f"# Tile size: {tile_size}x{tile_size}, Overlap: {int(overlap_ratio * 100)}%\n")
        f.write(f"\n")
        f.write(f"path: {output_dir.absolute()}\n")
        f.write(f"train: images\n")
        f.write(f"val: images\n")
        f.write(f"\n")
        f.write(f"nc: 1\n")
        f.write(f"names: ['bird']\n")

    # Print summary
    print(f"\n{'='*60}")
    print(f"✓ Dataset created successfully!")
    print(f"{'='*60}")
    print(f"Output directory: {output_dir}")
    print(f"\nFinal Dataset:")
    print(f"  Total tiles: {total_tiles:,}")
    print(f"  Tiles with birds: {tiles_saved['with_birds']:,} ({100 * tiles_saved['with_birds'] / total_tiles:.1f}%)")
    print(f"  Background tiles: {tiles_saved['background']:,} ({100 * tiles_saved['background'] / total_tiles:.1f}%)")
    print(f"\nReady to train!")
    print(f"  Command: python train.py --data {data_yaml_path}")
    print(f"{'='*60}\n")


def main():
    parser = argparse.ArgumentParser(
        description='Build SAHI training dataset from bird detection images',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example usage:
  python build_sahi_training_dataset.py --source bird_detection_dataset --output stage_2_1024

This will create a memory-efficient tiled dataset with 20%% overlap and 10%% background tiles.
        """
    )
    parser.add_argument('--source', type=str, default='bird_detection_dataset',
                        help='Source dataset directory (default: bird_detection_dataset)')
    parser.add_argument('--output', type=str, default='bird_detection_dataset_sahi',
                        help='Output dataset directory (default: bird_detection_dataset_sahi)')
    parser.add_argument('--tile-size', type=int, default=1024,
                        help='Tile size in pixels (default: 1024)')
    parser.add_argument('--overlap', type=float, default=0.2,
                        help='Overlap ratio between tiles (default: 0.2 = 20%%)')
    parser.add_argument('--max-background', type=float, default=0.1,
                        help='Maximum background tile ratio (default: 0.1 = 10%%)')

    args = parser.parse_args()

    # Validate arguments
    if args.tile_size <= 0:
        parser.error("Tile size must be positive")
    if not 0 <= args.overlap < 1:
        parser.error("Overlap must be between 0 and 1")
    if not 0 <= args.max_background < 1:
        parser.error("Max background ratio must be between 0 and 1")

    build_sahi_dataset(
        source_dir=args.source,
        output_dir=args.output,
        tile_size=args.tile_size,
        overlap_ratio=args.overlap,
        max_background_ratio=args.max_background
    )


if __name__ == '__main__':
    main()
