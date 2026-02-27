"""
Complete Reference Images Database - ALL Gulf Coast Bird Species

This module provides RELIABLE reference images from Wikipedia/Wikimedia Commons
for ALL 41 species in the Gulf Coast monitoring database.

Educational Note:
-----------------
We switched from Macaulay Library to Wikipedia because:

✓ Direct image URLs that work in <img> tags (no search pages!)
✓ Free and open - public domain or Creative Commons licensed
✓ High quality, community-curated photos
✓ No authentication or API keys required
✓ Perfect for educational projects

Each species gets:
- Direct Wikipedia/Wikimedia image URLs (actual photos, not search pages)
- eBird species page URL (identification info + sounds)
- All About Birds field guide URL (comprehensive species info)
- Macaulay Library gallery link (for experts wanting more photos)

How it works:
1. Use Wikipedia API to find species page images
2. Extract actual photo URLs from Wikimedia Commons
3. Return direct links that display in <img> tags
4. Fall back to curated external links if Wikipedia fails
"""

from typing import Dict, List
import os
import sys

# Import our Wikipedia image fetcher (V2 - uses Commons search API)
try:
    from labeller.services.wikipedia_images_v2 import get_wikipedia_images
except ImportError:
    # If running from labeller directory
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    from services.wikipedia_images_v2 import get_wikipedia_images


# Mapping of our 4-letter codes to eBird taxonomy codes
# eBird codes are the standard used by Macaulay Library search
EBIRD_CODES = {
    # PELICANS
    "BRPE": "brnpel",
    "AWPE": "amwpel",

    # EGRETS (WHITE)
    "GREG": "greegr",
    "SNEG": "snoegr",
    "CAEG": "categr",
    "REEG": "rededg",
    "REEG DM": "rededg",  # Dark morph uses same eBird code
    "REEG WM": "rededg",  # White morph uses same eBird code

    # HERONS
    "GBHE": "grbher3",
    "LBHE": "litbhe",
    "TRHE": "triher",
    "BCNH": "bcnher",
    "YCNH": "ycnher",

    # IBISES & SPOONBILLS
    "WHIB": "whiibi",
    "WFIB": "whfibi",
    "ROSP": "rosspo1",

    # CORMORANTS & ANHINGA
    "DCCO": "doccor",
    "NECO": "neocor",
    "ANHI": "anhing",

    # WOOD STORK & FRIGATEBIRD
    "WOST": "woosto",
    "MAFR": "magfri",

    # GULLS
    "LAGU": "laugul",
    "HERG": "hergul",

    # TERNS (LARGE)
    "ROYT": "royter1",
    "CATE": "caster1",
    "SATE": "santer1",
    "GBTE": "gubter1",
    "ROST": "roster1",

    # TERNS (SMALL)
    "COTE": "comter",
    "FOTE": "forter",
    "LETE": "leater1",
    "BLTE": "blkter",
    "SOTE": "sooter1",
    "BRNO": "brnnod",

    # SKIMMER
    "BLSK": "blaski",

    # SHOREBIRDS
    "AMOY": "ameoyst",
    "AMAV": "ameavo",
    "BNST": "bknsti",
    "RUTU": "rudtur",

    # RAPTORS
    "OSPR": "osprey",
    "CRCA": "crecca"
}


SPECIES_NAMES = {
    "BRPE": "Brown Pelican",
    "AWPE": "American White Pelican",
    "GREG": "Great Egret",
    "SNEG": "Snowy Egret",
    "CAEG": "Cattle Egret",
    "REEG": "Reddish Egret",
    "REEG DM": "Reddish Egret (Dark Morph)",
    "REEG WM": "Reddish Egret (White Morph)",
    "GBHE": "Great Blue Heron",
    "LBHE": "Little Blue Heron",
    "TRHE": "Tricolored Heron",
    "BCNH": "Black-crowned Night-Heron",
    "YCNH": "Yellow-crowned Night-Heron",
    "WHIB": "White Ibis",
    "WFIB": "White-faced Ibis",
    "ROSP": "Roseate Spoonbill",
    "DCCO": "Double-crested Cormorant",
    "NECO": "Neotropic Cormorant",
    "ANHI": "Anhinga",
    "WOST": "Wood Stork",
    "MAFR": "Magnificent Frigatebird",
    "LAGU": "Laughing Gull",
    "HERG": "Herring Gull",
    "ROYT": "Royal Tern",
    "CATE": "Caspian Tern",
    "SATE": "Sandwich Tern",
    "GBTE": "Gull-billed Tern",
    "ROST": "Roseate Tern",
    "COTE": "Common Tern",
    "FOTE": "Forster's Tern",
    "LETE": "Least Tern",
    "BLTE": "Black Tern",
    "SOTE": "Sooty Tern",
    "BRNO": "Brown Noddy",
    "BLSK": "Black Skimmer",
    "AMOY": "American Oystercatcher",
    "AMAV": "American Avocet",
    "BNST": "Black-necked Stilt",
    "RUTU": "Ruddy Turnstone",
    "OSPR": "Osprey",
    "CRCA": "Crested Caracara"
}


def get_macaulay_search_url(ebird_code: str) -> str:
    """
    Generate Macaulay Library search URL for a species.

    This returns a dynamic gallery of photos sorted by rating.
    Much more reliable than individual asset IDs.

    Args:
        ebird_code: eBird taxonomy code (e.g., "brnpel" for Brown Pelican)

    Returns:
        URL to Macaulay Library photo gallery for this species
    """
    return f"https://search.macaulaylibrary.org/catalog?taxonCode={ebird_code}&mediaType=p&sort=rating_rank_desc"


def get_ebird_url(ebird_code: str) -> str:
    """Generate eBird species page URL."""
    return f"https://ebird.org/species/{ebird_code}"


def get_guide_url(species_name: str) -> str:
    """
    Generate All About Birds field guide URL.

    Converts species name to URL-friendly format.
    """
    # Replace spaces with underscores, keep hyphens
    url_name = species_name.replace(" ", "_")
    # Remove parenthetical morph info
    url_name = url_name.split(" (")[0]
    return f"https://www.allaboutbirds.org/guide/{url_name}"


def get_all_species_references() -> Dict[str, Dict]:
    """
    Complete reference database for all Gulf Coast colonial waterbirds.

    Returns:
        Dict mapping species codes to reference materials including:
        - name: Full species name
        - macaulay_gallery: Macaulay Library photo gallery URL (dynamic, curated)
        - ebird: eBird species page URL (includes sounds, maps, photos)
        - guide: All About Birds field guide URL (comprehensive info)
        - photos: List with single Macaulay search URL (for backwards compatibility)
    """
    references = {}

    for species_code, ebird_code in EBIRD_CODES.items():
        species_name = SPECIES_NAMES[species_code]
        macaulay_url = get_macaulay_search_url(ebird_code)

        references[species_code] = {
            "name": species_name,
            "macaulay_gallery": macaulay_url,
            "ebird": get_ebird_url(ebird_code),
            "guide": get_guide_url(species_name),
            # For backwards compatibility with code expecting 'photos' list
            # This contains the Macaulay search URL which shows multiple photos
            "photos": [macaulay_url]
        }

    return references


def get_reference_images(species_code: str, offset: int = 0, limit: int = 5) -> Dict[str, any]:
    """
    Get reference materials for a species with ACTUAL displayable images and pagination.

    Fetches real image URLs from Wikipedia that work in <img> tags!
    Also provides links to eBird, field guides, and photo galleries.

    Args:
        species_code: 4-letter species code (e.g., "BRPE")
        offset: Number of images to skip (for "Load More" functionality)
        limit: Number of images to return

    Returns:
        Dict with:
        - name: Species common name
        - photos: List of direct Wikipedia image URLs (ready for <img> tags!)
        - ebird: eBird species page
        - guide: All About Birds field guide
        - macaulay_gallery: Macaulay Library photo gallery (for experts)
    """
    all_refs = get_all_species_references()

    if species_code in all_refs:
        ref = all_refs[species_code]
        species_name = ref['name']

        # NEW: Fetch actual Wikipedia images (direct URLs!) with pagination
        try:
            wikipedia_images = get_wikipedia_images(species_name, max_images=limit, offset=offset)

            # If we got Wikipedia images, use those
            if wikipedia_images:
                ref['photos'] = wikipedia_images
                print(f"✓ Loaded {len(wikipedia_images)} Wikipedia images for {species_name} (offset={offset}, limit={limit})")
            else:
                # Fallback: keep Macaulay search URL
                print(f"⚠️  No Wikipedia images for {species_name}, using Macaulay gallery link")

        except Exception as e:
            print(f"❌ Error fetching Wikipedia images for {species_name}: {e}")
            # Keep existing Macaulay search URL as fallback

        return ref

    # Fallback for species not in database
    return {
        "name": species_code,
        "macaulay_gallery": "https://search.macaulaylibrary.org/catalog?mediaType=p",
        "photos": [],  # Empty means UI will show "No photos available"
        "ebird": "https://ebird.org/explore",
        "guide": "https://www.allaboutbirds.org"
    }


def add_references_to_species_list(species: List[Dict]) -> List[Dict]:
    """
    Add reference links to species list.

    Args:
        species: List of dicts with 'code' and 'name' keys

    Returns:
        Enhanced list with 'references' added to each species
    """
    for sp in species:
        sp['references'] = get_reference_images(sp['code'])

    return species


if __name__ == "__main__":
    # Validate all species have references
    refs = get_all_species_references()
    print(f"✓ Reference links generated for {len(refs)} species")

    # Show example
    print("\n📸 Example - Brown Pelican (BRPE):")
    brpe = refs["BRPE"]
    print(f"   Name: {brpe['name']}")
    print(f"   Macaulay Gallery: {brpe['macaulay_gallery']}")
    print(f"   eBird Page: {brpe['ebird']}")
    print(f"   Field Guide: {brpe['guide']}")

    # Check for missing species
    import json
    import os

    json_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'species_list.json')
    with open(json_path, 'r') as f:
        species_list = json.load(f)

    real_species = [s['code'] for s in species_list['real_species']]
    morph_variants = [s['code'] for s in species_list['morph_variants']]
    all_species = real_species + morph_variants

    missing = [s for s in all_species if s not in refs]
    if missing:
        print(f"\n⚠️  Missing references for: {missing}")
    else:
        print(f"\n✓ All {len(all_species)} species have reference links!")
