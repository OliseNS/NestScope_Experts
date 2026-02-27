"""
Improved YOLO Nano Training Script for Bird Detection

This script trains a YOLOv8/YOLO26 Nano model on the nestvision dataset
with optimized hyperparameters for small datasets and aerial imagery.
"""

from ultralytics import YOLO
from pathlib import Path
import torch

def main():
    # Get absolute path to data configuration
    # IMPORTANT: Use absolute path to avoid issues when running from different directories
    script_dir = Path(__file__).parent
    data_yaml = script_dir / "donesplit" / "data.yaml"

    if not data_yaml.exists():
        raise FileNotFoundError(f"Data config not found: {data_yaml}")

    print(f"📂 Using dataset: {data_yaml}")
    print(f"📂 Working directory: {script_dir}")

    # Check if CUDA is available
    device = "0" if torch.cuda.is_available() else "cpu"
    print(f"🖥️  Device: {'GPU (CUDA)' if device == '0' else 'CPU'}")

    if device == "cpu":
        print("⚠️  WARNING: Training on CPU will be VERY slow!")

    # Load the YOLO26 Nano model (or YOLOv8 Nano)
    # The model file will be auto-downloaded if it doesn't exist
    print("\n📥 Loading YOLO26n model...")
    try:
        model = YOLO("yolo26n.pt")
    except Exception as e:
        print(f"⚠️  Could not load yolo26n.pt: {e}")
        print("📥 Falling back to YOLOv8n (YOLOv8 Nano)...")
        model = YOLO("yolov8n.pt")  # Fallback to standard YOLOv8 Nano

    # Calculate optimal batch size
    # For small datasets (501 images), batch size should be much smaller
    # Rule of thumb: batch_size = min(training_images / 5, GPU_capacity)
    num_train_images = 469

    if device == "0":
        # Assume you have good GPU with ~80GB VRAM as mentioned
        # For 1024x1024 images, even with 80GB, batch=64 is aggressive
        optimal_batch = min(32, num_train_images // 15)  # Conservative for stability
        print(f"💾 GPU detected - using batch size: {optimal_batch}")
    else:
        optimal_batch = 8  # CPU-friendly batch size
        print(f"💾 CPU detected - using batch size: {optimal_batch}")

    # Start training with optimized settings
    print("\n🚀 Starting training process...")
    print("=" * 60)

    results = model.train(
        # =================================================================
        # CORE SETTINGS
        # =================================================================
        data=str(data_yaml),         # Absolute path to data.yaml
        epochs=150,                  # Maximum epochs (early stopping will kick in)
        patience=50,                 # Stop if no improvement for 50 epochs

        imgsz=1024,                  # High-res for aerial tiny-object detection
                                     # Your images are already 1024-sized, so no resizing overhead

        batch=optimal_batch,         # FIXED: Batch size adjusted for dataset size
                                     # Original batch=64 was too high for 469 training images

        device=device,               # Auto-selected based on availability

        # =================================================================
        # OPTIMIZER & LEARNING
        # =================================================================
        optimizer="Adam",            # Adam is good for small datasets

        lr0=0.001,                   # Initial learning rate (Adam default)
        lrf=0.01,                    # Final learning rate (lr0 * lrf)

        momentum=0.937,              # SGD momentum (Adam ignores this)
        weight_decay=0.0005,         # L2 regularization

        warmup_epochs=3.0,           # Warm up learning rate over first 3 epochs
        warmup_momentum=0.8,         # Starting momentum during warmup

        # =================================================================
        # MULTI-SCALE TRAINING
        # =================================================================
        # FIXED: multi_scale should be True/False, not a float!
        # The original value of 0.2 was incorrect
        multi_scale=True,            # Enable multi-scale training

        # When multi_scale=True, training randomly scales images by ±50%
        # This helps the model generalize to different altitudes/zoom levels

        # =================================================================
        # DATA AUGMENTATION (Aerial Photography Optimized)
        # =================================================================
        degrees=180.0,               # ✓ Random rotation ±180° (birds can be any orientation)
        fliplr=0.5,                  # ✓ 50% chance horizontal flip
        flipud=0.5,                  # ✓ 50% chance vertical flip (good for aerial)

        mosaic=1.0,                  # ✓ Mosaic augmentation (combines 4 images)
                                     # Very effective for small object detection!

        scale=0.5,                   # ✓ Random scaling ±50%
        translate=0.1,               # Random translation ±10%

        # Additional augmentations
        hsv_h=0.015,                 # HSV-Hue augmentation (lighting variations)
        hsv_s=0.7,                   # HSV-Saturation (weather/time-of-day)
        hsv_v=0.4,                   # HSV-Value (brightness changes)

        mixup=0.0,                   # Mixup augmentation (disabled for aerial)
                                     # Mixup blends images which doesn't make sense for aerial

        copy_paste=0.0,              # Copy-paste augmentation (disabled)
                                     # Not ideal for aerial bird detection

        # =================================================================
        # LOSS FUNCTION WEIGHTS
        # =================================================================
        box=7.5,                     # Box loss weight (default)
        cls=0.5,                     # Classification loss (only 1 class, so low weight)
        dfl=1.5,                     # Distribution Focal Loss (for bbox regression)

        # =================================================================
        # MODEL ARCHITECTURE
        # =================================================================
        close_mosaic=10,             # Disable mosaic for last 10 epochs (fine-tuning)

        # =================================================================
        # OUTPUT & LOGGING
        # =================================================================
        project="nestvision_runs",   # Output directory
        name="yolo26n_nano_1024",    # Experiment name

        exist_ok=False,              # Don't overwrite existing runs (creates run1, run2, etc.)

        pretrained=True,             # Use pretrained weights (important!)

        verbose=True,                # Print detailed training info

        # =================================================================
        # SAVING & CHECKPOINTING
        # =================================================================
        save=True,                   # Save best.pt and last.pt
        save_period=10,              # Save checkpoint every 10 epochs (good for long training)

        plots=True,                  # Generate training plots

        # =================================================================
        # VALIDATION
        # =================================================================
        val=True,                    # Run validation during training

        # Increase validation frequency for small datasets
        # Default is every epoch, which is good for small datasets
    )

    print("\n" + "=" * 60)
    print("✅ Training complete!")
    print(f"📊 Results saved to: nestvision_runs/yolo26n_nano_1024")
    print(f"🏆 Best model: nestvision_runs/yolo26n_nano_1024/weights/best.pt")
    print(f"📈 Last model: nestvision_runs/yolo26n_nano_1024/weights/last.pt")
    print("\n🔄 To convert to ONNX:")
    print("   python convert_to_onnx.py --model nestvision_runs/yolo26n_nano_1024/weights/best.pt --imgsz 1024")

if __name__ == "__main__":
    main()
