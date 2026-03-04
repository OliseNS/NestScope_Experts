"""
STAC Client for The Water Institute Avian Monitoring Catalog
============================================================

Provides cached access to the TWI STAC catalog hosted at:
  https://twi-avian-2024.s3.us-east-1.amazonaws.com/public/test_stac/

Data structure:
  - 4 colonies with georeferenced COG mosaics (2015–2021)
  - Expert-annotated species dot GeoJSONs (43,000+ labeled points, 19 species)
  - 2024 unprocessed mosaics in devDays (Queen Bess Island, East Timbalier)

All S3 fetches are cached in-memory with a 1-hour TTL to avoid
hammering the public S3 bucket during demos.
"""

import requests
import time
from functools import lru_cache
from typing import Optional

# ============================================================================
# S3 BASE URLS
# ============================================================================

BASE_S3 = "https://twi-avian-2024.s3.us-east-1.amazonaws.com/public"
SPECIES_TOTALS_URL = f"{BASE_S3}/mosaics/species_totals_summary.json"

# ============================================================================
# COLONY METADATA
# Hard-coded from STAC catalog bbox centroids — avoids an extra S3 fetch at startup
# ============================================================================

COLONIES: dict = {
    "QueenBessIsland": {
        "display_name": "Queen Bess Island",
        "region": "BaratariaBay",
        "lat": 29.3037,
        "lon": -89.9597,
        "years": ["2015", "2018", "2021"],
        "months": {"2015": "May", "2018": "May", "2021": "May"},
        "description": "Barataria Bay, Louisiana — primary Brown Pelican nesting colony, restored after Deepwater Horizon",
    },
    "NewHarborIsland2": {
        "display_name": "New Harbor Island 2",
        "region": "BretonChandeleurIslands",
        "lat": 29.8564,
        "lon": -88.8748,
        "years": ["2021"],
        "months": {"2021": "June"},
        "description": "Breton-Chandeleur Islands, Louisiana — remote island Brown Pelican colony",
    },
    "NewHarborIsland3": {
        "display_name": "New Harbor Island 3",
        "region": "BretonChandeleurIslands",
        "lat": 29.8545,
        "lon": -88.8637,
        "years": ["2021"],
        "months": {"2021": "June"},
        "description": "Breton-Chandeleur Islands, Louisiana — large mixed colony with BRPE, GREG, LAGU",
    },
    "PepperfishKey": {
        "display_name": "Pepperfish Key",
        "region": "ApalacheeBay",
        "lat": 29.5012,
        "lon": -83.3954,
        "years": ["2021"],
        "months": {"2021": "May"},
        "description": "Apalachee Bay, Florida — diverse colony with AWPE, GBHE, GREG, SNEG, TRHE",
    },
}

# ============================================================================
# SPECIES METADATA
# Full names + colors for UI display
# ============================================================================

SPECIES_INFO: dict = {
    "BRPE": {"name": "Brown Pelican",             "color": "#D97757"},
    "LAGU": {"name": "Laughing Gull",             "color": "#2EC46A"},
    "ROYT": {"name": "Royal Tern",                "color": "#2AB8DC"},
    "SATE": {"name": "Sandwich Tern",             "color": "#6AC4DC"},
    "AWPE": {"name": "American White Pelican",    "color": "#B0B0B0"},
    "BLSK": {"name": "Black Skimmer",             "color": "#505050"},
    "DCCO": {"name": "Double-crested Cormorant",  "color": "#707070"},
    "GREG": {"name": "Great Egret",               "color": "#E0E0E0"},
    "WHIB": {"name": "White Ibis",                "color": "#F0F0F0"},
    "TRHE": {"name": "Tricolored Heron",          "color": "#C878DC"},
    "ROSP": {"name": "Roseate Spoonbill",         "color": "#F080C0"},
    "SNEG": {"name": "Snowy Egret",               "color": "#D0D0FF"},
    "BCNH": {"name": "Black-crowned Night Heron", "color": "#907050"},
    "CAEG": {"name": "Cattle Egret",              "color": "#F0F0A0"},
    "GBHE": {"name": "Great Blue Heron",          "color": "#8090A0"},
    "AMAV": {"name": "American Avocet",           "color": "#F0A030"},
    "AMOY": {"name": "American Oystercatcher",    "color": "#E04040"},
    "GBTE": {"name": "Gull-billed Tern",          "color": "#A0D0E0"},
    "HERG": {"name": "Herring Gull",              "color": "#C0C080"},
}

# Dot types supported in the STAC catalog
DOT_TYPES = ["Bird", "Nest", "CN", "CNWA", "WBN", "PBN", "Empty", "Abandoned", "Territory"]

# ============================================================================
# IN-MEMORY TTL CACHE
# ============================================================================

_cache: dict = {}
_CACHE_TTL = 3600  # 1 hour


def _cache_get(key: str):
    entry = _cache.get(key)
    if entry and (time.time() - entry["ts"]) < _CACHE_TTL:
        return entry["data"]
    return None


def _cache_set(key: str, data):
    _cache[key] = {"data": data, "ts": time.time()}


def _fetch_json(url: str, timeout: int = 10) -> Optional[dict]:
    """Fetch JSON from a URL with caching and error handling."""
    cached = _cache_get(url)
    if cached is not None:
        return cached
    try:
        r = requests.get(url, timeout=timeout)
        r.raise_for_status()
        data = r.json()
        _cache_set(url, data)
        return data
    except Exception as e:
        print(f"[STAC] Failed to fetch {url}: {e}")
        return None


# ============================================================================
# PUBLIC API
# ============================================================================

def get_species_totals() -> dict:
    """
    Fetch the species totals summary from S3.

    Returns nested dict: {species_code: {region: {colony: {year: {total_birds, total_nests}}}}}
    """
    data = _fetch_json(SPECIES_TOTALS_URL)
    return data or {}


def get_colony_list() -> list:
    """
    Return list of all colony metadata dicts enriched with species totals.

    Each dict contains:
      id, display_name, region, lat, lon, years, months, description,
      dominant_species (code of species with most birds in latest year),
      total_birds_latest (sum across species in latest year)
    """
    totals = get_species_totals()
    result = []
    for colony_id, meta in COLONIES.items():
        colony_info = dict(meta)
        colony_info["id"] = colony_id

        # Calculate total birds and dominant species for latest year
        latest_year = max(meta["years"])
        total_birds = 0
        dominant_species = None
        dominant_count = 0

        for species_code, regions in totals.items():
            region_data = regions.get(meta["region"], {})
            colony_data = region_data.get(colony_id, {})
            year_data = colony_data.get(latest_year, {})
            birds = year_data.get("total_birds", 0)
            total_birds += birds
            if birds > dominant_count:
                dominant_count = birds
                dominant_species = species_code

        colony_info["total_birds_latest"] = total_birds
        colony_info["dominant_species"] = dominant_species
        colony_info["dominant_species_name"] = SPECIES_INFO.get(dominant_species, {}).get("name", dominant_species) if dominant_species else "Unknown"
        result.append(colony_info)

    return result


def get_colony_species_breakdown(colony_id: str, year: str) -> list:
    """
    Return species breakdown for a colony-year as a sorted list.

    Each item: {code, name, total_birds, total_nests, color}
    """
    meta = COLONIES.get(colony_id)
    if not meta:
        return []

    totals = get_species_totals()
    breakdown = []

    for species_code, regions in totals.items():
        region_data = regions.get(meta["region"], {})
        colony_data = region_data.get(colony_id, {})
        year_data = colony_data.get(year, {})
        birds = year_data.get("total_birds", 0)
        nests = year_data.get("total_nests", 0)

        if birds > 0 or nests > 0:
            info = SPECIES_INFO.get(species_code, {})
            breakdown.append({
                "code": species_code,
                "name": info.get("name", species_code),
                "color": info.get("color", "#888888"),
                "total_birds": birds,
                "total_nests": nests,
            })

    # Sort by total_birds descending
    breakdown.sort(key=lambda x: -x["total_birds"])
    return breakdown


def get_colony_dots(colony_id: str, year: str, species_code: str, dot_type: str = "Bird") -> dict:
    """
    Fetch species dot GeoJSON for a colony-year-species combination.

    Returns the GeoJSON FeatureCollection dict, or empty FeatureCollection on error.
    """
    meta = COLONIES.get(colony_id)
    if not meta:
        return {"type": "FeatureCollection", "features": []}

    url = build_dots_url(meta["region"], colony_id, year, species_code, dot_type)
    data = _fetch_json(url, timeout=15)
    if data is None:
        return {"type": "FeatureCollection", "features": []}
    return data


def build_mosaic_url(colony_id: str, year: str) -> Optional[str]:
    """
    Build the S3 URL for a colony's COG mosaic.

    Returns None if the colony or year is not in COLONIES metadata.
    """
    meta = COLONIES.get(colony_id)
    if not meta or year not in meta["years"]:
        return None
    month = meta["months"].get(year, "May")
    return f"{BASE_S3}/mosaics/{meta['region']}/{colony_id}/{year}/{month}_cog.tif"


def build_dots_url(region: str, colony_id: str, year: str, species_code: str, dot_type: str = "Bird") -> str:
    """Build S3 URL for a species dot GeoJSON."""
    return f"{BASE_S3}/mosaics/{region}/{colony_id}/{year}/{species_code}-{dot_type}_dots.json"


def get_available_species_for_colony_year(colony_id: str, year: str) -> list:
    """
    Return list of species codes that have dot data for a colony-year.
    Uses the species_totals_summary to determine which species are present.
    """
    breakdown = get_colony_species_breakdown(colony_id, year)
    return [item["code"] for item in breakdown if item["total_birds"] > 0]
