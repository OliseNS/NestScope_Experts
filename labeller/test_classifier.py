#!/usr/bin/env python3
"""
Test script for the ONNX classifier.

Usage:
    python labeller/test_classifier.py
"""

import os
import sys
import cv2
import numpy as np

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from labeller.onnx_classifier import ONNXClassifier, BirdDetector


def test_classifier():
    """Test the classifier with a dummy image."""
    print("=" * 60)
    print("Testing ONNX Classifier")
    print("=" * 60)

    # Initialize classifier
    print("\n1. Loading classifier...")
    try:
        classifier = ONNXClassifier()
        print("   ✓ Classifier loaded")
    except Exception as e:
        print(f"   ✗ Failed to load classifier: {e}")
        return False

    # Create a dummy bird crop (224x224 random image)
    print("\n2. Creating dummy bird crop...")
    dummy_crop = np.random.randint(0, 255, (224, 224, 3), dtype=np.uint8)
    print(f"   ✓ Created {dummy_crop.shape} image")

    # Test classification
    print("\n3. Running classification...")
    try:
        result = classifier.classify_crop(dummy_crop, top_k=3)
        print("   ✓ Classification successful")

        print("\n   Top 3 predictions:")
        for i, pred in enumerate(result['top_predictions'], 1):
            print(f"      {i}. {pred['full_name']} ({pred['code']}): {pred['confidence']*100:5.2f}%")

        print("\n   All scores:")
        for code, score in sorted(result['all_scores'].items(), key=lambda x: x[1], reverse=True):
            print(f"      {code:15} {score*100:5.2f}%")

    except Exception as e:
        print(f"   ✗ Classification failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Test BirdDetector compatibility wrapper
    print("\n4. Testing BirdDetector wrapper...")
    try:
        detector = BirdDetector()
        result2 = detector.classify_crop(dummy_crop, top_k=3)
        print("   ✓ BirdDetector wrapper works")
        print(f"      Top prediction: {result2['top_predictions'][0]['full_name']}")
    except Exception as e:
        print(f"   ✗ BirdDetector failed: {e}")
        return False

    print("\n" + "=" * 60)
    print("All tests passed! ✓")
    print("=" * 60)
    return True


if __name__ == '__main__':
    success = test_classifier()
    sys.exit(0 if success else 1)
