"""
Build two datasets from the Big Bird annotated dataset:
1. Detection dataset: YOLO format with single "bird" class
2. Classification dataset: Cropped bird images for species classification
"""

import json
import os
import shutil
from pathlib import Path
from PIL import Image
import ast
from collections import defaultdict
import random
import sys

def polygon_to_bbox(points):
    """Convert polygon points to bounding box [x_min, y_min, x_max, y_max]"""
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return [min(xs), min(ys), max(xs), max(ys)]

def rectangle_to_bbox(points):
    """Convert rectangle (2 points) to bounding box [x_min, y_min, x_max, y_max]"""
    x1, y1 = points[0]
    x2, y2 = points[1]
    return [min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2)]

def bbox_to_yolo(bbox, img_width, img_height):
    """Convert bbox to YOLO format: [x_center, y_center, width, height] normalized"""
    x_min, y_min, x_max, y_max = bbox

    x_center = (x_min + x_max) / 2 / img_width
    y_center = (y_min + y_max) / 2 / img_height
    width = (x_max - x_min) / img_width
    height = (y_max - y_min) / img_height

    # Clamp values to [0, 1]
    x_center = max(0, min(1, x_center))
    y_center = max(0, min(1, y_center))
    width = max(0, min(1, width))
    height = max(0, min(1, height))

    return [x_center, y_center, width, height]

def parse_label(label_str):
    """Parse the label string to extract species name"""
    try:
        label_dict = ast.literal_eval(label_str)
        species_name = label_dict.get('name', 'unknown').lower().replace(' ', '_').replace('-', '_')
        return species_name
    except:
        return 'unknown'

def process_annotations(source_dir, detect_dir, classify_dir, max_bg_percent=0.10):
    """
    Process all annotations and create two datasets.
    """
    source_path = Path(source_dir)
    detect_path = Path(detect_dir)
    classify_path = Path(classify_dir)

    # Create output directories
    print("Creating output directories...")
    (detect_path / 'images').mkdir(parents=True, exist_ok=True)
    (detect_path / 'labels').mkdir(parents=True, exist_ok=True)

    # Get all JSON annotation files
    json_files = list(source_path.glob('*.json'))
    total_files = len(json_files)
    print(f"Found {total_files} annotation files")

    # Track statistics
    stats = {
        'total_images': 0,
        'images_with_birds': 0,
        'background_images': 0,
        'total_birds': 0,
        'birds_by_species': defaultdict(int),
        'skipped_no_image': 0,
        'detection_saved': 0,
        'crops_saved': 0
    }

    background_images = []

    print("\nProcessing annotations...")
    for idx, json_file in enumerate(json_files, 1):
        # Progress update every 100 files
        if idx % 100 == 0 or idx == total_files:
            progress = (idx / total_files) * 100
            print(f"Progress: {idx}/{total_files} ({progress:.1f}%) - Birds: {stats['total_birds']}, Crops: {stats['crops_saved']}")
            sys.stdout.flush()

        try:
            with open(json_file, 'r') as f:
                data = json.load(f)
        except Exception as e:
            print(f"\nError reading {json_file}: {e}")
            continue

        # Get corresponding image
        image_name = data.get('imagePath')
        if not image_name:
            stats['skipped_no_image'] += 1
            continue

        image_path = source_path / image_name

        if not image_path.exists():
            stats['skipped_no_image'] += 1
            continue

        stats['total_images'] += 1

        # Get image dimensions
        img_width = data.get('imageWidth')
        img_height = data.get('imageHeight')

        if not img_width or not img_height:
            print(f"\nSkipping {json_file}: missing dimensions")
            continue

        shapes = data.get('shapes', [])

        # Check if this is a background image (no birds)
        if len(shapes) == 0:
            background_images.append((image_path, json_file.stem))
            continue

        stats['images_with_birds'] += 1

        # Process each bird annotation
        yolo_lines = []

        for shape in shapes:
            shape_type = shape.get('shape_type')
            points = shape.get('points')
            label_str = shape.get('label', '')

            if not shape_type or not points:
                continue

            # Convert to bounding box
            try:
                if shape_type == 'polygon':
                    bbox = polygon_to_bbox(points)
                elif shape_type == 'rectangle':
                    bbox = rectangle_to_bbox(points)
                else:
                    continue
            except Exception as e:
                print(f"\nError converting shape in {json_file}: {e}")
                continue

            # Get species name for classification dataset
            species_name = parse_label(label_str)
            stats['birds_by_species'][species_name] += 1
            stats['total_birds'] += 1

            # Save crop for classification dataset
            try:
                img = Image.open(image_path)
                x_min, y_min, x_max, y_max = bbox

                # Ensure bbox is within image bounds
                x_min = max(0, int(x_min))
                y_min = max(0, int(y_min))
                x_max = min(img_width, int(x_max))
                y_max = min(img_height, int(y_max))

                # Skip invalid boxes
                if x_max <= x_min or y_max <= y_min:
                    continue

                crop = img.crop((x_min, y_min, x_max, y_max))

                # Create species directory
                species_dir = classify_path / species_name
                species_dir.mkdir(parents=True, exist_ok=True)

                # Save crop with unique name
                crop_name = f"{json_file.stem}_{len(yolo_lines)}.jpg"
                crop.save(species_dir / crop_name, quality=95)
                stats['crops_saved'] += 1

            except Exception as e:
                print(f"\nError cropping bird from {image_path}: {e}")

            # Convert to YOLO format for detection dataset (class 0 = bird)
            try:
                yolo_bbox = bbox_to_yolo(bbox, img_width, img_height)
                yolo_lines.append(f"0 {yolo_bbox[0]:.6f} {yolo_bbox[1]:.6f} {yolo_bbox[2]:.6f} {yolo_bbox[3]:.6f}")
            except Exception as e:
                print(f"\nError converting to YOLO format: {e}")

        # Save detection dataset files
        if yolo_lines:
            try:
                # Copy image
                dest_image = detect_path / 'images' / image_name
                shutil.copy2(image_path, dest_image)

                # Save YOLO label
                label_file = detect_path / 'labels' / f"{json_file.stem}.txt"
                with open(label_file, 'w') as f:
                    f.write('\n'.join(yolo_lines))

                stats['detection_saved'] += 1
            except Exception as e:
                print(f"\nError saving detection data for {image_name}: {e}")

    # Add background images (up to 10% of total)
    print("\nAdding background images...")
    max_background = int(stats['images_with_birds'] * max_bg_percent)

    if len(background_images) > max_background:
        background_images = random.sample(background_images, max_background)

    stats['background_images'] = len(background_images)

    for bg_image_path, stem in background_images:
        try:
            # Copy image
            image_name = bg_image_path.name
            dest_image = detect_path / 'images' / image_name
            shutil.copy2(bg_image_path, dest_image)

            # Create empty label file
            label_file = detect_path / 'labels' / f"{stem}.txt"
            label_file.touch()
        except Exception as e:
            print(f"Error adding background image {bg_image_path}: {e}")

    # Create data.yaml for detection dataset
    print("Creating data.yaml...")
    data_yaml = f"""# Bird Detection Dataset
# Single class: bird

path: {detect_path.absolute()}
train: images
val: images

nc: 1
names: ['bird']
"""

    with open(detect_path / 'data.yaml', 'w') as f:
        f.write(data_yaml)

    # Create classes.txt for classification dataset
    print("Creating classes.txt...")
    species_list = sorted(stats['birds_by_species'].keys())
    with open(classify_path / 'classes.txt', 'w') as f:
        f.write('\n'.join(species_list))

    # Print statistics
    print("\n" + "="*60)
    print("DATASET CREATION COMPLETE")
    print("="*60)
    print(f"\nDetection Dataset: {detect_path}")
    print(f"  - Images with birds: {stats['detection_saved']}")
    print(f"  - Background images: {stats['background_images']} ({max_bg_percent*100:.0f}% of total)")
    print(f"  - Total images: {stats['detection_saved'] + stats['background_images']}")
    print(f"  - Total bird annotations: {stats['total_birds']}")

    print(f"\nClassification Dataset: {classify_path}")
    print(f"  - Total crops saved: {stats['crops_saved']}")
    print(f"  - Number of species: {len(species_list)}")
    print(f"  - Species distribution (top 10):")
    for species, count in sorted(stats['birds_by_species'].items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"    {species}: {count}")
    if len(stats['birds_by_species']) > 10:
        print(f"    ... and {len(stats['birds_by_species']) - 10} more species")

    print(f"\nSkipped (no image file): {stats['skipped_no_image']}")
    print("="*60)

if __name__ == '__main__':
    # Set random seed for reproducibility
    random.seed(42)

    # Define paths
    source_dir = '/home/olisemeka.dev/Projects/nexus/annotated_dataset'
    detect_dir = '/home/olisemeka.dev/Projects/nexus/bird_detection_dataset'
    classify_dir = '/home/olisemeka.dev/Projects/nexus/bird_classification_dataset'

    print("Building bird datasets from Big Bird annotated data...")
    print(f"Source: {source_dir}")
    print(f"Detection output: {detect_dir}")
    print(f"Classification output: {classify_dir}\n")

    process_annotations(source_dir, detect_dir, classify_dir, max_bg_percent=0.10)

    print("\nDone!")
