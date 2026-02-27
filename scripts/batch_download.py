"""
Batch Download Script - Phase 3a

Downloads images from S3 and creates species metadata linkage.
Separating download from detection allows:
1. Download once, run detection multiple times
2. Balance detection across species for even coverage
3. Inspect images before detection
4. Resume detection without re-downloading

Output:
- downloaded_images/ - Full images organized by photo_id
- image_metadata.json - Links each image to species candidates
"""

import json
import boto3
from botocore import UNSIGNED
from botocore.config import Config
from pathlib import Path
from collections import defaultdict
import sys

# Optional import for progress bars
try:
    from tqdm import tqdm
except ImportError:
    def tqdm(iterable, desc=""):
        return iterable
    print("⚠️ tqdm not installed - progress bars disabled")

# Configuration
PROJECT_ROOT = Path(__file__).parent.parent
MAPPINGS_FILE = PROJECT_ROOT / "data" / "weak_supervision" / "photo_mappings_2015_2021.json"
DOWNLOAD_DIR = PROJECT_ROOT / "data" / "weak_supervision" / "downloaded_images"
IMAGE_METADATA_FILE = PROJECT_ROOT / "data" / "weak_supervision" / "image_metadata.json"

BUCKET_NAME = "twi-aviandata"


def get_s3_client():
    """Create S3 client with unsigned access (public bucket)"""
    return boto3.client('s3', config=Config(signature_version=UNSIGNED))


def load_photo_mappings(mappings_file: Path):
    """Load photo mappings from Phase 2"""
    with open(mappings_file, 'r') as f:
        mappings = json.load(f)
    print(f"✓ Loaded {len(mappings):,} photo mappings")
    return mappings


def download_image_from_s3(s3_client, s3_key: str, output_path: Path) -> bool:
    """
    Download single image from S3.

    Returns:
        True if successful, False otherwise
    """
    try:
        s3_client.download_file(BUCKET_NAME, s3_key, str(output_path))
        return True
    except Exception as e:
        print(f"  ⚠️ Failed to download {s3_key}: {e}")
        return False


def download_all_images(s3_client, mappings: list) -> dict:
    """
    Download all images and create metadata mapping.

    Returns:
        dict: {photo_id: metadata} for all successfully downloaded images
    """
    image_metadata = {}
    successful_downloads = 0
    failed_downloads = 0

    print(f"\n📥 Downloading {len(mappings):,} images from S3...")
    print(f"   Saving to: {DOWNLOAD_DIR}/")

    for mapping in tqdm(mappings, desc="Downloading"):
        photo_id = mapping['photo_id']
        s3_key = mapping['s3_key']

        # Determine file extension from S3 key
        extension = Path(s3_key).suffix  # e.g., ".JPG" or ".jpg"
        output_path = DOWNLOAD_DIR / f"{photo_id}{extension}"

        # Download
        if download_image_from_s3(s3_client, s3_key, output_path):
            # Store metadata for this image
            image_metadata[photo_id] = {
                'photo_id': photo_id,
                'image_path': str(output_path.relative_to(PROJECT_ROOT)),
                's3_path': mapping['s3_path'],
                's3_key': s3_key,
                'species_codes': mapping['species_codes'],
                'species_count': len(mapping['species_codes']),
                'is_single_species': len(mapping['species_codes']) == 1,
                'metadata': mapping['metadata']
            }
            successful_downloads += 1
        else:
            failed_downloads += 1

        # Progress report every 500 images
        if (successful_downloads + failed_downloads) % 500 == 0:
            print(f"   Progress: {successful_downloads:,} downloaded, {failed_downloads} failed")

    return image_metadata


def analyze_species_distribution(image_metadata: dict):
    """
    Analyze species distribution in downloaded images.

    Returns statistics about species coverage and balance.
    """
    total_images = len(image_metadata)
    single_species = sum(1 for m in image_metadata.values() if m['is_single_species'])
    multi_species = total_images - single_species

    # Count images per species
    species_image_count = defaultdict(int)
    for metadata in image_metadata.values():
        for species in metadata['species_codes']:
            species_image_count[species] += 1

    # Sort by count
    species_sorted = sorted(species_image_count.items(), key=lambda x: x[1], reverse=True)

    return {
        'total_images': total_images,
        'single_species_images': single_species,
        'multi_species_images': multi_species,
        'unique_species': len(species_image_count),
        'species_distribution': dict(species_sorted),
        'species_sorted': species_sorted
    }


def main():
    """Main download workflow"""
    print("=" * 70)
    print("📥 BATCH DOWNLOAD - PHASE 3a")
    print("=" * 70)
    print(f"Source mappings: {MAPPINGS_FILE}")
    print(f"S3 Bucket: {BUCKET_NAME}")
    print(f"Output directory: {DOWNLOAD_DIR}/")

    # Setup
    DOWNLOAD_DIR.mkdir(exist_ok=True, parents=True)

    # Step 1: Load mappings
    print(f"\n[1/3] Loading photo mappings...")
    mappings = load_photo_mappings(MAPPINGS_FILE)

    # Step 2: Initialize S3 client
    print(f"\n[2/3] Initializing S3 client...")
    s3_client = get_s3_client()
    print(f"✓ S3 client ready")

    # Step 3: Download all images
    print(f"\n[3/3] Downloading images...")
    image_metadata = download_all_images(s3_client, mappings)

    # Save metadata
    print(f"\n💾 Saving image metadata...")
    with open(IMAGE_METADATA_FILE, 'w') as f:
        json.dump(image_metadata, f, indent=2)
    print(f"✓ Saved to: {IMAGE_METADATA_FILE}")

    # Analyze and report
    print(f"\n" + "=" * 70)
    print("📊 DOWNLOAD COMPLETE")
    print("=" * 70)

    stats = analyze_species_distribution(image_metadata)

    print(f"Total images downloaded:    {stats['total_images']:,}")
    print(f"  Single-species images:    {stats['single_species_images']:,} ({stats['single_species_images']/stats['total_images']*100:.1f}%)")
    print(f"  Multi-species images:     {stats['multi_species_images']:,} ({stats['multi_species_images']/stats['total_images']*100:.1f}%)")
    print()
    print(f"Unique species represented: {stats['unique_species']}")
    print()
    print(f"Top 10 species (by image count):")
    for i, (species, count) in enumerate(stats['species_sorted'][:10], 1):
        pct = count / stats['total_images'] * 100
        print(f"  {i:2}. {species}: {count:,} images ({pct:.1f}%)")
    print()
    print(f"💾 Image metadata: {IMAGE_METADATA_FILE}")
    print(f"📁 Downloaded images: {DOWNLOAD_DIR}/")
    print()
    print("=" * 70)
    print("✅ NEXT STEP: Run batch_detect.py to extract bird crops")
    print("=" * 70)
    print()


if __name__ == "__main__":
    main()
