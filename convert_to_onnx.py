"""
Convert YOLOv model to ONNX format for faster inference
"""
from ultralytics import YOLO
import os

def convert_model_to_onnx(model_path="seconditer.pt", output_path="seconditer.onnx", imgsz=1024):
    """
    Convert YOLO model to ONNX format

    Args:
        model_path: Path to the .pt model file
        output_path: Path for the output .onnx file
        imgsz: Image size for inference (default: 1024)
    """
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model not found at {model_path}")

    print(f"Loading model from {model_path}...")
    model = YOLO(model_path)

    print(f"Exporting to ONNX format...")
    model.export(
        format="onnx",
        imgsz=imgsz,
        simplify=True,  # Simplify the ONNX model
        dynamic=False,   # Fixed input size for better optimization
        opset=12         # ONNX opset version
    )

    # The export function automatically names the file
    expected_output = model_path.replace('.pt', '.onnx')

    if os.path.exists(expected_output):
        print(f"✓ Model successfully converted to {expected_output}")
        print(f"Original size: {os.path.getsize(model_path) / (1024*1024):.2f} MB")
        print(f"ONNX size: {os.path.getsize(expected_output) / (1024*1024):.2f} MB")
    else:
        print(f"Warning: Expected output file not found at {expected_output}")

if __name__ == "__main__":
    convert_model_to_onnx()
