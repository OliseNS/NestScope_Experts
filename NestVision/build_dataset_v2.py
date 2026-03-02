"""
NestVision Classification Dataset Builder v2
=============================================

Builds a YOLO classification dataset using tiered confidence labeling.

Unlike v1 which only used "single-species photos" (throwing away 77% of data),
this version extracts training signal from 4 confidence tiers:

  Tier 1 — Gold:      Single-species + Excellent quality + OtherBirds=0
  Tier 2 — High:      Single-species + Good/Excellent quality
  Tier 3 — Dominant:  Multi-species photos where one species is >= 90% of birds
  Tier 4 — Colony:    All photos from single-species colonies

Each crop is tagged with its confidence tier so downstream cleaning
(clean_dataset.py) can filter by quality level.

Pipeline steps (each is resumable):
  1. Query database with tiered confidence across all years (2010-2021)
  2. Build S3 file index and map database records to S3 paths
  3. Download images from S3 (skips already downloaded)
  4. Run Swift detection model to extract bird crops
  5. Create train/val split and dataset.yaml

Usage:
    python NestVision/build_dataset_v2.py
    python NestVision/build_dataset_v2.py --step 3   # resume from step 3
    python NestVision/build_dataset_v2.py --conf 0.4  # custom detection confidence
    python NestVision/build_dataset_v2.py --tiers 1,2  # only use Tier 1 and 2
"""

import os
import sys
import json
import sqlite3
import shutil
import random
import argparse
import time
from pathlib import Path
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import cv2

# ============================================================================
# CONFIGURATION
# ============================================================================

PROJECT_ROOT = Path(__file__).parent.parent
DB_PATH = PROJECT_ROOT / "data" / "bird_data_complete.db"
BUCKET_NAME = "twi-aviandata"

# Output directories
IMAGES_DIR = PROJECT_ROOT / "data" / "weak_supervision" / "downloaded_images"
CROPS_DIR = PROJECT_ROOT / "NestVision" / "crops_v2"
DATASET_DIR = PROJECT_ROOT / "NestVision" / "classify_v2"
STATE_FILE = PROJECT_ROOT / "NestVision" / "pipeline_state_v2.json"
MAPPINGS_CACHE = PROJECT_ROOT / "NestVision" / "all_year_mappings.json"

# Detection settings (BirdDetector handles model loading internally)
DETECTION_CONF = 0.45        # High conf for clean training data
MIN_CROP_PX = 10             # Absolute minimum — below this is pixel noise, not a bird
CROP_PADDING = 0.10          # 10% padding — tight crop so the bird dominates the frame.
                             # 30% was too much for classification (included neighboring birds).

# Crop caps — skip SAHI entirely once a species has enough crops
MAX_CROPS_PER_SPECIES = 500  # Per real species (enough for training + val split)

# Dataset settings
DATASET_IMGSZ = 320  # Larger than default 224 to capture features from tiny birds
VAL_SPLIT = 0.15     # 15% for validation
RANDOM_SEED = 42
MIN_CROPS_TO_TRAIN = 30       # Drop species with fewer crops than this
DATASET_CAP_PER_CLASS = 500   # Max crops per species in final dataset

# Species codes that mean "unknown/unidentified" in the database
# UN* = Unknown (UNTE=Unknown Tern, UNCO=Unknown Cormorant, UNWA=Unknown Wading, etc.)
# US* = Unknown Sternidae (USTE)
UNKNOWN_PREFIXES = ("UN", "US")

# Ambiguous species codes that can't be resolved to a single species.
# These are expert annotations like "could be Great or Snowy Egret" — useless
# for training a classifier that needs unambiguous labels.
AMBIGUOUS_CODES = {
    "WHEG",   # White Egret (Great or Snowy — can't tell)
    "SDHE",   # Small Dark Heron/Egret
    "ROSA",   # Royal or Sandwich Tern
    "TRSN",   # Tricolored Heron or Snowy Egret
    "REEG WM", "REEG DM",  # Reddish Egret color morphs (too specific, merge later)
}

# Tier 3 threshold: minimum % of birds that must be one species to count
# as "dominant species". 90% means in a photo with 100 birds, at least
# 90 must be the same species. The remaining 10% become label noise —
# but the confident learning step (clean_dataset.py) will catch most of them.
DOMINANT_SPECIES_PCT = 90.0

# Minimum bird count for a species to qualify as dominant in a photo.
# Prevents photos with tiny counts (e.g., 2 of 2 = 100%) from qualifying.
DOMINANT_MIN_BIRDS = 5

# Month name mapping
MONTH_NAMES = {
    1: "January", 2: "February", 3: "March", 4: "April",
    5: "May", 6: "June", 7: "July", 8: "August",
    9: "September", 10: "October", 11: "November", 12: "December"
}


# ============================================================================
# STATE MANAGEMENT (resumability)
# ============================================================================

def load_state() -> dict:
    """Load pipeline state from disk."""
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"completed_steps": [], "last_updated": None}


def save_state(state: dict):
    """Save pipeline state to disk."""
    state["last_updated"] = datetime.now().isoformat()
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def is_step_done(state: dict, step: int) -> bool:
    return step in state.get("completed_steps", [])


def mark_step_done(state: dict, step: int):
    if step not in state["completed_steps"]:
        state["completed_steps"].append(step)
    save_state(state)


# ============================================================================
# STEP 1: QUERY DATABASE WITH TIERED CONFIDENCE
# ============================================================================

def parse_date(date_str: str) -> Optional[Tuple[int, int, int]]:
    """Parse database date field into (day, month, year).

    The database stores dates like "06/25/10 00:00:00" or "5/19/11 00:00:00".
    Returns (day, month_number, full_year) or None if parsing fails.
    """
    try:
        date_part = date_str.split(" ")[0] if " " in date_str else date_str
        parts = date_part.split("/")
        if len(parts) != 3:
            return None
        month, day, year = int(parts[0]), int(parts[1]), int(parts[2])
        if year < 100:
            year += 2000
        return (day, month, year)
    except Exception:
        return None


def _is_usable_species(code: str) -> bool:
    """Check if a species code is usable for training.

    Rejects unknown prefixes (UN*, US*) and ambiguous codes (WHEG, SDHE, etc.)
    """
    upper = code.upper().strip()
    if upper.startswith(UNKNOWN_PREFIXES):
        return False
    if upper in AMBIGUOUS_CODES:
        return False
    return True


def _make_photo_dict(year, date, camera, card, photo_num, species,
                     table_source, tier, dominance_pct=None):
    """Create a standardized photo record dict."""
    rec = {
        "year": str(year).strip(),
        "date": str(date).strip(),
        "camera": str(camera).strip(),
        "card": str(card).strip(),
        "photo_num": str(photo_num).strip(),
        "species": species.strip(),
        "table_source": table_source,
        "tier": tier,
    }
    if dominance_pct is not None:
        rec["dominance_pct"] = dominance_pct
    return rec


def _photo_key(p: dict) -> str:
    """Unique key for deduplication across tiers."""
    return f"{p['year']}_{p['camera']}_{p['card']}_{p['photo_num']}"


def _query_tier1_gold(cursor) -> List[dict]:
    """Tier 1 — Gold Standard: Single-species + Excellent + OtherBirds=0.

    Only available for 2015-2021 (the only table with the OtherBirds column).
    These are photos where an expert confirmed NO other species are visible.
    """
    cursor.execute("""
        SELECT Year, Date, CameraNumber, CardNumber, PhotoNumber,
               MIN(SpeciesCode) as SpeciesCode
        FROM tblSpeciesData2015_2018_2021
        WHERE PQ = 'E'
          AND "BestForBPE?" = 'Y'
          AND (OtherBirds = 0 OR OtherBirds IS NULL OR OtherBirds = '')
          AND SpeciesCode IS NOT NULL AND SpeciesCode != ''
        GROUP BY Year, Date, CameraNumber, CardNumber, PhotoNumber
        HAVING COUNT(DISTINCT SpeciesCode) = 1
    """)
    results = []
    for row in cursor.fetchall():
        year, date, camera, card, photo_num, species = row
        if _is_usable_species(species):
            results.append(_make_photo_dict(
                year, date, camera, card, photo_num, species,
                "tblSpeciesData2015_2018_2021", tier=1
            ))
    return results


def _query_tier2_single_species(cursor) -> List[dict]:
    """Tier 2 — High Confidence: Single-species + Good/Excellent quality.

    Queries all 3 database tables. This is the original approach but with
    a photo quality filter added.
    """
    tables = [
        ("tblSpeciesData2010", "tblSpeciesData2010"),
        ("tblSpeciesData2011-2013", '"tblSpeciesData2011-2013"'),
        ("tblSpeciesData2015_2018_2021", "tblSpeciesData2015_2018_2021"),
    ]
    results = []
    for table_name, table_ref in tables:
        cursor.execute(f"""
            SELECT Year, Date, CameraNumber, CardNumber, PhotoNumber,
                   MIN(SpeciesCode) as SpeciesCode
            FROM {table_ref}
            WHERE SpeciesCode IS NOT NULL
              AND SpeciesCode != '' AND SpeciesCode != 'N/A' AND SpeciesCode != '0'
              AND PQ IN ('E', 'G')
            GROUP BY Year, Date, CameraNumber, CardNumber, PhotoNumber
            HAVING COUNT(DISTINCT SpeciesCode) = 1
        """)
        for row in cursor.fetchall():
            year, date, camera, card, photo_num, species = row
            if _is_usable_species(species):
                results.append(_make_photo_dict(
                    year, date, camera, card, photo_num, species,
                    table_name, tier=2
                ))
    return results


def _query_tier3_dominant(cursor) -> List[dict]:
    """Tier 3 — Dominant Species: One species is >= 90% of birds in a multi-species photo.

    For each photo, calculates each species' share of total birds. If one species
    dominates (e.g., 50 LAGU out of 53 total = 94%), all crops from that photo
    get labeled as the dominant species.

    The ~6% of crops that are actually the minority species will be caught
    by the confident learning step in clean_dataset.py.
    """
    tables = [
        ("tblSpeciesData2010", "tblSpeciesData2010"),
        ("tblSpeciesData2011-2013", '"tblSpeciesData2011-2013"'),
        ("tblSpeciesData2015_2018_2021", "tblSpeciesData2015_2018_2021"),
    ]
    results = []
    for table_name, table_ref in tables:
        cursor.execute(f"""
            WITH photo_species AS (
                SELECT Year, Date, CameraNumber, CardNumber, PhotoNumber,
                       SpeciesCode,
                       COALESCE(WBN, 0) + COALESCE(Site, 0) + COALESCE(Brood, 0) as bird_count
                FROM {table_ref}
                WHERE SpeciesCode IS NOT NULL AND SpeciesCode != ''
                  AND PQ IN ('E', 'G')
            ),
            photo_totals AS (
                SELECT Year, Date, CameraNumber, CardNumber, PhotoNumber,
                       SpeciesCode, bird_count,
                       SUM(bird_count) OVER (
                           PARTITION BY Year, Date, CameraNumber, CardNumber, PhotoNumber
                       ) as total_birds
                FROM photo_species
                WHERE bird_count > 0
            )
            SELECT Year, Date, CameraNumber, CardNumber, PhotoNumber,
                   SpeciesCode, bird_count, total_birds,
                   ROUND(100.0 * bird_count / total_birds, 1) as pct
            FROM photo_totals
            WHERE total_birds > 0
              AND ROUND(100.0 * bird_count / total_birds, 1) >= {DOMINANT_SPECIES_PCT}
              AND bird_count >= {DOMINANT_MIN_BIRDS}
        """)
        for row in cursor.fetchall():
            year, date, camera, card, photo_num, species = row[:6]
            pct = row[8]
            if _is_usable_species(species):
                results.append(_make_photo_dict(
                    year, date, camera, card, photo_num, species,
                    table_name, tier=3, dominance_pct=pct
                ))
    return results


def _query_tier4_colony(cursor) -> set:
    """Tier 4 — Colony-Level: Colonies where only one species was ever recorded.

    Returns a set of (ColonyName, Year) tuples. Photos from these colony-years
    can be promoted to higher confidence even if they're multi-species at the
    photo level — because the entire colony has only one species.

    This is used as a VALIDATION layer: if a crop from Tier 2/3 is from a
    single-species colony, we can be more confident in the label.
    """
    cursor.execute("""
        SELECT ColonyName, Year, MIN(SpeciesCode) as species
        FROM "tblColonyTotals2010-2021_MayJuneCombined"
        WHERE SpeciesCode IS NOT NULL AND SpeciesCode != ''
          AND SpeciesCode NOT LIKE 'UN%'
        GROUP BY ColonyName, Year
        HAVING COUNT(DISTINCT SpeciesCode) = 1
    """)
    return {(row[0], str(row[1])) for row in cursor.fetchall()}


def query_photos_tiered(tiers: List[int] = None) -> List[dict]:
    """Query database with tiered confidence strategy.

    Tiers are queried in priority order (1→2→3). If a photo already appeared
    in a higher tier, it keeps that tier's label and is not duplicated.

    Tier 4 (colony-level) is used as a cross-reference to boost confidence
    of photos from known single-species colonies.

    Args:
        tiers: Which tiers to include. Default: [1, 2, 3]

    Returns:
        List of photo dicts with 'tier' field indicating confidence level.
    """
    if tiers is None:
        tiers = [1, 2, 3]

    print("\n" + "=" * 70)
    print("STEP 1: Query database with tiered confidence")
    print(f"  Active tiers: {tiers}")
    print("=" * 70)

    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    # Track seen photos to avoid duplicates across tiers
    seen_keys = set()
    all_photos = []
    tier_counts = defaultdict(int)

    # Tier 4 is always loaded as a cross-reference (doesn't add photos directly)
    single_species_colonies = _query_tier4_colony(cursor)
    print(f"  Tier 4 cross-ref: {len(single_species_colonies)} single-species colony-years")

    # Query each active tier in priority order
    tier_queries = {
        1: ("Gold (single-sp + Excellent + OtherBirds=0)", _query_tier1_gold),
        2: ("High (single-sp + Good/Excellent)", _query_tier2_single_species),
        3: ("Dominant (>= 90% of birds in photo)", _query_tier3_dominant),
    }

    for tier_num in sorted(tiers):
        if tier_num not in tier_queries:
            continue
        tier_label, query_fn = tier_queries[tier_num]
        tier_photos = query_fn(cursor)

        added = 0
        for p in tier_photos:
            key = _photo_key(p)
            if key not in seen_keys:
                seen_keys.add(key)
                all_photos.append(p)
                added += 1
                tier_counts[tier_num] += 1

        print(f"  Tier {tier_num} ({tier_label}): {len(tier_photos)} queried, "
              f"{added} new (after dedup)")

    conn.close()

    # Species breakdown
    species_counts = defaultdict(lambda: defaultdict(int))
    for p in all_photos:
        species_counts[p["species"]][p["tier"]] += 1

    print(f"\n  Total photos: {len(all_photos)}")
    print(f"  Tier breakdown: " + ", ".join(
        f"T{t}={c}" for t, c in sorted(tier_counts.items())))
    print(f"  Unique species: {len(species_counts)}")

    print(f"\n  {'Species':<8} {'T1':>5} {'T2':>5} {'T3':>5} {'Total':>7}")
    print(f"  {'-' * 33}")
    for sp in sorted(species_counts.keys(),
                     key=lambda s: -sum(species_counts[s].values())):
        t1 = species_counts[sp].get(1, 0)
        t2 = species_counts[sp].get(2, 0)
        t3 = species_counts[sp].get(3, 0)
        total = t1 + t2 + t3
        skip = " SKIP" if sp.upper().startswith(UNKNOWN_PREFIXES) else ""
        print(f"  {sp:<8} {t1:>5} {t2:>5} {t3:>5} {total:>7}{skip}")

    return all_photos


# ============================================================================
# STEP 2: MAP DATABASE RECORDS TO S3 PATHS
# ============================================================================

def reconstruct_s3_variations(year: int, day: int, month: int,
                              camera: int, card: int,
                              photo_num: str) -> List[str]:
    """Generate candidate S3 key patterns for a given photo.

    Each year has a different filename convention in the S3 bucket.
    We generate multiple variations (with/without zero padding, etc.)
    and try them all against the S3 file index.
    """
    month_name = MONTH_NAMES[month]
    photo_stripped = str(int(photo_num)) if photo_num.isdigit() else photo_num
    photo_padded = photo_stripped.zfill(3)

    # List of (filename, S3 prefix path) candidates
    candidates = []

    if year == 2010:
        # Pattern: "10 June 2010 Camera 1 Card 1 001.JPG"
        # Path:    HighResolutionImages/2010/June 2010/10 June 2010/
        #          10 June 2010 Camera {cam} Card {card}/
        for pn in [photo_padded, photo_stripped]:
            fname = f"{day} {month_name} {year} Camera {camera} Card {card} {pn}.JPG"
            prefix = (f"HighResolutionImages/{year}/{month_name} {year}/"
                      f"{day} {month_name} {year}/"
                      f"{day} {month_name} {year} Camera {camera} Card {card}/")
            candidates.append(prefix + fname)

    elif year == 2011:
        # Pattern: "13June2011Camera1Card1 001.JPG"
        # Path:    HighResolutionImages/2011/June 2011/13June2011/
        #          13June2011Camera{cam}Card{card}/
        for pn in [photo_padded, photo_stripped]:
            fname = f"{day}{month_name}{year}Camera{camera}Card{card} {pn}.JPG"
            prefix = (f"HighResolutionImages/{year}/{month_name} {year}/"
                      f"{day}{month_name}{year}/"
                      f"{day}{month_name}{year}Camera{camera}Card{card}/")
            candidates.append(prefix + fname)

    elif year in (2012, 2013):
        # Pattern: "18June2012Cam1Card1 001.jpg" (2012=.jpg, 2013=.JPG)
        # Path:    HighResolutionImages/{year}/June {year}/{day}June{year}/
        #          {day}June{year}Cam{cam}Card{card}/
        ext = ".jpg" if year == 2012 else ".JPG"
        for pn in [photo_padded, photo_stripped]:
            fname = f"{day}{month_name}{year}Cam{camera}Card{card} {pn}{ext}"
            prefix = (f"HighResolutionImages/{year}/{month_name} {year}/"
                      f"{day}{month_name}{year}/"
                      f"{day}{month_name}{year}Cam{camera}Card{card}/")
            candidates.append(prefix + fname)

    elif year == 2015:
        # Pattern: "20June2015Cam1Card1 001.JPG"
        # Path:    HighResolutionImages/2015/June2015/20June2015/
        #          20June2015 Cam{cam}Card{card}/
        for pn in [photo_padded, photo_stripped]:
            fname = f"{day}{month_name}{year}Cam{camera}Card{card} {pn}.JPG"
            prefix = (f"HighResolutionImages/{year}/{month_name}{year}/"
                      f"{day}{month_name}{year}/"
                      f"{day}{month_name}{year} Cam{camera}Card{card}/")
            candidates.append(prefix + fname)

    elif year == 2018:
        # Pattern: "19May2018 Camera1-1.jpg" (no card!)
        # Path:    HighResolutionImages/2018/  (flat directory)
        for pn in [photo_stripped, photo_padded]:
            fname = f"{day}{month_name}{year} Camera{camera}-{pn}.jpg"
            candidates.append(f"HighResolutionImages/{year}/{fname}")

    elif year == 2021:
        # Pattern: "14June2021Camera1Card1-1.jpg"
        # Path:    HighResolutionImages/2021/June2021/14June21/14June21Camera1/
        short_year = str(year)[2:]  # "21"
        for pn in [photo_stripped, photo_padded]:
            fname = f"{day}{month_name}{year}Camera{camera}Card{card}-{pn}.jpg"
            prefix = (f"HighResolutionImages/{year}/{month_name}{year}/"
                      f"{day}{month_name}{short_year}/"
                      f"{day}{month_name}{short_year}Camera{camera}/")
            candidates.append(prefix + fname)

    return candidates


def build_s3_index_for_year(s3_client, year: int) -> Dict[str, str]:
    """List all files in S3 for a given year.

    Returns dict mapping lowercase_s3_key → actual_s3_key.
    This handles case-insensitive matching since S3 keys may vary.
    """
    prefix = f"HighResolutionImages/{year}/"
    paginator = s3_client.get_paginator("list_objects_v2")

    file_lookup = {}
    count = 0

    for page in paginator.paginate(Bucket=BUCKET_NAME, Prefix=prefix):
        for obj in page.get("Contents", []):
            key = obj["Key"]
            file_lookup[key.lower()] = key
            count += 1

    print(f"    Year {year}: {count:,} files indexed")
    return file_lookup


def build_all_mappings(photos: List[dict]) -> List[dict]:
    """Map each single-species photo record to an S3 key.

    For 2015-2021, we first check existing mappings (photo_mappings_2015_2021.json)
    to avoid re-querying S3. For 2010-2013, we build the S3 index and reconstruct
    filenames using year-specific patterns.

    Returns the photos list with added 's3_key' and 'local_filename' fields.
    """
    print("\n" + "=" * 70)
    print("STEP 2: Map database records to S3 paths")
    print("=" * 70)

    # Check if we have a cached mapping file
    if MAPPINGS_CACHE.exists():
        print(f"  Loading cached mappings from {MAPPINGS_CACHE.name}...")
        with open(MAPPINGS_CACHE) as f:
            cached = json.load(f)
        print(f"  Loaded {len(cached)} cached mappings")
        return cached

    # Load existing 2015-2021 mappings for fast lookup
    existing_mappings = {}
    mappings_file = PROJECT_ROOT / "data" / "weak_supervision" / "photo_mappings_2015_2021.json"
    if mappings_file.exists():
        with open(mappings_file) as f:
            for m in json.load(f):
                existing_mappings[m["photo_id"]] = m["s3_key"]
        print(f"  Loaded {len(existing_mappings)} existing 2015-2021 mappings")

    # Determine which years need S3 indexing
    years_needed = set()
    for p in photos:
        year = int(p["year"])
        photo_id = f"{p['year']}_{p['camera']}_{p['card']}_{p['photo_num']}"
        if photo_id not in existing_mappings:
            years_needed.add(year)

    # Build S3 indexes for years not in existing mappings
    s3_indexes = {}
    if years_needed:
        import boto3
        from botocore import UNSIGNED
        from botocore.config import Config as BotoConfig

        print(f"  Building S3 index for years: {sorted(years_needed)}")
        s3_client = boto3.client("s3", config=BotoConfig(signature_version=UNSIGNED))
        for year in sorted(years_needed):
            s3_indexes[year] = build_s3_index_for_year(s3_client, year)

    # Map each photo to its S3 key
    mapped = []
    found = 0
    not_found = 0

    for p in photos:
        year = int(p["year"])
        photo_id = f"{p['year']}_{p['camera']}_{p['card']}_{p['photo_num']}"

        # Try existing mappings first (2015-2021)
        if photo_id in existing_mappings:
            p["s3_key"] = existing_mappings[photo_id]
            ext = p["s3_key"].split(".")[-1]
            p["local_filename"] = f"{photo_id}.{ext}"
            mapped.append(p)
            found += 1
            continue

        # Parse date to get day + month for filename reconstruction
        date_info = parse_date(p["date"])
        if not date_info:
            not_found += 1
            continue

        day, month, _ = date_info

        try:
            camera = int(p["camera"])
            card = int(p["card"])
        except (ValueError, TypeError):
            not_found += 1
            continue

        # Generate candidate S3 keys
        candidates = reconstruct_s3_variations(
            year, day, month, camera, card, p["photo_num"]
        )

        # Try each candidate against the S3 index
        s3_key = None
        if year in s3_indexes:
            for candidate in candidates:
                if candidate.lower() in s3_indexes[year]:
                    s3_key = s3_indexes[year][candidate.lower()]
                    break

        if s3_key:
            p["s3_key"] = s3_key
            ext = s3_key.split(".")[-1]
            p["local_filename"] = f"{photo_id}.{ext}"
            mapped.append(p)
            found += 1
        else:
            not_found += 1

    print(f"\n  Mapping results:")
    print(f"    Found in S3:     {found}")
    print(f"    Not found in S3: {not_found}")
    print(f"    Match rate:      {found/(found+not_found)*100:.1f}%")

    # Cache the mappings so we don't need to rebuild
    MAPPINGS_CACHE.parent.mkdir(parents=True, exist_ok=True)
    with open(MAPPINGS_CACHE, "w") as f:
        json.dump(mapped, f, indent=2)
    print(f"  Saved mappings cache to {MAPPINGS_CACHE.name}")

    return mapped


# ============================================================================
# STEP 3: DOWNLOAD IMAGES FROM S3
# ============================================================================

def download_images(photos: List[dict], max_workers: int = 10) -> List[dict]:
    """Download images from S3 concurrently, skipping ones we already have.

    Images are saved as {photo_id}.{ext} in the IMAGES_DIR.
    This is fully resumable — it checks for existing files before downloading.

    Uses ThreadPoolExecutor to download multiple images in parallel.
    Each thread gets its own S3 client (boto3 clients aren't thread-safe,
    but creating one per thread is lightweight).

    Args:
        photos: List of photo dicts with 's3_key' and 'local_filename'
        max_workers: Number of concurrent download threads (default: 10)
    """
    print("\n" + "=" * 70)
    print("STEP 3: Download images from S3")
    print("=" * 70)

    from concurrent.futures import ThreadPoolExecutor, as_completed
    import threading

    import boto3
    from botocore import UNSIGNED
    from botocore.config import Config as BotoConfig

    IMAGES_DIR.mkdir(parents=True, exist_ok=True)

    # Check what's already downloaded
    existing_files = set(os.listdir(IMAGES_DIR))

    to_download = []
    already_have = []

    for p in photos:
        if p["local_filename"] in existing_files:
            already_have.append(p)
        else:
            to_download.append(p)

    print(f"  Already downloaded: {len(already_have)}")
    print(f"  Need to download:   {len(to_download)}")

    if not to_download:
        print("  Nothing to download!")
        return photos

    # Thread-safe counters
    lock = threading.Lock()
    stats = {"downloaded": 0, "failed": 0, "completed": 0}

    # Thread-local storage so each thread gets its own S3 client
    thread_local = threading.local()

    def get_s3_client():
        """Get or create an S3 client for the current thread."""
        if not hasattr(thread_local, "s3_client"):
            thread_local.s3_client = boto3.client(
                "s3", config=BotoConfig(signature_version=UNSIGNED)
            )
        return thread_local.s3_client

    def download_one(p: dict) -> bool:
        """Download a single image. Returns True on success."""
        local_path = IMAGES_DIR / p["local_filename"]
        try:
            client = get_s3_client()
            client.download_file(BUCKET_NAME, p["s3_key"], str(local_path))
            return True
        except Exception:
            # Clean up partial file if download failed
            if local_path.exists():
                local_path.unlink()
            return False

    print(f"  Downloading with {max_workers} concurrent threads...")
    start_time = time.time()

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all downloads
        future_to_photo = {
            executor.submit(download_one, p): p for p in to_download
        }

        # Process results as they complete
        for future in as_completed(future_to_photo):
            success = future.result()
            with lock:
                stats["completed"] += 1
                if success:
                    stats["downloaded"] += 1
                else:
                    stats["failed"] += 1

                # Progress update every 50 completions
                if stats["completed"] % 50 == 0 or stats["completed"] == len(to_download):
                    elapsed = time.time() - start_time
                    rate = stats["completed"] / elapsed if elapsed > 0 else 0
                    remaining = len(to_download) - stats["completed"]
                    eta = remaining / rate if rate > 0 else 0
                    print(f"    [{stats['completed']}/{len(to_download)}] "
                          f"Downloaded {stats['downloaded']}, "
                          f"Failed {stats['failed']}, "
                          f"Rate: {rate:.1f} img/s, ETA: {eta/60:.0f}min")

    print(f"\n  Download complete:")
    print(f"    Downloaded: {stats['downloaded']}")
    print(f"    Failed:     {stats['failed']}")
    print(f"    Total available: {len(already_have) + stats['downloaded']}")

    return photos


# ============================================================================
# STEP 4: RUN DETECTION AND EXTRACT CROPS
# ============================================================================

def extract_crops(photos: List[dict], det_conf: float = DETECTION_CONF):
    """Run detection on each image and extract bird crops.

    Uses the existing BirdDetector from server/cv_tools/inference.py.
    Every detection gets the ground truth species label from the database.
    Unknown species (UN*/US*) are skipped entirely — not extracted.

    Saves a progress file so we can resume if interrupted.
    """
    print("\n" + "=" * 70)
    print("STEP 4: Run detection and extract bird crops")
    print("=" * 70)

    # Import the existing BirdDetector — reuses all detection logic
    sys.path.insert(0, str(PROJECT_ROOT))
    from server.cv_tools.inference import BirdDetector

    # Load progress (which images we've already processed)
    progress_file = CROPS_DIR / "extraction_progress.json"
    if progress_file.exists():
        with open(progress_file) as f:
            progress = json.load(f)
    else:
        progress = {"processed_images": {}, "total_crops": 0, "species_counts": {}}

    processed_set = set(progress["processed_images"].keys())

    # Filter to photos that exist on disk, haven't been processed, and are real species
    to_process = []
    already_done = 0
    missing = 0
    skipped_unknown = 0

    for p in photos:
        # Skip unknown species entirely — no point extracting crops for them
        if p["species"].upper().startswith(UNKNOWN_PREFIXES):
            skipped_unknown += 1
            continue
        img_path = IMAGES_DIR / p["local_filename"]
        if p["local_filename"] in processed_set:
            already_done += 1
        elif img_path.exists():
            to_process.append(p)
        else:
            missing += 1

    print(f"  Already processed: {already_done}")
    print(f"  To process:        {len(to_process)}")
    print(f"  Missing images:    {missing}")
    print(f"  Skipped unknown:   {skipped_unknown} (UN*/US* species — not trainable)")

    if not to_process:
        print("  Nothing to process!")
        _print_crop_stats(progress)
        return progress

    # If old progress has UNK entries, wipe everything and start fresh
    # Old runs routed crops to UNK — that logic is removed now
    if progress.get("species_counts", {}).get("UNK", 0) > 0:
        print(f"  Old progress has UNK entries — wiping crops and starting fresh...")
        if CROPS_DIR.exists():
            shutil.rmtree(CROPS_DIR)
        progress = {"processed_images": {}, "total_crops": 0, "species_counts": {}}
        processed_set = set()

    # Initialize the detector (same one used by the API)
    print(f"  Initializing BirdDetector (Swift mode)...")
    detector = BirdDetector()
    CROPS_DIR.mkdir(parents=True, exist_ok=True)

    start_time = time.time()
    total_new_crops = 0
    skipped_capped = 0

    for i, p in enumerate(to_process, 1):
        img_path = IMAGES_DIR / p["local_filename"]
        species = p["species"]

        # Check if this species already has enough crops — skip entire image
        current_count = progress["species_counts"].get(species, 0)
        if current_count >= MAX_CROPS_PER_SPECIES:
            skipped_capped += 1
            progress["processed_images"][p["local_filename"]] = {"status": "capped"}
            if skipped_capped % 100 == 0:
                print(f"    ... skipped {skipped_capped} images (species capped)")
            continue

        try:
            result = detector.predict(
                str(img_path),
                conf_threshold=det_conf,
                fast_mode=True,
                verbose=False,
                classify=False,
            )
        except Exception as e:
            progress["processed_images"][p["local_filename"]] = {
                "status": "error", "error": str(e)
            }
            continue

        detections = result.get("detections", [])

        # Read the original image to extract crops
        image = cv2.imread(str(img_path))
        if image is None:
            progress["processed_images"][p["local_filename"]] = {"status": "read_error"}
            continue

        # Every detection in a single-species image IS that species.
        # The species label comes from the database ground truth, not the detector.
        img_h, img_w = image.shape[:2]
        img_crops = 0
        for det in detections:
            bbox = det["bbox"]
            x1, y1, x2, y2 = int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])

            crop_w = x2 - x1
            crop_h = y2 - y1

            # Add padding around the bounding box for context
            pad_x = int(crop_w * CROP_PADDING)
            pad_y = int(crop_h * CROP_PADDING)
            x1_pad = max(0, x1 - pad_x)
            y1_pad = max(0, y1 - pad_y)
            x2_pad = min(img_w, x2 + pad_x)
            y2_pad = min(img_h, y2 + pad_y)

            padded_w = x2_pad - x1_pad
            padded_h = y2_pad - y1_pad

            # Skip pixel noise (sub-10px artifacts), everything else is a real bird
            if padded_w < MIN_CROP_PX or padded_h < MIN_CROP_PX:
                continue

            # Create species directory
            species_dir = CROPS_DIR / species
            species_dir.mkdir(parents=True, exist_ok=True)

            # Extract padded crop
            crop = image[y1_pad:y2_pad, x1_pad:x2_pad]
            if crop.size == 0:
                continue

            crop_filename = f"{p['local_filename'].rsplit('.', 1)[0]}_crop{img_crops:03d}.jpg"
            crop_path = species_dir / crop_filename

            cv2.imwrite(str(crop_path), crop)

            progress["total_crops"] += 1
            progress["species_counts"][species] = \
                progress["species_counts"].get(species, 0) + 1
            img_crops += 1
            total_new_crops += 1

        progress["processed_images"][p["local_filename"]] = {
            "status": "ok",
            "n_detections": len(detections),
            "n_crops": img_crops,
            "species": species,
        }

        # Per-image progress line
        elapsed = time.time() - start_time
        eta = (len(to_process) - i) / (i / elapsed) if elapsed > 0 else 0
        sp_count = progress["species_counts"].get(species, 0)
        print(f"    [{i}/{len(to_process)}] {species:>6} +{img_crops} "
              f"({sp_count}/{MAX_CROPS_PER_SPECIES}) "
              f"| Total: {total_new_crops} | Skipped: {skipped_capped} "
              f"| ETA: {eta/60:.0f}min")

        # Save progress to disk every 50 images (disk writes are slow)
        if i % 50 == 0 or i == len(to_process):
            with open(progress_file, "w") as f:
                json.dump(progress, f)

    # Final save
    with open(progress_file, "w") as f:
        json.dump(progress, f, indent=2)

    print(f"\n  Skipped {skipped_capped} images (species already at cap)")
    _print_crop_stats(progress)
    return progress


def _print_crop_stats(progress: dict):
    """Print crop extraction statistics."""
    print(f"\n  Crop extraction summary:")
    print(f"    Total crops: {progress['total_crops']}")
    print(f"    Species breakdown:")
    for sp, count in sorted(progress["species_counts"].items(), key=lambda x: -x[1]):
        pct = count / progress["total_crops"] * 100 if progress["total_crops"] > 0 else 0
        print(f"      {sp}: {count} ({pct:.1f}%)")


# ============================================================================
# STEP 5: BUILD TRAIN/VAL DATASET
# ============================================================================

def build_dataset(progress: dict):
    """Organize crops into YOLO classification dataset format.

    Filtering rules:
      1. DROP UNK entirely — these are low-confidence noise, not real training signal
      2. DROP species with fewer than MIN_CROPS_TO_TRAIN crops — not enough to learn from
      3. CAP each species at DATASET_CAP_PER_CLASS — prevents dominant species bias

    Structure:
        classify_v2/
          train/BRPE/, train/LAGU/, ...
          val/BRPE/, val/LAGU/, ...
          dataset.yaml
    """
    print("\n" + "=" * 70)
    print("STEP 5: Build train/val dataset")
    print("=" * 70)

    random.seed(RANDOM_SEED)

    # Remove old dataset if it exists
    if DATASET_DIR.exists():
        print(f"  Removing old dataset at {DATASET_DIR.name}/...")
        shutil.rmtree(DATASET_DIR)

    train_dir = DATASET_DIR / "train"
    val_dir = DATASET_DIR / "val"

    # Collect all crop files per species
    all_species_crops = {}

    for species_dir in sorted(CROPS_DIR.iterdir()):
        if not species_dir.is_dir():
            continue
        species = species_dir.name
        crops = sorted(species_dir.glob("*.jpg"))
        all_species_crops[species] = [str(c) for c in crops]

    # Print raw stats
    print(f"\n  Raw crops from extraction ({len(all_species_crops)} species):")
    total_raw = 0
    for sp, crops in sorted(all_species_crops.items(), key=lambda x: -len(x[1])):
        total_raw += len(crops)
        print(f"    {sp}: {len(crops)}")
    print(f"    Total: {total_raw}")

    # --- FILTER 1: Drop UNK ---
    dropped_unk = len(all_species_crops.pop("UNK", []))
    if dropped_unk:
        print(f"\n  Dropped UNK: {dropped_unk} crops (noise from low-confidence detections)")

    # --- FILTER 2: Drop species with too few crops ---
    dropped_small = {}
    kept_species = {}
    for sp, crops in all_species_crops.items():
        if len(crops) < MIN_CROPS_TO_TRAIN:
            dropped_small[sp] = len(crops)
        else:
            kept_species[sp] = crops

    if dropped_small:
        print(f"\n  Dropped {len(dropped_small)} species with < {MIN_CROPS_TO_TRAIN} crops:")
        for sp, count in sorted(dropped_small.items()):
            print(f"    {sp}: {count}")

    # --- FILTER 3: Cap large species ---
    print(f"\n  Class cap: {DATASET_CAP_PER_CLASS} per species")
    capped = []
    for sp, crops in kept_species.items():
        if len(crops) > DATASET_CAP_PER_CLASS:
            capped.append(f"{sp}: {len(crops)} → {DATASET_CAP_PER_CLASS}")
            kept_species[sp] = random.sample(crops, DATASET_CAP_PER_CLASS)
    if capped:
        print(f"  Capped species:")
        for msg in capped:
            print(f"    {msg}")

    # --- Build train/val split ---
    split_stats = {}

    for species, crop_paths in kept_species.items():
        random.shuffle(crop_paths)
        n_val = max(1, int(len(crop_paths) * VAL_SPLIT))
        val_crops = crop_paths[:n_val]
        train_crops = crop_paths[n_val:]

        (train_dir / species).mkdir(parents=True, exist_ok=True)
        (val_dir / species).mkdir(parents=True, exist_ok=True)

        for src in train_crops:
            shutil.copy2(src, train_dir / species / Path(src).name)
        for src in val_crops:
            shutil.copy2(src, val_dir / species / Path(src).name)

        split_stats[species] = {
            "train": len(train_crops),
            "val": len(val_crops),
            "total": len(train_crops) + len(val_crops),
        }

    # Create dataset.yaml
    class_names = sorted(split_stats.keys())
    yaml_content = f"""# NestVision Classification Dataset v2
# Generated: {datetime.now().isoformat()}
# Image size: {DATASET_IMGSZ}x{DATASET_IMGSZ}

path: {DATASET_DIR}
train: train
val: val

# Number of classes
nc: {len(class_names)}

# Class names (alphabetical order)
names: {class_names}
"""
    yaml_path = DATASET_DIR / "dataset.yaml"
    with open(yaml_path, "w") as f:
        f.write(yaml_content)

    # Print final stats
    print(f"\n  Dataset created at {DATASET_DIR}")
    print(f"  Classes: {len(class_names)}")
    print(f"\n  {'Species':<10} {'Train':>7} {'Val':>7} {'Total':>7}")
    print(f"  {'-'*35}")

    total_train = 0
    total_val = 0
    for sp in class_names:
        s = split_stats[sp]
        print(f"  {sp:<10} {s['train']:>7} {s['val']:>7} {s['total']:>7}")
        total_train += s["train"]
        total_val += s["val"]

    print(f"  {'-'*35}")
    print(f"  {'TOTAL':<10} {total_train:>7} {total_val:>7} {total_train+total_val:>7}")
    print(f"\n  dataset.yaml: {yaml_path}")
    print(f"  Recommended training command:")
    print(f"    yolo classify train data={yaml_path} model=yolov8s-cls.pt "
          f"imgsz={DATASET_IMGSZ} epochs=100 batch=64")

    # Save split stats
    stats_path = DATASET_DIR / "split_stats.json"
    with open(stats_path, "w") as f:
        json.dump({
            "generated": datetime.now().isoformat(),
            "imgsz": DATASET_IMGSZ,
            "val_split": VAL_SPLIT,
            "max_per_class": MAX_CROPS_PER_SPECIES,
            "total_train": total_train,
            "total_val": total_val,
            "species": split_stats,
        }, f, indent=2)


# ============================================================================
# MAIN PIPELINE
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Build NestVision classification dataset v2",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python NestVision/build_dataset_v2.py                  # Full pipeline, all tiers
  python NestVision/build_dataset_v2.py --tiers 1,2      # Conservative (skip Tier 3)
  python NestVision/build_dataset_v2.py --step 4         # Resume from crop extraction
  python NestVision/build_dataset_v2.py --conf 0.5       # Stricter detection confidence
  python NestVision/build_dataset_v2.py --fresh          # Wipe caches and start over
        """
    )
    parser.add_argument(
        "--step", type=int, default=0,
        help="Resume from this step (1-5). 0 = run all."
    )
    parser.add_argument(
        "--conf", type=float, default=DETECTION_CONF,
        help=f"Detection confidence threshold (default: {DETECTION_CONF})"
    )
    parser.add_argument(
        "--tiers", type=str, default="1,2,3",
        help="Comma-separated list of tiers to use (default: 1,2,3)"
    )
    parser.add_argument(
        "--fresh", action="store_true",
        help="Delete cached mappings and crop progress to start fresh"
    )
    args = parser.parse_args()

    det_conf = args.conf
    active_tiers = [int(t.strip()) for t in args.tiers.split(",")]

    # Wipe caches if --fresh
    if args.fresh:
        for f in [MAPPINGS_CACHE, STATE_FILE,
                  CROPS_DIR / "extraction_progress.json"]:
            if f.exists():
                f.unlink()
                print(f"  Deleted {f.name}")
        if CROPS_DIR.exists():
            shutil.rmtree(CROPS_DIR)
            print(f"  Deleted {CROPS_DIR.name}/")

    print("=" * 70)
    print("NestVision Classification Dataset Builder v2")
    print("=" * 70)
    print(f"  Active tiers:       {active_tiers}")
    print(f"  Detection model:    Swift (detect only, no classifier)")
    print(f"  Detection conf:     {det_conf}")
    print(f"  Min crop pixels:    {MIN_CROP_PX}px (below = pixel noise)")
    print(f"  Crop padding:       {int(CROP_PADDING * 100)}% on each side")
    print(f"  Crop cap/species:   {MAX_CROPS_PER_SPECIES}")
    print(f"  Dataset image size: {DATASET_IMGSZ}")
    print(f"  Output:             {DATASET_DIR}")

    state = load_state()
    start_step = args.step if args.step > 0 else 1

    # STEP 1: Query database with tiered confidence
    if start_step <= 1:
        photos = query_photos_tiered(tiers=active_tiers)
        state["n_photos_queried"] = len(photos)
        state["tiers_used"] = active_tiers
        mark_step_done(state, 1)
    else:
        print(f"\n  [Skipping to step {start_step}, re-querying database...]")
        photos = query_photos_tiered(tiers=active_tiers)

    # STEP 2: Map to S3 paths
    if start_step <= 2:
        photos = build_all_mappings(photos)
        state["n_photos_mapped"] = len(photos)
        mark_step_done(state, 2)
    else:
        photos = build_all_mappings(photos)

    # STEP 3: Download images
    if start_step <= 3:
        download_images(photos)
        mark_step_done(state, 3)

    # STEP 4: Extract crops
    if start_step <= 4:
        progress = extract_crops(photos, det_conf=det_conf)
        mark_step_done(state, 4)
    else:
        progress_file = CROPS_DIR / "extraction_progress.json"
        if progress_file.exists():
            with open(progress_file) as f:
                progress = json.load(f)
        else:
            progress = extract_crops(photos, det_conf=det_conf)

    # STEP 5: Build dataset
    if start_step <= 5:
        build_dataset(progress)
        mark_step_done(state, 5)

    print("\n" + "=" * 70)
    print("PIPELINE COMPLETE!")
    print(f"Next steps:")
    print(f"  1. python NestVision/clean_dataset.py --data {DATASET_DIR}")
    print(f"  2. python NestVision/train_classifier.py --data {DATASET_DIR}_clean --mode both")
    print("=" * 70)
    save_state(state)


if __name__ == "__main__":
    main()
