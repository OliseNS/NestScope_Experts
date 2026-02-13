"""
Test ONNX inference implementation
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'server'))

from cv_tools.inference import BirdDetector
import time

def test_onnx_inference():
    """Test the ONNX-based bird detector"""
    print("Initializing ONNX-based BirdDetector...")
    detector = BirdDetector()

    print("\nTesting with a sample image (if available)...")

    # Try to find a test image
    test_images = [
        "server/cv_tools/images/15May2022_Cam1Card1_1027.jpg",
        "server/cv_tools/images/test.jpg",
        "server/cv_tools/images/test.png",
    ]

    test_image = None
    for img_path in test_images:
        if os.path.exists(img_path):
            test_image = img_path
            break

    if test_image:
        print(f"Found test image: {test_image}")

        # Test inference speed
        start_time = time.time()
        results = detector.predict(test_image, conf_threshold=0.25, use_sliding_window=True)
        inference_time = time.time() - start_time

        print(f"\n✓ Inference completed in {inference_time:.3f} seconds")
        print(f"✓ Detected {results['bird_count']} birds")
        print(f"✓ Detections: {len(results['detections'])} objects")

        # Save annotated image
        output_path = "test_output_onnx.jpg"
        detector.save_annotated_image(results['annotated_image'], output_path)
        print(f"✓ Saved annotated image to {output_path}")
    else:
        print("No test images found. Skipping image inference test.")
        print("✓ Model loaded successfully!")

if __name__ == "__main__":
    test_onnx_inference()
