"""
S3 Filename Verification Script

Verifies that reconstructed filenames from database metadata actually exist in S3 bucket.
This is the critical first step - without verified filename mapping, the entire weak
supervision pipeline cannot proceed.

Expected database → S3 mapping:
- Database: Date="05/16/15", Camera=1, Card=1, Photo=00094
- Reconstructed: "16 May 2015 Camera 1 Card 1 94.JPG"
- S3 path: "HighResolutionImages/2015/16 May 2015 Camera 1 Card 1 94.JPG"
"""

import sqlite3
import boto3
from botocore import UNSIGNED
from botocore.config import Config
from pathlib import Path
import json
import random
from datetime import datetime
from collections import defaultdict
from typing import Dict, List, Tuple, Optional

# Configuration
# Use absolute paths relative to project root (parent of scripts/ directory)
PROJECT_ROOT = Path(__file__).parent.parent
DB_PATH = PROJECT_ROOT / "data" / "bird_data_complete.db"
BUCKET_NAME = "twi-aviandata"
SAMPLE_SIZE = 100  # Number of records to test
OUTPUT_FILE = PROJECT_ROOT / "data" / "s3_verification_results.json"

# Month name mapping (handle variations)
MONTH_NAMES = {
    1: "January", 2: "February", 3: "March", 4: "April",
    5: "May", 6: "June", 7: "July", 8: "August",
    9: "September", 10: "October", 11: "November", 12: "December"
}

MONTH_ABBREV = {
    1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr", 5: "May", 6: "Jun",
    7: "Jul", 8: "Aug", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec"
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

    print(f"  ✓ Found {count} files in {prefix}")
    return file_lookup


def parse_date(date_str: str) -> Optional[Tuple[int, int, int]]:
    """
    Parse database date field into (day, month, year).

    Examples:
        "05/16/15 12:34:56" → (16, 5, 2015)
        "6/25/10" → (25, 6, 2010)
    """
    try:
        # Try parsing with time
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
    except Exception as e:
        print(f"  ⚠️ Error parsing date '{date_str}': {e}")
        return None


def reconstruct_filename(record: Dict) -> List[str]:
    """
    Reconstruct possible filename variations from database record.

    Returns list of candidate filenames to try (we'll test all variations).

    **Discovered S3 patterns per year:**
    - 2015: "20June2015Cam1Card1 001.JPG" (DDMonthYYYYCamXCardY NNN.JPG)
    - 2018: "19May2018 Camera1-1.jpg" (DDMonthYYYY CameraX-N.jpg) - NO CARD!
    - 2021: "14June2021Camera1Card1-1.jpg" (DDMonthYYYYCameraXCardY-N.jpg)
    """
    date_info = parse_date(record['Date'])
    if not date_info:
        return []

    day, month, year = date_info
    camera = record['CameraNumber']
    card = record['CardNumber']
    photo_num = record['PhotoNumber']

    # Handle NULL values
    if camera is None or card is None or photo_num is None:
        return []

    # Strip leading zeros from photo number
    try:
        photo_num_stripped = str(int(photo_num))
    except:
        photo_num_stripped = photo_num

    # Month name (full only - S3 uses full month names)
    month_name = MONTH_NAMES[month]

    # Generate year-specific patterns
    variations = []

    # **2015 Format:** "20June2015Cam1Card1 001.JPG"
    if year == 2015:
        for photo_str in [photo_num, photo_num_stripped]:
            # Add leading zeros to make 3-digit minimum (e.g., "001", "010", "100")
            photo_padded = photo_str.zfill(3)
            for photo_variant in [photo_str, photo_padded]:
                filename = f"{day}{month_name}{year}Cam{camera}Card{card} {photo_variant}.JPG"
                variations.append(filename)

    # **2018 Format:** "19May2018 Camera1-1.jpg" (no card in filename!)
    elif year == 2018:
        for photo_str in [photo_num, photo_num_stripped]:
            # 2018 doesn't use card numbers in the filename
            filename = f"{day}{month_name}{year} Camera{camera}-{photo_str}.jpg"
            variations.append(filename)

    # **2021 Format:** "14June2021Camera1Card1-1.jpg"
    elif year == 2021:
        for photo_str in [photo_num, photo_num_stripped]:
            filename = f"{day}{month_name}{year}Camera{camera}Card{card}-{photo_str}.jpg"
            variations.append(filename)

    # Fallback: try generic patterns for other years
    else:
        for photo_str in [photo_num, photo_num_stripped]:
            # Try both known patterns
            variations.append(f"{day}{month_name}{year}Cam{camera}Card{card} {photo_str}.JPG")  # 2015-style
            variations.append(f"{day}{month_name}{year}Camera{camera}Card{card}-{photo_str}.jpg")  # 2021-style
            variations.append(f"{day}{month_name}{year} Camera{camera}-{photo_str}.jpg")  # 2018-style

    return variations


def verify_filename_in_s3(filename_variations: List[str], s3_lookup: Dict[str, str]) -> Optional[str]:
    """
    Check if any filename variation exists in S3 lookup dict.

    Returns:
        S3 key if found, None otherwise
    """
    for filename in filename_variations:
        if filename.lower() in s3_lookup:
            return s3_lookup[filename.lower()]
    return None


def sample_database_records(db_path: Path, sample_size: int) -> List[Dict]:
    """
    Sample random records from tblSpeciesData2015_2018_2021.
    """
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Get total count
    cursor.execute('SELECT COUNT(*) FROM "tblSpeciesData2015_2018_2021"')
    total_count = cursor.fetchone()[0]
    print(f"\n📊 Database: {total_count} total records in tblSpeciesData2015_2018_2021")

    # Random sample using RANDOM()
    query = f'''
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
        ORDER BY RANDOM()
        LIMIT {sample_size}
    '''

    cursor.execute(query)
    records = [dict(row) for row in cursor.fetchall()]

    conn.close()

    print(f"✓ Sampled {len(records)} random records")
    return records


def main():
    """Main verification workflow"""
    print("=" * 70)
    print("🔍 S3 FILENAME VERIFICATION")
    print("=" * 70)
    print(f"Target: {BUCKET_NAME}/HighResolutionImages/")
    print(f"Sample size: {SAMPLE_SIZE} records")

    # Step 1: Load database records
    print("\n[1/4] Loading database records...")
    records = sample_database_records(DB_PATH, SAMPLE_SIZE)

    # Step 2: List S3 files by year
    print("\n[2/4] Building S3 file index...")
    s3_client = get_s3_client()
    s3_lookups = {}

    years = set(record['Year'] for record in records if record['Year'])
    for year in sorted(years):
        s3_lookups[year] = list_s3_files_for_year(s3_client, year)

    # Step 3: Attempt filename reconstruction and matching
    print("\n[3/4] Verifying filename reconstruction...")
    results = {
        'matched': [],
        'not_found': [],
        'parse_error': []
    }

    for i, record in enumerate(records, 1):
        year = record['Year']

        # Generate filename variations
        filename_variations = reconstruct_filename(record)

        if not filename_variations:
            results['parse_error'].append({
                'record_id': record['AutoID'],
                'reason': 'Failed to parse metadata',
                'metadata': record
            })
            continue

        # Check if any variation exists in S3
        if year in s3_lookups:
            s3_key = verify_filename_in_s3(filename_variations, s3_lookups[year])

            if s3_key:
                results['matched'].append({
                    'record_id': record['AutoID'],
                    's3_key': s3_key,
                    'species_code': record['SpeciesCode'],
                    'colony': record['ColonyName'],
                    'metadata': record
                })
                status = "✓"
            else:
                results['not_found'].append({
                    'record_id': record['AutoID'],
                    'tried_filenames': filename_variations[:4],  # Show first 4 attempts
                    'metadata': record
                })
                status = "✗"
        else:
            results['not_found'].append({
                'record_id': record['AutoID'],
                'reason': f'Year {year} not in S3 lookups',
                'metadata': record
            })
            status = "?"

        # Progress indicator
        if i % 10 == 0:
            print(f"  Progress: {i}/{SAMPLE_SIZE} records checked...")

    # Step 4: Report results
    print("\n[4/4] Generating report...")

    matched = len(results['matched'])
    not_found = len(results['not_found'])
    parse_errors = len(results['parse_error'])
    total = matched + not_found + parse_errors

    match_rate = (matched / total * 100) if total > 0 else 0

    print("\n" + "=" * 70)
    print("📊 VERIFICATION RESULTS")
    print("=" * 70)
    print(f"Total records tested: {total}")
    print(f"  ✓ Matched:         {matched} ({match_rate:.1f}%)")
    print(f"  ✗ Not found:       {not_found} ({not_found/total*100:.1f}%)")
    print(f"  ⚠️ Parse errors:    {parse_errors} ({parse_errors/total*100:.1f}%)")
    print()

    if match_rate >= 80:
        print("✅ SUCCESS! Match rate ≥80% - filename reconstruction works!")
        print("   → Ready to proceed with Phase 2 (filename mapper)")
    elif match_rate >= 50:
        print("⚠️ PARTIAL SUCCESS: Match rate 50-80% - needs investigation")
        print("   → Check 'not_found' examples to identify pattern issues")
    else:
        print("❌ FAILURE: Match rate <50% - filename reconstruction needs major fixes")
        print("   → Review reconstruction logic and S3 filename patterns")

    # Show sample mismatches
    if results['not_found']:
        print("\n📋 Sample mismatches (first 5):")
        for item in results['not_found'][:5]:
            print(f"\n  Record ID: {item['record_id']}")
            print(f"  Date: {item['metadata']['Date']}")
            print(f"  Camera/Card/Photo: {item['metadata']['CameraNumber']}/{item['metadata']['CardNumber']}/{item['metadata']['PhotoNumber']}")
            if 'tried_filenames' in item:
                print(f"  Tried: {item['tried_filenames'][0]}")

    # Save results to JSON
    output_path = OUTPUT_FILE
    output_path.parent.mkdir(exist_ok=True)

    with open(str(output_path), 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\n💾 Full results saved to: {OUTPUT_FILE}")
    print()


if __name__ == "__main__":
    main()
