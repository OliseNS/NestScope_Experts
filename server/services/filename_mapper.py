"""
Filename Mapper Service

Builds complete mapping of database records to S3 photos for weak supervision pipeline.
Queries all 23,747 species records and maps to ~6,700 available S3 photos.

Output: data/photo_mappings_2015_2021.json with photo metadata and species labels
"""

import sqlite3
import boto3
from botocore import UNSIGNED
from botocore.config import Config
from pathlib import Path
import json
from collections import defaultdict
from typing import Dict, List, Optional
from datetime import datetime

# Configuration
PROJECT_ROOT = Path(__file__).parent.parent.parent
DB_PATH = PROJECT_ROOT / "data" / "bird_data_complete.db"
BUCKET_NAME = "twi-aviandata"
OUTPUT_FILE = PROJECT_ROOT / "data" / "photo_mappings_2015_2021.json"
STATS_FILE = PROJECT_ROOT / "data" / "photo_mapping_stats.json"

# Month name mapping
MONTH_NAMES = {
    1: "January", 2: "February", 3: "March", 4: "April",
    5: "May", 6: "June", 7: "July", 8: "August",
    9: "September", 10: "October", 11: "November", 12: "December"
}


def get_s3_client():
    """Create S3 client with unsigned access (public bucket)"""
    return boto3.client('s3', config=Config(signature_version=UNSIGNED))


def list_s3_files_for_year(s3_client, year: int) -> Dict[str, str]:
    """
    List all files in S3 for a given year and build a lookup dict.

    Returns:
        Dict mapping lowercase filename → full S3 key
    """
    print(f"  📂 Listing S3 files for year {year}...")
    prefix = f"HighResolutionImages/{year}/"

    paginator = s3_client.get_paginator('list_objects_v2')
    pages = paginator.paginate(Bucket=BUCKET_NAME, Prefix=prefix)

    file_lookup = {}
    count = 0

    for page in pages:
        if 'Contents' not in page:
            continue
        for obj in page['Contents']:
            key = obj['Key']
            # Extract just the filename (everything after last '/')
            filename = key.split('/')[-1].lower()
            file_lookup[filename] = key
            count += 1

    print(f"  ✓ Found {count:,} files in {prefix}")
    return file_lookup


def parse_date(date_str: str) -> Optional[tuple]:
    """
    Parse database date field into (day, month, year).

    Examples:
        "05/16/15 12:34:56" → (16, 5, 2015)
        "6/25/10" → (25, 6, 2010)
    """
    try:
        if ' ' in date_str:
            date_part = date_str.split(' ')[0]
        else:
            date_part = date_str

        parts = date_part.split('/')
        if len(parts) != 3:
            return None

        month, day, year = map(int, parts)

        # Convert 2-digit year to 4-digit
        if year < 100:
            year += 2000

        return (day, month, year)
    except:
        return None


def reconstruct_filename(date_str: str, camera, card, photo_num: str, year) -> List[str]:
    """
    Reconstruct possible filename variations using year-specific patterns.

    Returns list of candidate filenames to try.
    """
    date_info = parse_date(date_str)
    if not date_info:
        return []

    day, month, _ = date_info

    # Convert to proper types (database stores everything as TEXT)
    try:
        year = int(year)
        camera = int(camera)
        card = int(card)
    except:
        return []

    # Strip leading zeros from photo number
    try:
        photo_num_stripped = str(int(photo_num))
    except:
        photo_num_stripped = photo_num

    # Month name (full only)
    month_name = MONTH_NAMES[month]

    variations = []

    # **2015 Format:** "20June2015Cam1Card1 001.JPG"
    if year == 2015:
        for photo_str in [photo_num, photo_num_stripped]:
            photo_padded = photo_str.zfill(3)
            for photo_variant in [photo_str, photo_padded]:
                filename = f"{day}{month_name}{year}Cam{camera}Card{card} {photo_variant}.JPG"
                variations.append(filename)

    # **2018 Format:** "19May2018 Camera1-1.jpg" (no card!)
    elif year == 2018:
        for photo_str in [photo_num, photo_num_stripped]:
            filename = f"{day}{month_name}{year} Camera{camera}-{photo_str}.jpg"
            variations.append(filename)

    # **2021 Format:** "14June2021Camera1Card1-1.jpg"
    elif year == 2021:
        for photo_str in [photo_num, photo_num_stripped]:
            filename = f"{day}{month_name}{year}Camera{camera}Card{card}-{photo_str}.jpg"
            variations.append(filename)

    return variations


def verify_filename_in_s3(filename_variations: List[str], s3_lookup: Dict[str, str]) -> Optional[str]:
    """Check if any filename variation exists in S3"""
    for filename in filename_variations:
        if filename.lower() in s3_lookup:
            return s3_lookup[filename.lower()]
    return None


def query_all_species_records(db_path: Path) -> List[Dict]:
    """
    Query all species records from database.

    Returns list of records with:
        AutoID, Year, Date, CameraNumber, CardNumber, PhotoNumber,
        SpeciesCode, ColonyName
    """
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    query = '''
        SELECT
            AutoID,
            Year,
            Date,
            CameraNumber,
            CardNumber,
            PhotoNumber,
            SpeciesCode,
            ColonyName
        FROM "tblSpeciesData2015_2018_2021"
        WHERE Year IN ('2015', '2018', '2021')
        ORDER BY Year, Date, CameraNumber, CardNumber, PhotoNumber
    '''

    cursor.execute(query)
    records = [dict(row) for row in cursor.fetchall()]
    conn.close()

    return records


def build_photo_mappings(records: List[Dict], s3_lookups: Dict[int, Dict]) -> Dict:
    """
    Group database records by unique photo and build mappings.

    Args:
        records: All database records
        s3_lookups: Dict of {year: {filename: s3_key}}

    Returns:
        Dict with:
            - photos: List of photo mappings (only those found in S3)
            - stats: Summary statistics
    """
    # Group records by unique photo identifier
    photo_groups = defaultdict(list)

    for record in records:
        # Photo identifier: (Year, Date, Camera, Card, PhotoNumber)
        photo_key = (
            record['Year'],
            record['Date'],
            record['CameraNumber'],
            record['CardNumber'],
            record['PhotoNumber']
        )
        photo_groups[photo_key].append(record)

    print(f"\n📊 Grouped {len(records):,} database records into {len(photo_groups):,} unique photos")

    # Build mappings for photos that exist in S3
    photo_mappings = []
    species_distribution = defaultdict(int)
    colony_distribution = defaultdict(int)
    year_distribution = defaultdict(int)

    matched = 0
    not_found = 0

    for i, (photo_key, group_records) in enumerate(photo_groups.items(), 1):
        year, date, camera, card, photo_num = photo_key

        # Convert year to int for s3_lookups dictionary key lookup
        try:
            year_int = int(year)
        except:
            not_found += 1
            continue

        # Reconstruct filename
        filename_variations = reconstruct_filename(date, camera, card, photo_num, year)

        if not filename_variations:
            not_found += 1
            continue

        # Check if exists in S3
        if year_int in s3_lookups:
            s3_key = verify_filename_in_s3(filename_variations, s3_lookups[year_int])

            if s3_key:
                # Collect all species codes for this photo
                species_codes = list(set(r['SpeciesCode'] for r in group_records if r['SpeciesCode']))

                # Generate unique photo ID
                photo_id = f"{year}_{camera}_{card}_{photo_num}"

                # Build mapping entry
                mapping = {
                    'photo_id': photo_id,
                    's3_key': s3_key,
                    's3_path': f"s3://{BUCKET_NAME}/{s3_key}",
                    'species_codes': sorted(species_codes),
                    'species_count': len(species_codes),
                    'metadata': {
                        'year': year,
                        'date': date,
                        'camera': camera,
                        'card': card,
                        'photo_num': photo_num,
                        'colony': group_records[0]['ColonyName'],
                        'database_record_count': len(group_records)
                    }
                }

                photo_mappings.append(mapping)
                matched += 1

                # Update statistics
                for species in species_codes:
                    species_distribution[species] += 1
                colony_distribution[group_records[0]['ColonyName']] += 1
                year_distribution[year] += 1
            else:
                not_found += 1
        else:
            not_found += 1

        # Progress indicator
        if i % 1000 == 0:
            print(f"  Progress: {i:,}/{len(photo_groups):,} photos processed (matched: {matched:,}, not found: {not_found:,})")

    # Final statistics
    stats = {
        'total_database_records': len(records),
        'unique_photos_in_database': len(photo_groups),
        'photos_matched_in_s3': matched,
        'photos_not_found_in_s3': not_found,
        'match_rate': matched / len(photo_groups) * 100 if photo_groups else 0,
        'year_distribution': dict(year_distribution),
        'species_distribution': dict(sorted(species_distribution.items(), key=lambda x: x[1], reverse=True)[:20]),  # Top 20
        'colony_distribution': dict(sorted(colony_distribution.items(), key=lambda x: x[1], reverse=True)[:10]),  # Top 10
        'single_species_photos': sum(1 for p in photo_mappings if p['species_count'] == 1),
        'multi_species_photos': sum(1 for p in photo_mappings if p['species_count'] > 1),
        'generated_at': datetime.now().isoformat()
    }

    return {
        'photos': photo_mappings,
        'stats': stats
    }


def main():
    """Main mapping workflow"""
    print("=" * 70)
    print("🗺️  FILENAME MAPPER - PHASE 2")
    print("=" * 70)
    print(f"Database: {DB_PATH}")
    print(f"S3 Bucket: {BUCKET_NAME}/HighResolutionImages/")

    # Step 1: Query database
    print("\n[1/4] Querying database for all species records...")
    records = query_all_species_records(DB_PATH)
    print(f"✓ Loaded {len(records):,} species records")

    # Step 2: Build S3 file indexes
    print("\n[2/4] Building S3 file indexes...")
    s3_client = get_s3_client()
    s3_lookups = {}

    for year in [2015, 2018, 2021]:
        s3_lookups[year] = list_s3_files_for_year(s3_client, year)

    total_s3_files = sum(len(lookup) for lookup in s3_lookups.values())
    print(f"✓ Indexed {total_s3_files:,} total S3 files")

    # Step 3: Build photo mappings
    print("\n[3/4] Building photo mappings...")
    result = build_photo_mappings(records, s3_lookups)

    # Step 4: Save results
    print("\n[4/4] Saving results...")

    # Save photo mappings
    OUTPUT_FILE.parent.mkdir(exist_ok=True)
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(result['photos'], f, indent=2)

    # Save statistics
    with open(STATS_FILE, 'w') as f:
        json.dump(result['stats'], f, indent=2)

    # Print summary
    stats = result['stats']
    print("\n" + "=" * 70)
    print("📊 MAPPING COMPLETE")
    print("=" * 70)
    print(f"Total database records:     {stats['total_database_records']:,}")
    print(f"Unique photos in database:  {stats['unique_photos_in_database']:,}")
    print(f"✓ Photos matched in S3:     {stats['photos_matched_in_s3']:,} ({stats['match_rate']:.1f}%)")
    print(f"✗ Photos not found in S3:   {stats['photos_not_found_in_s3']:,}")
    print()
    print(f"Single-species photos:      {stats['single_species_photos']:,}")
    print(f"Multi-species photos:       {stats['multi_species_photos']:,}")
    print()
    print("Year distribution:")
    for year, count in sorted(stats['year_distribution'].items()):
        print(f"  {year}: {count:,} photos")
    print()
    print("Top 10 species (by photo count):")
    for i, (species, count) in enumerate(list(stats['species_distribution'].items())[:10], 1):
        print(f"  {i:2}. {species}: {count:,} photos")
    print()
    print(f"💾 Photo mappings saved to: {OUTPUT_FILE}")
    print(f"📊 Statistics saved to:     {STATS_FILE}")
    print()


if __name__ == "__main__":
    main()
