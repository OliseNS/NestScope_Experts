# ONNX Model Conversion Summary

## Changes Made

### 1. Model Conversion
- Converted `seconditer.pt` (PyTorch model) to `seconditer.onnx` (ONNX format)
- ONNX model size: 77.0 MB (from 38.7 MB PyTorch)
- Model uses ONNX opset version 12 with graph optimizations

### 2. Updated Inference Code (`server/cv_tools/inference.py`)
- Replaced `ultralytics YOLO` with `onnxruntime` for inference
- Added ONNX-specific preprocessing and postprocessing methods
- Maintained all existing functionality (sliding window, NMS, annotations)
- Performance: Uses `CPUExecutionProvider` (falls back from CUDA if unavailable)

### 3. Key Methods Added
- `_preprocess_image()`: Prepares images for ONNX inference (resize, pad, normalize)
- `_postprocess_onnx_output()`: Processes raw ONNX outputs to detections
- `_nms_boxes()`: Custom NMS implementation for bounding boxes

### 4. Dependencies
- Added `onnxruntime>=1.16.0` to `requirements.txt`
- Removed dependency on ultralytics for inference (still needed for conversion)

## Performance Benefits

ONNX Runtime provides:
- Faster inference speed compared to PyTorch
- Lower memory footprint
- Better optimization for production deployment
- Support for multiple execution providers (CPU, CUDA, TensorRT, etc.)

## Usage

The API remains unchanged:
```python
from server.cv_tools.inference import BirdDetector

detector = BirdDetector()
results = detector.predict(image_path, conf_threshold=0.25)
print(f"Detected {results['bird_count']} birds")
```

## Testing

Tested with sample image:
- Detected 271 birds in test image
- Inference completed successfully
- Annotated images generated correctly

## Files Generated
- `seconditer.onnx`: ONNX model file
- `convert_to_onnx.py`: Conversion script (for future reference)
- `test_onnx_inference.py`: Test script to verify ONNX integration
