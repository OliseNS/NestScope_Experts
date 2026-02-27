"""
Debug script to check ONNX model output format
This helps us understand what the model is actually outputting
"""

import onnxruntime as ort
import numpy as np
from pathlib import Path

def inspect_onnx_model(model_path: str):
    """
    Inspect ONNX model input/output shapes and format

    This is crucial because different YOLO versions output data in different formats:
    - YOLOv5: [1, 25200, 85] = [batch, anchors, (x,y,w,h,conf,classes...)]
    - YOLOv8: [1, 84, 8400] = [batch, (x,y,w,h,classes...), anchors]
    - YOLOv8 export formats vary: sometimes [1, num_detections, 6]
    """
    print(f"Inspecting model: {model_path}")
    print("=" * 60)

    # Load model
    session = ort.InferenceSession(model_path)

    # Get input details
    print("\n📥 INPUT DETAILS:")
    for inp in session.get_inputs():
        print(f"  Name: {inp.name}")
        print(f"  Shape: {inp.shape}")
        print(f"  Type: {inp.type}")

    # Get output details
    print("\n📤 OUTPUT DETAILS:")
    for out in session.get_outputs():
        print(f"  Name: {out.name}")
        print(f"  Shape: {out.shape}")
        print(f"  Type: {out.type}")

    # Test with dummy input
    print("\n🧪 TESTING WITH DUMMY INPUT:")
    input_name = session.get_inputs()[0].name
    input_shape = session.get_inputs()[0].shape

    # Create dummy input (batch, channels, height, width)
    dummy_input = np.random.rand(*input_shape).astype(np.float32)
    print(f"  Dummy input shape: {dummy_input.shape}")

    # Run inference
    outputs = session.run(None, {input_name: dummy_input})

    print(f"\n  Number of outputs: {len(outputs)}")
    for i, output in enumerate(outputs):
        print(f"  Output {i} shape: {output.shape}")
        print(f"  Output {i} dtype: {output.dtype}")

        # Analyze the output format
        if len(output.shape) == 3:
            batch, dim1, dim2 = output.shape
            print(f"    Format: [batch={batch}, dim1={dim1}, dim2={dim2}]")

            # Try to guess the format
            if dim2 == 6:
                print("    ✓ Likely format: [batch, num_detections, (x,y,w,h,conf,class)]")
                print("    This is YOLOv8 'max_det' format with 6 values per detection")
            elif dim2 > 84:
                print("    ✓ Likely format: [batch, num_detections, (4_coords + 1_conf + N_classes)]")
            elif dim1 > 80:
                print("    ✓ Likely format: [batch, (4_coords + N_classes), num_anchors]")
                print("    Needs transpose before processing")

            # Show sample values from first detection
            if output.shape[1] > 0:
                print(f"\n  Sample first detection (first 10 values):")
                first_det = output[0, 0, :]
                print(f"    {first_det[:min(10, len(first_det))]}")

if __name__ == "__main__":
    # Check both models for comparison
    models_dir = Path(__file__).parent / "models"

    nano_model = models_dir / "nano1024.onnx"
    old_model = models_dir / "seconditer.onnx"

    if nano_model.exists():
        print("\n" + "🔍 NANO1024 MODEL ".center(60, "="))
        inspect_onnx_model(str(nano_model))

    if old_model.exists():
        print("\n\n" + "🔍 SECONDITER MODEL (for comparison) ".center(60, "="))
        inspect_onnx_model(str(old_model))

    print("\n" + "=" * 60)
    print("\n💡 Next steps:")
    print("  1. Compare the output formats")
    print("  2. Adjust postprocessing code to match nano1024 format")
    print("  3. Check if class IDs need remapping")
