"""
Convert MobileSAM to ONNX format

This script converts the MobileSAM PyTorch model to ONNX format
for faster inference without PyTorch dependency.
"""

import torch
import os
from pathlib import Path

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import sys
sys.path.insert(0, PROJECT_ROOT)

def convert_mobile_sam_to_onnx():
    """Convert MobileSAM to ONNX format"""
    from ultralytics import SAM

    model_path = os.path.join(PROJECT_ROOT, 'models', 'mobile_sam.pt')
    output_path = os.path.join(PROJECT_ROOT, 'models', 'mobile_sam_encoder.onnx')

    if not os.path.exists(model_path):
        print(f"❌ MobileSAM not found at {model_path}")
        return False

    print(f"Loading MobileSAM from {model_path}...")
    model = SAM(model_path)

    # Export to ONNX
    print("Converting to ONNX...")
    try:
        # Export the SAM model
        success = model.export(format='onnx', dynamic=False, simplify=True)

        if success:
            print(f"✓ MobileSAM converted to ONNX")
            # The exported file will be in the same directory as the .pt file
            exported_path = model_path.replace('.pt', '.onnx')
            if os.path.exists(exported_path):
                print(f"✓ Exported to: {exported_path}")
                return True
        else:
            print("❌ Export failed")
            return False

    except Exception as e:
        print(f"❌ Error during conversion: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    print("=" * 60)
    print("MobileSAM to ONNX Converter")
    print("=" * 60)
    convert_mobile_sam_to_onnx()
