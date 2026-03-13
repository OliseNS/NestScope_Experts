"""
YOLOv26n Fine-Tuning Script for Bird Detection
==============================================

This script fine-tunes an ALREADY TRAINED swift.pt model for improved:
- RECALL: Detect more birds (minimize missed detections)
- BOX TIGHTNESS: Tighter, more accurate bounding boxes (higher IoU)
- ROBUSTNESS: Handle various scales, occlusions, and lighting

Training Strategy (SCALED FOR 16K IMAGES):
- Swift.pt trained on ~500 images, this dataset has 16,787 (33x MORE!)
- 100 epochs (each epoch sees 33x more data than original training)
- Learning rate 0.0005 (higher than typical fine-tuning - large dataset allows this)
- HIGHER BOX LOSS (10.0) - forces tighter, more precise boxes
- LOWER CLASS LOSS (0.3) - prioritize finding birds over classification confidence
- HIGHER DFL (2.0) - better box corner localization
- MULTISCALE TRAINING (CRITICAL) - varies input resolution for robustness
- Heavy augmentation - reinforce learning with massive dataset

Key Features:
- TRUE multi-scale training (varies input size across batches)
- Scale augmentation ±20% (varies object size within images)
- Mosaic (100%), MixUp (15%), Copy-Paste (30%) for robustness
- Base 1024x1024 input resolution for small bird detection
- Early stopping (35 epochs patience) to prevent degradation
- Parameters tuned for LARGE dataset (not tiny 500-image datasets)

Dataset: licksplit/
- 16,787 bird images across train/val/test splits (33x larger than swift.pt's training data!)
- Single class: 'bird'
"""

from ultralytics import YOLO
import torch
import yaml
from pathlib import Path
import argparse


def setup_training_config():
    """
    Configure training hyperparameters for FINE-TUNING swift.pt.

    Focus: RECALL (detect more birds) + BOX TIGHTNESS (accurate localization)

    Fine-Tuning Strategy for LARGE DATASET (16,787 images vs swift.pt's 500):
    -------------------------------------------------------------------------
    Swift.pt was trained on ~500 images. This dataset is 33x LARGER!

    This changes everything:
    - 100 epochs (not 75) - with 16K images, each epoch sees 33x more data
      * Original: 500 epochs × 500 images = 250K training views
      * Ours: 100 epochs × 16K images = 1.6M training views (6x more!)

    - Learning rate 0.0005 (not 0.0002) - larger dataset = more stable gradients
      * More data means gradient estimates are reliable, can train faster
      * Still conservative enough to preserve swift.pt's knowledge

    - Patience 35 (not 25) - more data = training more stable but takes longer

    - Box loss 10.0 (HIGH) - prioritize tight, accurate boxes
    - Class loss 0.3 (LOW) - focus on detection recall over confidence
    - DFL 2.0 (HIGH) - better corner localization for precise boxes
    - MULTISCALE 0.2 - trains on varying image sizes for robustness

    Large dataset is a HUGE advantage: natural regularization, more diversity,
    better generalization. We can train more aggressively without overfitting.

    IMPORTANT: Multi-Scale vs Scale Augmentation
    --------------------------------------------
    - multiscale=True: Varies INPUT IMAGE SIZE across batches (e.g., 640px, 768px, 896px)
                       → Model learns to detect at ANY resolution
    - scale=0.2: Scales OBJECTS within the image (zoom in/out on content)
                 → Model learns to detect birds at any apparent size

    BOTH are critical for a robust model!

    Augmentation Strategy Explained:
    --------------------------------
    1. **Mosaic (p=1.0)**: Combines 4 images into one. Forces model to learn
       birds at different scales simultaneously. Critical for multi-scale detection.

    2. **MixUp (p=0.15)**: Blends two images together. Teaches model to handle
       overlapping/occluded birds by learning from partially transparent instances.

    3. **Copy-Paste (p=0.3)**: Copies bird instances and pastes them elsewhere
       in the image. Increases effective dataset size and helps with class imbalance.
       Especially useful for small birds.

    4. **HSV Augmentation**: Color jittering simulates different lighting:
       - Hue shift (0.015): Subtle color changes (morning vs evening light)
       - Saturation (0.7): Handles overcast vs sunny conditions
       - Value (0.4): Brightness variations (shadows, highlights)

    5. **Geometric Augmentations**:
       - Flip (50%): Horizontal flips (birds can face any direction)
       - Rotation (0°): Disabled to preserve natural bird orientations
       - Translate (0.1): Small shifts to learn position invariance
       - Scale (0.9): Combined with multi-scale training for size variations
       - Shear (0.0): Disabled to preserve bird shape
       - Perspective (0.0001): Very subtle to avoid unrealistic distortions

    6. **Image Quality Augmentations**:
       - Blur (0.01): Simulates motion blur or out-of-focus birds
       - Noise (0.02): Adds Gaussian noise for sensor noise robustness

    Why These Values?
    ----------------
    Birds are relatively rigid objects (unlike humans with many poses), so we:
    - Keep rotation/shear minimal to preserve natural appearance
    - Use heavy mosaic/mixup for scale/occlusion robustness
    - Moderate color augmentation (birds have distinctive plumage)
    - Light blur/noise to handle real-world image quality issues
    """

    training_config = {
        # ============ Core Training Parameters ============
        'epochs': 200,              # 200 epochs for 16K images (vs 500 on original 500 images)
        'patience': 35,             # Early stopping after 35 epochs (more data = more stable)
        'batch': 16,                # Batch size (adjust based on GPU memory)
        'imgsz': 1024,              # Input image size (larger = better small bird detection)
        'device': 0,                # GPU device (0 = first GPU, 'cpu' for CPU)
        'workers': 8,               # Data loading workers (increase if CPU has cores)

        # ============ Learning Rate & Optimizer ============
        'lr0': 0.0005,              # Higher LR for large dataset (16K images, not 500!)
        'lrf': 0.01,                # Final learning rate (lr0 * lrf at end)
        'momentum': 0.937,          # SGD momentum
        'weight_decay': 0.0005,     # L2 regularization (large dataset = natural regularization)
        'warmup_epochs': 3.0,       # 3 epoch warmup (more data = longer warmup helps)
        'warmup_momentum': 0.8,     # Starting momentum during warmup
        'warmup_bias_lr': 0.1,      # Bias learning rate during warmup

        # ============ Loss Function Weights (OPTIMIZED FOR RECALL & TIGHT BOXES) ============
        'box': 10.0,                # Higher box loss = tighter bounding boxes (was 7.5)
        'cls': 0.3,                 # Lower class loss = prioritize detection over classification
        'dfl': 2.0,                 # Higher DFL = better localization precision (was 1.5)

        # ============ Multi-Scale Training ============
        'multiscale': .2,         # CRITICAL: Vary input size during training (±50% of imgsz)
                                    # Trains on multiple resolutions: 512px, 640px, 768px, 896px, 1024px
                                    # Forces model to learn scale-invariant features
        'scale': 0.2,               # Scale augmentation: 0.8x to 1.2x of image content
                                    # Different from multiscale - this scales the objects within image

        # ============ Heavy Augmentation Pipeline ============
        'hsv_h': 0.015,             # Hue augmentation (0-1 range)
        'hsv_s': 0.7,               # Saturation augmentation (0-1 range)
        'hsv_v': 0.4,               # Value (brightness) augmentation (0-1 range)

        'degrees': 0.0,             # Rotation disabled (birds have natural orientation)
        'translate': 0.1,           # Translation (10% of image size)
        'scale_aug': 0.9,           # Scale augmentation (0.5 = ±50%)
        'shear': 0.0,               # Shear disabled (preserve bird shape)
        'perspective': 0.0001,      # Minimal perspective transform
        'flipud': 0.0,              # No vertical flip (birds don't fly upside down)
        'fliplr': 0.5,              # 50% horizontal flip (birds face any direction)

        'blur': 0.01,               # Gaussian blur probability
        'noise': 0.02,              # Gaussian noise probability

        'mosaic': 1.0,              # Always use mosaic (critical for multi-scale)
        'mixup': 0.15,              # 15% mixup probability (helps with occlusion)
        'copy_paste': 0.3,          # 30% copy-paste probability (boosts small birds)

        # ============ Model Configuration ============
        'close_mosaic': 10,         # Disable mosaic last 10 epochs (fine-tune on real images)
        'amp': True,                # Automatic mixed precision (faster training)
        'fraction': 1.0,            # Use 100% of dataset

        # ============ Validation & Checkpointing ============
        'save': True,               # Save checkpoints
        'save_period': -1,          # Save every N epochs (-1 = only best/last)
        'cache': False,             # Cache images (set True if RAM allows)
        'rect': False,              # Rectangular training (disabled for multi-scale)
        'resume': False,            # Resume from last checkpoint
        'exist_ok': True,           # Overwrite existing project
        'pretrained': True,         # Use pretrained weights from swift.pt
        'optimizer': 'SGD',         # SGD optimizer (stable for YOLO)
        'verbose': True,            # Verbose output
        'seed': 42,                 # Random seed for reproducibility
        'deterministic': False,     # Deterministic mode (slower, more reproducible)
        'single_cls': True,         # Single class training (bird only)
        'plots': True,              # Generate training plots
        'overlap_mask': True,       # Masks can overlap (for segmentation tasks)
        'mask_ratio': 4,            # Mask downsample ratio
        'dropout': 0.0,             # Dropout (0.0 = disabled)
        'val': True,                # Validate during training
        'split': 'val',             # Validation split name
    }

    return training_config


def validate_dataset(data_yaml_path):
    """
    Validate that the dataset is properly configured.

    Checks:
    - data.yaml exists and is valid
    - Train/val directories exist
    - At least some images are present
    """
    data_yaml = Path(data_yaml_path)

    if not data_yaml.exists():
        raise FileNotFoundError(f"Dataset config not found: {data_yaml}")

    with open(data_yaml, 'r') as f:
        data_config = yaml.safe_load(f)

    print(f"📊 Dataset Configuration:")
    print(f"   Classes: {data_config['nc']} ({data_config['names']})")
    print(f"   Train: {data_config['train']}")
    print(f"   Val: {data_config['val']}")

    # Validate directories exist (relative to data.yaml location)
    base_path = data_yaml.parent
    train_path = base_path / data_config['train']
    val_path = base_path / data_config['val']

    if not train_path.exists():
        raise FileNotFoundError(f"Training directory not found: {train_path}")
    if not val_path.exists():
        raise FileNotFoundError(f"Validation directory not found: {val_path}")

    # Count images
    train_images = list(train_path.glob('*.jpg')) + list(train_path.glob('*.png'))
    val_images = list(val_path.glob('*.jpg')) + list(val_path.glob('*.png'))

    print(f"   Train images: {len(train_images)}")
    print(f"   Val images: {len(val_images)}")

    if len(train_images) == 0:
        raise ValueError("No training images found!")

    return data_config


def main():
    parser = argparse.ArgumentParser(
        description='Fine-tune swift.pt for improved recall and tighter bounding boxes'
    )
    parser.add_argument(
        '--model',
        type=str,
        default='swift.pt',
        help='Path to base model checkpoint (default: swift.pt)'
    )
    parser.add_argument(
        '--data',
        type=str,
        default='licksplit/data.yaml',
        help='Path to data.yaml (default: licksplit/data.yaml)'
    )
    parser.add_argument(
        '--project',
        type=str,
        default='runs/train',
        help='Project directory for outputs (default: runs/train)'
    )
    parser.add_argument(
        '--name',
        type=str,
        default='bird_detector',
        help='Experiment name (default: bird_detector)'
    )
    parser.add_argument(
        '--batch',
        type=int,
        default=16,
        help='Batch size (default: 16, reduce if OOM)'
    )
    parser.add_argument(
        '--epochs',
        type=int,
        default=100,
        help='Number of training epochs (default: 100 for 16K dataset)'
    )
    parser.add_argument(
        '--imgsz',
        type=int,
        default=1024,
        help='Input image size (default: 1024)'
    )

    args = parser.parse_args()

    print("=" * 80)
    print("🦅 YOLOv26n Bird Detection Fine-Tuning")
    print("=" * 80)

    # Resolve paths relative to script location
    script_dir = Path(__file__).parent
    model_path = script_dir / args.model
    data_path = script_dir / args.data

    if not model_path.exists():
        raise FileNotFoundError(f"Model checkpoint not found: {model_path}")

    print(f"\n✅ Found model checkpoint: {model_path}")

    # Validate dataset
    validate_dataset(data_path)

    # Check CUDA availability
    if torch.cuda.is_available():
        print(f"\n🚀 GPU Detected: {torch.cuda.get_device_name(0)}")
        print(f"   CUDA Version: {torch.version.cuda}")
        print(f"   GPU Memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.2f} GB")
    else:
        print("\n⚠️  No GPU detected - training will be slow on CPU")
        print("   Consider using Google Colab or a GPU instance")

    # Load model
    print(f"\n📦 Loading YOLOv26n from {model_path}...")
    model = YOLO(str(model_path))

    # Get training config
    config = setup_training_config()

    # Override with command-line arguments
    config['batch'] = args.batch
    config['epochs'] = args.epochs
    config['imgsz'] = args.imgsz
    config['project'] = args.project
    config['name'] = args.name

    print("\n🎯 Training Configuration:")
    print(f"   Epochs: {config['epochs']}")
    print(f"   Batch size: {config['batch']}")
    print(f"   Base image size: {config['imgsz']}px")
    print(f"   Multi-scale training: {'ENABLED' if config['multiscale'] else 'DISABLED'} (varies resolution)")
    print(f"   Scale augmentation: ±{int(config['scale']*100)}% (varies object size)")
    print(f"   Learning rate: {config['lr0']} → {config['lr0'] * config['lrf']}")
    print(f"   Warmup: {config['warmup_epochs']} epochs")
    print(f"\n⚖️  Loss Weights (Optimized for Recall + Tight Boxes):")
    print(f"   Box loss: {config['box']} (high = tighter boxes)")
    print(f"   Class loss: {config['cls']} (low = higher recall)")
    print(f"   DFL: {config['dfl']} (high = better localization)")
    print(f"\n🔄 Augmentation Pipeline:")
    print(f"   Mosaic: {config['mosaic']*100:.0f}%")
    print(f"   MixUp: {config['mixup']*100:.0f}%")
    print(f"   Copy-Paste: {config['copy_paste']*100:.0f}%")
    print(f"   HSV: H={config['hsv_h']}, S={config['hsv_s']}, V={config['hsv_v']}")
    print(f"   Flip LR: {config['fliplr']*100:.0f}%")
    print(f"   Translate: ±{config['translate']*100:.0f}%")
    print(f"   Blur: {config['blur']*100:.0f}%")
    print(f"   Noise: {config['noise']*100:.0f}%")

    print(f"\n💾 Outputs will be saved to: {args.project}/{args.name}/")
    print("\n" + "=" * 80)
    print("🚀 Starting Training...")
    print("=" * 80 + "\n")

    # Train the model
    results = model.train(
        data=str(data_path),
        **config
    )

    print("\n" + "=" * 80)
    print("✅ Training Complete!")
    print("=" * 80)
    print(f"\n📊 Results saved to: {args.project}/{args.name}/")
    print(f"🏆 Best model: {args.project}/{args.name}/weights/best.pt")
    print(f"📈 Last model: {args.project}/{args.name}/weights/last.pt")
    print(f"\n🔍 Validation Metrics:")
    print(f"   mAP50: {results.results_dict.get('metrics/mAP50(B)', 'N/A')}")
    print(f"   mAP50-95: {results.results_dict.get('metrics/mAP50-95(B)', 'N/A')}")
    print("\n💡 Next Steps:")
    print("   1. Review training plots in the output directory")
    print("   2. Validate model on test set: yolo val model=weights/best.pt data=licksplit/data.yaml")
    print("   3. Run inference: yolo predict model=weights/best.pt source=<image/folder>")
    print("   4. Export for deployment: yolo export model=weights/best.pt format=onnx imgsz=1024")


if __name__ == '__main__':
    main()
