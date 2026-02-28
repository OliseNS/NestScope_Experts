"""
Create Optimized Cluster Visualization Data

This script creates an optimized version of the cluster data for web visualization:
1. Keeps all 100K birds (no sampling)
2. Pre-generates low-res thumbnails for fast loading
3. Creates spatial index for efficient frustum culling
4. Organizes data for progressive loading
"""

import sys
from pathlib import Path
import json
import numpy as np
from PIL import Image
import cv2
from tqdm import tqdm

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))


def create_thumbnail(image_path, output_path, size=(32, 32)):
    """Create a tiny thumbnail for placeholder"""
    try:
        img = cv2.imread(str(image_path))
        if img is None:
            return False

        # Resize to thumbnail
        thumb = cv2.resize(img, size, interpolation=cv2.INTER_AREA)

        # Save with high compression
        cv2.imwrite(str(output_path), thumb, [cv2.IMWRITE_JPEG_QUALITY, 60])
        return True
    except Exception as e:
        print(f"Error creating thumbnail: {e}")
        return False


def create_spatial_index(positions, grid_size=20):
    """
    Create spatial grid index for fast frustum culling.

    Returns dict mapping grid cells to bird indices.
    """
    # Find bounds
    x_coords = [p['x'] for p in positions]
    y_coords = [p['y'] for p in positions]

    x_min, x_max = min(x_coords), max(x_coords)
    y_min, y_max = min(y_coords), max(y_coords)

    # Create grid
    cell_width = (x_max - x_min) / grid_size
    cell_height = (y_max - y_min) / grid_size

    spatial_index = {}

    for idx, pos in enumerate(positions):
        # Calculate grid cell
        cell_x = int((pos['x'] - x_min) / cell_width)
        cell_y = int((pos['y'] - y_min) / cell_height)

        # Clamp to grid
        cell_x = max(0, min(grid_size - 1, cell_x))
        cell_y = max(0, min(grid_size - 1, cell_y))

        cell_key = f"{cell_x},{cell_y}"

        if cell_key not in spatial_index:
            spatial_index[cell_key] = []

        spatial_index[cell_key].append(idx)

    return {
        'grid_size': grid_size,
        'bounds': {
            'x_min': x_min, 'x_max': x_max,
            'y_min': y_min, 'y_max': y_max
        },
        'cell_width': cell_width,
        'cell_height': cell_height,
        'cells': spatial_index
    }


def create_optimized_data(clusters_json_path, images_dir, output_dir):
    """
    Create optimized visualization data.
    """
    print("Loading cluster data...")
    with open(clusters_json_path, 'r') as f:
        data = json.load(f)

    positions = data['positions']
    print(f"Processing {len(positions)} birds...")

    # Create output directories
    output_dir = Path(output_dir)
    thumbs_dir = output_dir / "thumbnails"
    thumbs_dir.mkdir(parents=True, exist_ok=True)

    # Step 1: Create thumbnails
    print("\n[1/3] Generating thumbnails...")
    thumbnail_map = {}

    for pos in tqdm(positions[:1000], desc="Creating thumbnails (first 1000 only)"):
        # Only create thumbnails for first 1000 for now
        bird_id = pos['bird_id']
        crop_filename = pos['image_name']

        image_path = images_dir / crop_filename
        thumb_path = thumbs_dir / f"thumb_{bird_id:06d}.jpg"

        if create_thumbnail(image_path, thumb_path):
            thumbnail_map[bird_id] = str(thumb_path.relative_to(output_dir))

    # Step 2: Create spatial index
    print("\n[2/3] Building spatial index...")
    spatial_index = create_spatial_index(positions)

    # Step 3: Create metadata chunks for progressive loading
    print("\n[3/3] Creating metadata chunks...")
    chunk_size = 5000
    chunks = []

    for i in range(0, len(positions), chunk_size):
        chunk = positions[i:i + chunk_size]
        chunk_file = output_dir / f"chunk_{i//chunk_size:03d}.json"

        with open(chunk_file, 'w') as f:
            json.dump({
                'start_index': i,
                'count': len(chunk),
                'positions': chunk
            }, f)

        chunks.append({
            'file': f"chunk_{i//chunk_size:03d}.json",
            'start_index': i,
            'count': len(chunk)
        })

    # Save manifest
    manifest = {
        'total_birds': len(positions),
        'n_clusters': data['n_clusters'],
        'clusters': data['clusters'],
        'chunk_size': chunk_size,
        'chunks': chunks,
        'spatial_index': spatial_index,
        'optimization': {
            'thumbnails_generated': len(thumbnail_map),
            'spatial_grid_size': spatial_index['grid_size'],
            'recommended_load_strategy': 'frustum_culling'
        }
    }

    manifest_path = output_dir / "manifest.json"
    with open(manifest_path, 'w') as f:
        json.dump(manifest, f, indent=2)

    print(f"\n✓ Optimization complete!")
    print(f"  Output: {output_dir}")
    print(f"  Manifest: {manifest_path}")
    print(f"  Chunks: {len(chunks)}")
    print(f"  Thumbnails: {len(thumbnail_map)}")


def main():
    clusters_json = Path("data/weak_supervision/bird_crops/species_clusters/clusters_for_labeling.json")
    images_dir = Path("data/weak_supervision/bird_crops/images")
    output_dir = Path("labeller/nestvision/bird_crops/clusters_optimized")

    if not clusters_json.exists():
        print(f"Error: {clusters_json} not found")
        return

    if not images_dir.exists():
        print(f"Error: {images_dir} not found")
        return

    create_optimized_data(clusters_json, images_dir, output_dir)


if __name__ == '__main__':
    main()
