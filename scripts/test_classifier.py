"""
Test Species Classifier Integration

This script tests the newly converted ONNX classifiers to ensure they work correctly.
"""

import sys
import os
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

def test_classifier_loading():
    """Test 1: Can we load the classifiers?"""
    print("\n" + "="*60)
    print("TEST 1: Loading Classifiers")
    print("="*60)

    try:
        from server.cv_tools.inference import BirdDetector
        detector = BirdDetector()
        print("✓ BirdDetector initialized successfully")
        return detector
    except Exception as e:
        print(f"✗ Failed to load BirdDetector: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_species_mapping():
    """Test 2: Are species codes and names correct?"""
    print("\n" + "="*60)
    print("TEST 2: Species Mapping")
    print("="*60)

    try:
        from server.cv_tools.classifier_species import (
            CLASSIFIER_SPECIES,
            SPECIES_COMMON_NAMES,
            get_species_code,
            get_species_name,
            get_species_group,
            get_group_color
        )

        print(f"✓ Loaded {len(CLASSIFIER_SPECIES)} species codes")
        print(f"✓ Loaded {len(SPECIES_COMMON_NAMES)} common names")

        # Test a few species
        test_cases = [
            (4, 'BRPE', 'Brown Pelican', 'PELICAN'),
            (13, 'LAGU', 'Laughing Gull', 'GULL'),
            (18, 'ROYT', 'Royal Tern', 'TERN'),
        ]

        print("\nSample Species:")
        for class_id, expected_code, expected_name, expected_group in test_cases:
            code = get_species_code(class_id)
            name = get_species_name(code)
            group = get_species_group(code)
            color = get_group_color(group)

            assert code == expected_code, f"Code mismatch: {code} != {expected_code}"
            assert name == expected_name, f"Name mismatch: {name} != {expected_name}"
            assert group == expected_group, f"Group mismatch: {group} != {expected_group}"

            print(f"  {class_id}: {code} = {name} ({group}) - Color: {color}")

        print("\n✓ Species mapping is correct!")
        return True

    except Exception as e:
        print(f"✗ Species mapping test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_classification():
    """Test 3: Can we classify a test image?"""
    print("\n" + "="*60)
    print("TEST 3: Classification on Test Image")
    print("="*60)

    detector = test_classifier_loading()
    if detector is None:
        print("✗ Skipping classification test (detector not loaded)")
        return False

    # Find a test image
    test_image_dir = PROJECT_ROOT / "server" / "cv_tools" / "images"
    test_images = list(test_image_dir.glob("*.jpg")) + list(test_image_dir.glob("*.png"))

    if not test_images:
        print("⚠️  No test images found in server/cv_tools/images/")
        print("   Place a bird image there to test classification")
        return False

    test_image = str(test_images[0])
    print(f"Using test image: {Path(test_image).name}")

    try:
        import cv2
        image = cv2.imread(test_image)
        if image is None:
            print(f"✗ Failed to load image: {test_image}")
            return False

        print(f"✓ Image loaded: {image.shape[1]}×{image.shape[0]} pixels")

        # Test both Swift and Apex classifiers
        for mode_name, fast_mode in [("Swift", True), ("Apex", False)]:
            print(f"\nTesting {mode_name} Classifier:")

            # Classify the full image (as a test)
            result = detector.classify_crop(image, fast_mode=fast_mode, top_k=5)

            print(f"  Top Prediction:")
            print(f"    Species: {result['species_name']} ({result['species_code']})")
            print(f"    Confidence: {result['confidence']:.1%}")
            print(f"    Group: {result['group']}")

            print(f"  Top 5 Predictions:")
            for i, pred in enumerate(result['top_predictions'], 1):
                print(f"    {i}. {pred['species_name']} ({pred['species_code']}) - {pred['confidence']:.1%}")

        print("\n✓ Classification test passed!")
        return True

    except Exception as e:
        print(f"✗ Classification test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("\n🧪 Species Classifier Integration Tests")
    print("="*60)

    results = {
        "Classifier Loading": test_classifier_loading() is not None,
        "Species Mapping": test_species_mapping(),
        "Classification": test_classification(),
    }

    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)

    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {test_name}: {status}")

    all_passed = all(results.values())

    if all_passed:
        print("\n🎉 All tests passed!")
        print("\nNext steps:")
        print("  1. Start the application: ./run_app.sh")
        print("  2. Go to NestVision: http://localhost:8501")
        print("  3. Upload a bird image and run detection")
        print("  4. Check that species codes appear on bounding boxes")
    else:
        print("\n⚠️  Some tests failed. Check the errors above.")

    print("\n" + "="*60 + "\n")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
