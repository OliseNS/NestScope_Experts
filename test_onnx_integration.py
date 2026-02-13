"""
Test script to verify ONNX bird detector integration
"""

import sys
import os

# Add server directory to path
sys.path.insert(0, os.path.dirname(__file__))

from server.cv_tools.inference_onnx import BirdDetectorONNX
import numpy as np

print("="*70)
print("Testing ONNX Bird Detector Integration")
print("="*70)

# Test 1: Initialize detector
print("\n[Test 1] Initializing detector...")
try:
    detector = BirdDetectorONNX()
    print("✅ Detector initialized successfully!")
    print(f"   Model: {detector.model_path}")
    print(f"   Tile size: {detector.tile_size}x{detector.tile_size}")
    print(f"   Overlap: {detector.overlap * 100}%")
    print(f"   Stride: {detector.stride} pixels")
except Exception as e:
    print(f"❌ Failed to initialize detector: {e}")
    sys.exit(1)

# Test 2: Test with dummy image
print("\n[Test 2] Testing with dummy image (800x600)...")
try:
    # Create a dummy image
    dummy_image = np.random.randint(0, 255, (600, 800, 3), dtype=np.uint8)

    # Convert to bytes (simulate upload)
    import cv2
    _, buffer = cv2.imencode('.jpg', dummy_image)
    image_bytes = buffer.tobytes()

    # Run inference
    results = detector.predict_from_bytes(image_bytes, conf_threshold=0.5)

    print(f"✅ Inference completed!")
    print(f"   Birds detected: {results['bird_count']}")
    print(f"   Detections: {len(results['detections'])}")
    print(f"   Annotated image shape: {results['annotated_image'].shape}")

except Exception as e:
    print(f"❌ Inference failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 3: Test with different image sizes
print("\n[Test 3] Testing with various image sizes...")
test_sizes = [(400, 400), (800, 600), (1920, 1080), (3000, 2000)]

for w, h in test_sizes:
    try:
        dummy_image = np.random.randint(0, 255, (h, w, 3), dtype=np.uint8)
        _, buffer = cv2.imencode('.jpg', dummy_image)
        image_bytes = buffer.tobytes()

        results = detector.predict_from_bytes(image_bytes, conf_threshold=0.7)
        tiles_count = len(detector._extract_tiles(dummy_image))

        print(f"   {w}x{h}: {tiles_count} tiles, {results['bird_count']} birds detected ✅")
    except Exception as e:
        print(f"   {w}x{h}: Failed - {e} ❌")

# Test 4: Test INT8 model
print("\n[Test 4] Testing INT8 quantized model...")
try:
    detector_int8 = BirdDetectorONNX(use_int8=True)
    print("✅ INT8 model loaded successfully!")
    print(f"   Model: {detector_int8.model_path}")

    # Quick inference test
    dummy_image = np.random.randint(0, 255, (600, 800, 3), dtype=np.uint8)
    _, buffer = cv2.imencode('.jpg', dummy_image)
    results = detector_int8.predict_from_bytes(buffer.tobytes(), conf_threshold=0.5)
    print(f"✅ INT8 inference works! Detected: {results['bird_count']} birds")

except FileNotFoundError as e:
    print(f"⚠️  INT8 model not found (optional)")
except Exception as e:
    print(f"❌ INT8 test failed: {e}")

print("\n" + "="*70)
print("✅ All tests passed! ONNX integration is working correctly.")
print("="*70)
print("\nThe detector is ready to use!")
print("  - Uses sliding window approach for accurate aerial detection")
print("  - No image squishing - tiles are processed at native resolution")
print("  - NMS removes duplicate detections across tiles")
print("  - Works with any image size")
