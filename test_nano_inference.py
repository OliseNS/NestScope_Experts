"""
Test script to verify nano1024 model detections
"""

import sys
sys.path.insert(0, '.')

from server.cv_tools.inference import BirdDetector
import cv2

# Initialize detector
print("Initializing BirdDetector...")
detector = BirdDetector()
print(f"✓ Loaded model: {detector.model_path}")
print(f"✓ Output format: {detector.output_format}")

# Test with an example image
image_path = "server/cv_tools/images/15May2022_Cam1Card1_1027.jpg"
print(f"\nRunning inference on: {image_path}")

# Run prediction
results = detector.predict(image_path, conf_threshold=0.25, fast_mode=True)

print(f"\n📊 RESULTS:")
print(f"  Birds detected: {results['bird_count']}")
print(f"  Inference time: {results['inference_time']:.3f}s")

if results['bird_count'] > 0:
    print(f"\n🐦 Detections (first 10):")
    for i, det in enumerate(results['detections'][:10], 1):
        x1, y1, x2, y2 = det['bbox']
        conf = det['confidence']
        class_id = det['class_id']
        print(f"  {i}. bbox=[{x1:.1f}, {y1:.1f}, {x2:.1f}, {y2:.1f}] conf={conf:.3f} class={class_id}")

    # Save annotated image
    output_path = "test_nano_output.jpg"
    cv2.imwrite(output_path, results['annotated_image'])
    print(f"\n✓ Saved annotated image to: {output_path}")
else:
    print("\n⚠️  No birds detected. Try lowering confidence threshold.")
