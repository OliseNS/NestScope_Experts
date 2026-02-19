"""
Convert YOLO format nest vision dataset to DeepForest/RetinaNet CSV format.
Splits dataset into 90% train / 10% validation.
Properly handles background (negative) images with empty values.
"""

import os
import pandas as pd
import random
from PIL import Image
from pathlib import Path

# Set random seed for reproducibility
random.seed(42)

def yolo_to_corners(x_center, y_center, width, height, img_width, img_height):
    # Convert normalized to absolute coordinates
    abs_x_center = x_center * img_width
    abs_y_center = y_center * img_height
    abs_width = width * img_width
    abs_height = height * img_height

    # Calculate corners
    xmin = abs_x_center - (abs_width / 2)
    ymin = abs_y_center - (abs_height / 2)
    xmax = abs_x_center + (abs_width / 2)
    ymax = abs_y_center + (abs_height / 2)

    # Ensure coordinates are within image bounds
    xmin = max(0, int(xmin))
    ymin = max(0, int(ymin))
    xmax = min(img_width, int(xmax))
    ymax = min(img_height, int(ymax))

    return xmin, ymin, xmax, ymax


def convert_yolo_to_deepforest(images_dir, labels_dir, output_dir, train_ratio=0.9):
    images_dir = Path(images_dir)
    labels_dir = Path(labels_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True, parents=True)

    # Get all image files
    image_files = sorted([f for f in images_dir.iterdir() if f.suffix.lower() in ['.jpg', '.jpeg', '.png']])
    print(f"Found {len(image_files)} images")

    all_annotations = []
    images_with_birds = 0
    images_without_birds = 0
    total_birds = 0

    for img_path in image_files:
        label_path = labels_dir / f"{img_path.stem}.txt"
        
        # Get image dimensions
        try:
            with Image.open(img_path) as img:
                img_width, img_height = img.size
        except Exception as e:
            print(f"Error reading image {img_path.name}: {e}")
            continue

        has_birds = False
        
        # Check if label exists AND has content
        if label_path.exists() and label_path.stat().st_size > 0:
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

                        # Convert to corner format
                        xmin, ymin, xmax, ymax = yolo_to_corners(
                            x_center, y_center, width, height, img_width, img_height
                        )

                        all_annotations.append({
                            'image_path': img_path.name,
                            'xmin': xmin,
                            'ymin': ymin,
                            'xmax': xmax,
                            'ymax': ymax,
                            'label': 'bird' 
                        })
                        has_birds = True
                        total_birds += 1
        
        # If no birds were found (no txt file, or empty txt file), add as background
        if not has_birds:
            all_annotations.append({
                'image_path': img_path.name,
                'xmin': '',
                'ymin': '',
                'xmax': '',
                'ymax': '',
                'label': ''
            })
            images_without_birds += 1
        else:
            images_with_birds += 1

    print(f"\nDataset Statistics:")
    print(f"  Total images processed: {len(image_files)}")
    print(f"  Images with birds: {images_with_birds}")
    print(f"  Background images (no birds): {images_without_birds}")
    print(f"  Total bird annotations: {total_birds}")

    if not all_annotations:
        print("Error: No valid images found!")
        return

    # Create DataFrame
    df = pd.DataFrame(all_annotations)

    # Get unique images to ensure no data leakage between train and val
    unique_images = df['image_path'].unique()
    random.shuffle(unique_images)

    # Split images
    n_train = int(len(unique_images) * train_ratio)
    train_images = unique_images[:n_train]
    val_images = unique_images[n_train:]

    # Filter dataframe based on image splits
    train_df = df[df['image_path'].isin(train_images)]
    val_df = df[df['image_path'].isin(val_images)]

    # Save annotation CSV files
    train_path = output_dir / 'train_annotations.csv'
    val_path = output_dir / 'val_annotations.csv'

    train_df.to_csv(train_path, index=False)
    val_df.to_csv(val_path, index=False)

    print(f"\nSplit Statistics:")
    print(f"  TRAINING set: {len(train_images)} images ({len(train_df[train_df['label'] == 'bird'])} bird boxes)")
    print(f"  VALIDATION set: {len(val_images)} images ({len(val_df[val_df['label'] == 'bird'])} bird boxes)")
    print(f"\nSaved CSVs to {output_dir}")

    return train_df, val_df

if __name__ == "__main__":
    BASE_DIR = Path(__file__).parent / "nestvision"
    IMAGES_DIR = BASE_DIR / "images"
    LABELS_DIR = BASE_DIR / "labels"
    OUTPUT_DIR = BASE_DIR 

    print("=" * 70)
    print("Converting NestVision Dataset to DeepForest Format")
    print("=" * 70)

    result = convert_yolo_to_deepforest(
        images_dir=IMAGES_DIR,
        labels_dir=LABELS_DIR,
        output_dir=OUTPUT_DIR,
        train_ratio=0.9
    )