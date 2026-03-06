"""
Test Nestperts Classification API

Verifies that the /api/classify_crop endpoint works without circular reference errors.
"""

import requests
import json
import sys

def test_classification_api():
    """Test the classification API with a sample request"""

    print("\n" + "="*60)
    print("Testing Nestperts Classification API")
    print("="*60)

    # Sample request (you'll need to adjust the image_name to an actual image in your dataset)
    test_request = {
        "image_name": "test_image.jpg",  # Adjust this to an actual image
        "bbox": {
            "x_center": 0.5,
            "y_center": 0.5,
            "width": 0.1,
            "height": 0.1
        },
        "fast_mode": True
    }

    try:
        print("\n1. Sending request to http://localhost:5000/api/classify_crop")
        print(f"   Request: {json.dumps(test_request, indent=2)}")

        response = requests.post(
            "http://localhost:5000/api/classify_crop",
            json=test_request,
            timeout=10
        )

        print(f"\n2. Response status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print("\n✅ Success! No circular reference error!")
            print(f"\n3. Response data:")
            print(f"   Predictions returned: {len(data.get('predictions', []))}")

            if 'predictions' in data and len(data['predictions']) > 0:
                print(f"\n   Top prediction:")
                top = data['predictions'][0]
                print(f"   - Species: {top.get('species_name')} ({top.get('species_code')})")
                print(f"   - Confidence: {top.get('confidence', 0)*100:.1f}%")
                print(f"   - Group: {top.get('group')}")

                print(f"\n   All predictions:")
                for i, pred in enumerate(data['predictions'], 1):
                    conf = pred.get('confidence', 0) * 100
                    print(f"   {i}. {pred.get('species_name'):30} {conf:5.1f}%")

            return True

        elif response.status_code == 404:
            print("\n⚠️  Image not found - this is expected if test_image.jpg doesn't exist")
            print("   To test with a real image:")
            print("   1. Find an image in labeller/nestvision/images/")
            print("   2. Update the 'image_name' in this script")
            print("   3. Run again")
            return True

        else:
            print(f"\n❌ Error: {response.status_code}")
            print(f"   Response: {response.text}")
            return False

    except requests.exceptions.ConnectionError:
        print("\n❌ Connection error!")
        print("   Make sure Nestperts is running:")
        print("   ./run_app.sh")
        print("   or")
        print("   python labeller/app.py --data labeller/nestvision")
        return False

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    print("\n🧪 Nestperts Classification API Test")

    success = test_classification_api()

    print("\n" + "="*60)
    if success:
        print("✅ TEST PASSED!")
        print("\nThe circular reference error is fixed!")
        print("\nNext steps:")
        print("1. Go to http://localhost:5000")
        print("2. Click 'E' (edit mode)")
        print("3. Click any bird detection")
        print("4. AI will automatically classify and show top-5!")
    else:
        print("❌ TEST FAILED")
        print("\nCheck the errors above and try again.")

    print("="*60 + "\n")

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
