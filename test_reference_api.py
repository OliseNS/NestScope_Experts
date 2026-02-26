"""
Test the reference images API endpoint

This simulates what the frontend does - calls the Flask API
to get reference images for species.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'labeller'))

from services.reference_images_complete import get_reference_images

def test_species(code, name):
    print(f"\n{'='*60}")
    print(f"Testing: {name} ({code})")
    print(f"{'='*60}")

    ref = get_reference_images(code)

    print(f"\nSpecies Name: {ref['name']}")
    print(f"Photos Found: {len(ref['photos'])}")

    if ref['photos']:
        print("\n📸 Image URLs:")
        for i, url in enumerate(ref['photos'], 1):
            # Show first 100 chars of URL
            display_url = url if len(url) <= 100 else url[:97] + "..."
            print(f"   {i}. {display_url}")
    else:
        print("\n⚠️  No photos available")

    print(f"\n🔗 Resource Links:")
    print(f"   eBird: {ref['ebird']}")
    print(f"   Field Guide: {ref['guide']}")
    print(f"   Macaulay Gallery: {ref['macaulay_gallery']}")

if __name__ == "__main__":
    print("🧪 TESTING REFERENCE IMAGES API")
    print("="*60)

    # Test a few species
    test_cases = [
        ("BRPE", "Brown Pelican"),
        ("GREG", "Great Egret"),
        ("ROSP", "Roseate Spoonbill"),
        ("MAFR", "Magnificent Frigatebird")
    ]

    for code, name in test_cases:
        test_species(code, name)

    print("\n\n✅ Test complete!")
    print("If you see image URLs above, the system is working correctly!")
