"""
Convert YOLOv8 Classification Models from PyTorch (.pt) to ONNX

This script converts the bird species classifier models from PyTorch format
to ONNX format for faster inference and cross-platform compatibility.

ONNX Benefits:
- Faster inference (optimized runtime)
- Platform independent (works without PyTorch)
- Smaller memory footprint
- Better integration with production systems

Usage:
    python scripts/convert_classifier_to_onnx.py
"""

import torch
from pathlib import Path
from ultralytics import YOLO
import onnx


def convert_classifier(pt_path: str, onnx_path: str, imgsz: int = 224):
    """
    Convert a YOLOv8 classifier from .pt to .onnx format

    Args:
        pt_path: Path to input .pt model
        onnx_path: Path to output .onnx model
        imgsz: Input image size (YOLOv8-cls uses 224x224)

    Why 224x224?
    - Standard size for image classification models
    - Pre-trained ImageNet models use this size
    - Good balance between accuracy and speed
    """
    print(f"\n{'='*60}")
    print(f"Converting: {Path(pt_path).name}")
    print(f"{'='*60}")

    # Check if input file exists
    if not Path(pt_path).exists():
        print(f"❌ Error: {pt_path} not found!")
        return False

    try:
        # Load the YOLOv8 classifier
        print(f"📦 Loading PyTorch model...")
        model = YOLO(pt_path)

        # Get model info
        print(f"✓ Model loaded successfully")
        print(f"   Architecture: {model.model.__class__.__name__}")

        # Export to ONNX
        # The export() method handles all the conversion details:
        # 1. Traces the model with dummy input
        # 2. Converts PyTorch ops to ONNX ops
        # 3. Optimizes the graph
        # 4. Saves the .onnx file
        print(f"\n🔄 Exporting to ONNX...")
        print(f"   Input size: {imgsz}x{imgsz}")
        print(f"   Format: ONNX")

        success = model.export(
            format='onnx',
            imgsz=imgsz,
            simplify=True,  # Simplify the ONNX model graph
            opset=12,       # ONNX opset version (12 is widely supported)
        )

        # The export creates the file automatically with .onnx extension
        # We need to rename it to match our desired output path
        auto_generated_path = str(Path(pt_path).with_suffix('.onnx'))

        if Path(auto_generated_path).exists():
            # Move to desired location
            import shutil
            shutil.move(auto_generated_path, onnx_path)
            print(f"✓ Model exported successfully!")
            print(f"   Output: {onnx_path}")

            # Verify the ONNX model
            print(f"\n🔍 Verifying ONNX model...")
            onnx_model = onnx.load(onnx_path)
            onnx.checker.check_model(onnx_model)
            print(f"✓ ONNX model is valid!")

            # Show file sizes
            pt_size = Path(pt_path).stat().st_size / (1024 * 1024)
            onnx_size = Path(onnx_path).stat().st_size / (1024 * 1024)
            print(f"\n📊 File Size Comparison:")
            print(f"   PyTorch (.pt):  {pt_size:.2f} MB")
            print(f"   ONNX (.onnx):   {onnx_size:.2f} MB")
            print(f"   Difference:     {((onnx_size/pt_size - 1) * 100):+.1f}%")

            return True
        else:
            print(f"❌ Export failed - output file not created")
            return False

    except Exception as e:
        print(f"❌ Error during conversion: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """
    Main conversion workflow

    Converts both Swift (fast) and Apex (accurate) classifiers
    """
    print("\n" + "="*60)
    print("🔧 Bird Species Classifier Conversion Tool")
    print("   PyTorch → ONNX")
    print("="*60)

    # Define paths
    project_root = Path(__file__).parent.parent
    models_dir = project_root / "models"

    # Input: User's PyTorch models
    pt_models = {
        'swift': models_dir / "cls_swift.pt",
        'apex': models_dir / "cls_apex.pt"
    }

    # Output: ONNX models (matching what inference.py expects)
    onnx_models = {
        'swift': models_dir / "classifier_swift.onnx",
        'apex': models_dir / "classifier_apex.onnx"
    }

    # Classifier input size (standard for image classification)
    CLASSIFIER_INPUT_SIZE = 224

    results = {}

    # Convert Swift classifier (fast model)
    print("\n\n🚀 SWIFT CLASSIFIER (Fast Inference)")
    results['swift'] = convert_classifier(
        str(pt_models['swift']),
        str(onnx_models['swift']),
        imgsz=CLASSIFIER_INPUT_SIZE
    )

    # Convert Apex classifier (accurate model)
    print("\n\n🎯 APEX CLASSIFIER (High Accuracy)")
    results['apex'] = convert_classifier(
        str(pt_models['apex']),
        str(onnx_models['apex']),
        imgsz=CLASSIFIER_INPUT_SIZE
    )

    # Summary
    print("\n\n" + "="*60)
    print("📋 CONVERSION SUMMARY")
    print("="*60)

    for model_name, success in results.items():
        status = "✓ Success" if success else "❌ Failed"
        print(f"   {model_name.title()}: {status}")

    if all(results.values()):
        print("\n🎉 All models converted successfully!")
        print("\n📝 Next Steps:")
        print("   1. The ONNX models are ready to use")
        print("   2. Run NestVision to test bird detection + classification")
        print("   3. Try different images to see species predictions")
        print("\n💡 The system will automatically:")
        print("   - Detect birds in images")
        print("   - Crop each detection")
        print("   - Classify into 7 functional groups")
        print("   - Color-code bounding boxes by species group")
    else:
        print("\n⚠️ Some conversions failed. Check errors above.")

    print("\n" + "="*60 + "\n")


if __name__ == "__main__":
    main()
