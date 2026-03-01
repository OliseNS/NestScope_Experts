"""
NestScope Bird Species Classifier Training

Two models (matching detection naming convention):
  Swift  — YOLOv8n-cls (3.5MB, fast inference)
  Apex   — YOLOv8s-cls (12MB, better accuracy)

Usage on RunPod:
  1. Upload classify_dataset.zip to the pod
  2. unzip classify_dataset.zip -d dataset
  3. pip install ultralytics
  4. python train_classifier.py --data dataset --mode apex
  5. python train_classifier.py --data dataset --mode swift

Expected time: ~30-40 min per model on a single GPU
"""

import argparse
import os
import shutil
from pathlib import Path

# Model configs: name → (base weights, output name)
MODELS = {
    'swift': ('yolov8n-cls.pt', 'classifier_swift'),
    'apex':  ('yolov8s-cls.pt', 'classifier_apex'),
}


def main():
    parser = argparse.ArgumentParser(description='Train NestScope bird species classifier')
    parser.add_argument('--data', type=str, required=True,
                        help='Path to dataset directory (contains train/ and val/)')
    parser.add_argument('--mode', type=str, default='apex', choices=['swift', 'apex', 'both'],
                        help='Model to train: swift (fast), apex (accurate), or both')
    parser.add_argument('--epochs', type=int, default=50)
    parser.add_argument('--imgsz', type=int, default=224)
    parser.add_argument('--batch', type=int, default=128)
    parser.add_argument('--patience', type=int, default=10,
                        help='Early stopping patience (0 to disable)')
    args = parser.parse_args()

    data_dir = Path(args.data)
    if not (data_dir / 'train').exists():
        print(f"ERROR: {data_dir / 'train'} not found")
        return

    train_count = sum(len(f) for _, _, f in os.walk(data_dir / 'train'))
    val_count = sum(len(f) for _, _, f in os.walk(data_dir / 'val'))
    species = sorted(os.listdir(data_dir / 'train'))
    print(f"Train: {train_count} images | Val: {val_count} images | Species: {len(species)}")

    modes = ['swift', 'apex'] if args.mode == 'both' else [args.mode]

    for mode in modes:
        base_weights, output_name = MODELS[mode]
        print(f"\n{'=' * 60}")
        print(f"Training {mode.upper()} classifier ({base_weights})")
        print(f"{'=' * 60}")

        from ultralytics import YOLO
        model = YOLO(base_weights)

        model.train(
            data=str(data_dir),
            epochs=args.epochs,
            imgsz=args.imgsz,
            batch=args.batch,
            patience=args.patience,
            project='runs',
            name=output_name,
            verbose=True
        )

        # Validate
        metrics = model.val()
        print(f"\n{mode.upper()} Results:")
        print(f"  Top-1 Accuracy: {metrics.top1:.1%}")
        print(f"  Top-5 Accuracy: {metrics.top5:.1%}")

        # Copy best model
        best = Path(f'runs/{output_name}/weights/best.pt')
        if best.exists():
            out = Path(f'{output_name}.pt')
            shutil.copy2(best, out)
            print(f"  Model saved to: {out} ({out.stat().st_size / 1024 / 1024:.1f} MB)")


if __name__ == '__main__':
    main()
