"""
Wikimedia Commons Image Fetcher for Bird Species

Uses Wikimedia Commons API to fetch high-quality bird photos.
More reliable than Macaulay Library and completely open/free.

API Docs: https://www.mediawiki.org/wiki/API:Main_page
Commons Search: https://commons.wikimedia.org/wiki/Special:Search
"""

import requests
from typing import List, Dict, Optional
import time


class WikimediaImageFetcher:
    """
    Fetch bird images from Wikimedia Commons using their API.
    """

    BASE_URL = "https://commons.wikimedia.org/w/api.php"

    # Mapping of our species codes to Wikimedia Commons search terms
    SPECIES_SEARCH_TERMS = {
        "BRPE": "Brown Pelican Pelecanus occidentalis",
        "GREG": "Great Egret Ardea alba",
        "SNEG": "Snowy Egret Egretta thula",
        "DCCO": "Double-crested Cormorant Phalacrocorax auritus",
        "NECO": "Neotropic Cormorant Phalacrocorax brasilianus",
        "LAGU": "Laughing Gull Leucophaeus atricilla",
        "ROYT": "Royal Tern Thalasseus maximus",
        "BLSK": "Black Skimmer Rynchops niger",
        "AWPE": "American White Pelican Pelecanus erythrorhynchos",
        "ROSP": "Roseate Spoonbill Platalea ajaja",
        "WHIB": "White Ibis Eudocimus albus",
        "WFIB": "White-faced Ibis Plegadis chihi",
        "GBHE": "Great Blue Heron Ardea herodias",
        "LBHE": "Little Blue Heron Egretta caerulea",
        "TRHE": "Tricolored Heron Egretta tricolor",
        "BCNH": "Black-crowned Night Heron Nycticorax nycticorax",
        "YCNH": "Yellow-crowned Night Heron Nyctanassa violacea",
        "REEG": "Reddish Egret Egretta rufescens",
        "CAEG": "Cattle Egret Bubulcus ibis",
        "ANHI": "Anhinga Anhinga anhinga",
        "WOST": "Wood Stork Mycteria americana",
        "MAFR": "Magnificent Frigatebird Fregata magnificens",
        "HERG": "Herring Gull Larus argentatus",
        "CATE": "Caspian Tern Hydroprogne caspia",
        "SATE": "Sandwich Tern Thalasseus sandvicensis",
        "GBTE": "Gull-billed Tern Gelochelidon nilotica",
        "ROST": "Roseate Tern Sterna dougallii",
        "COTE": "Common Tern Sterna hirundo",
        "FOTE": "Forster's Tern Sterna forsteri",
        "LETE": "Least Tern Sternula antillarum",
        "BLTE": "Black Tern Chlidonias niger",
        "SOTE": "Sooty Tern Onychoprion fuscatus",
        "BRNO": "Brown Noddy Anous stolidus",
        "AMOY": "American Oystercatcher Haematopus palliatus",
        "AMAV": "American Avocet Recurvirostra americana",
        "BNST": "Black-necked Stilt Himantopus mexicanus",
        "RUTU": "Ruddy Turnstone Arenaria interpres",
        "OSPR": "Osprey Pandion haliaetus",
        "CRCA": "Crested Caracara Caracara plancus",
    }

    # Species that look similar (for "Similar Birds" feature)
    SIMILAR_SPECIES = {
        "BRPE": ["AWPE"],  # Brown vs American White Pelican
        "AWPE": ["BRPE"],
        "GREG": ["SNEG", "CAEG"],  # White egrets
        "SNEG": ["GREG", "CAEG"],
        "CAEG": ["GREG", "SNEG"],
        "DCCO": ["NECO", "ANHI"],  # Dark water birds
        "NECO": ["DCCO", "ANHI"],
        "ANHI": ["DCCO", "NECO"],
        "GBHE": ["LBHE", "TRHE"],  # Herons
        "LBHE": ["GBHE", "TRHE"],
        "TRHE": ["GBHE", "LBHE"],
        "BCNH": ["YCNH"],  # Night herons
        "YCNH": ["BCNH"],
        "WHIB": ["WFIB", "ROSP"],  # Long-billed waders
        "WFIB": ["WHIB"],
        "ROSP": ["WHIB"],
        "ROYT": ["CATE", "SATE"],  # Large terns
        "CATE": ["ROYT", "SATE"],
        "SATE": ["ROYT", "CATE"],
        "COTE": ["FOTE", "LETE"],  # Small terns
        "FOTE": ["COTE", "LETE"],
        "LETE": ["COTE", "FOTE"],
        "LAGU": ["HERG"],  # Gulls
        "HERG": ["LAGU"],
    }

    @classmethod
    def fetch_images(cls, species_code: str, limit: int = 10) -> List[str]:
        """
        Fetch image URLs from Wikimedia Commons for a species.

        Args:
            species_code: 4-letter species code (e.g., "BRPE")
            limit: Maximum number of images to fetch

        Returns:
            List of image URLs (direct links to images)
        """
        search_term = cls.SPECIES_SEARCH_TERMS.get(species_code)
        if not search_term:
            print(f"⚠️ No search term for species: {species_code}")
            return []

        print(f"🔍 Searching Wikimedia Commons for: {search_term}")

        try:
            # Step 1: Search for images
            search_params = {
                "action": "query",
                "format": "json",
                "list": "search",
                "srsearch": f"filetype:bitmap|drawing {search_term}",
                "srnamespace": "6",  # File namespace
                "srlimit": limit * 2,  # Get extra in case some fail
                "srinfo": "totalhits",
                "srprop": "size|wordcount|timestamp"
            }

            response = requests.get(cls.BASE_URL, params=search_params, timeout=10)
            response.raise_for_status()
            data = response.json()

            if "query" not in data or "search" not in data["query"]:
                print(f"❌ No results for {species_code}")
                return []

            # Step 2: Get image URLs for each file
            image_urls = []
            for result in data["query"]["search"][:limit]:
                file_title = result["title"]
                image_url = cls._get_image_url(file_title)
                if image_url:
                    image_urls.append(image_url)

                # Be nice to the API
                time.sleep(0.1)

            print(f"✅ Found {len(image_urls)} images for {species_code}")
            return image_urls[:limit]

        except Exception as e:
            print(f"❌ Error fetching images for {species_code}: {e}")
            return []

    @classmethod
    def _get_image_url(cls, file_title: str) -> Optional[str]:
        """
        Get direct image URL from file title.

        Args:
            file_title: Wikimedia file title (e.g., "File:Brown Pelican.jpg")

        Returns:
            Direct URL to image, or None if failed
        """
        try:
            params = {
                "action": "query",
                "format": "json",
                "titles": file_title,
                "prop": "imageinfo",
                "iiprop": "url|size",
                "iiurlwidth": "1200"  # Request 1200px width (high quality)
            }

            response = requests.get(cls.BASE_URL, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            pages = data.get("query", {}).get("pages", {})
            for page_id, page_data in pages.items():
                if "imageinfo" in page_data and len(page_data["imageinfo"]) > 0:
                    # Prefer thumbnail URL, fall back to original
                    image_info = page_data["imageinfo"][0]
                    return image_info.get("thumburl", image_info.get("url"))

            return None

        except Exception as e:
            print(f"⚠️ Failed to get URL for {file_title}: {e}")
            return None

    @classmethod
    def get_similar_species(cls, species_code: str) -> List[str]:
        """
        Get list of visually similar species codes.

        Args:
            species_code: Species to find similar species for

        Returns:
            List of similar species codes
        """
        return cls.SIMILAR_SPECIES.get(species_code, [])


# Cache for fetched images (avoid repeated API calls)
_IMAGE_CACHE: Dict[str, List[str]] = {}


def get_species_images(species_code: str, limit: int = 10, use_cache: bool = True) -> List[str]:
    """
    Get images for a species (with caching).

    Args:
        species_code: 4-letter species code
        limit: Number of images to fetch
        use_cache: Whether to use cached results

    Returns:
        List of image URLs
    """
    cache_key = f"{species_code}_{limit}"

    if use_cache and cache_key in _IMAGE_CACHE:
        print(f"📦 Using cached images for {species_code}")
        return _IMAGE_CACHE[cache_key]

    images = WikimediaImageFetcher.fetch_images(species_code, limit)
    _IMAGE_CACHE[cache_key] = images

    return images


def get_similar_species_images(species_code: str, images_per_species: int = 3) -> Dict[str, Dict]:
    """
    Get images for visually similar species (for comparison).

    Args:
        species_code: Species to compare against
        images_per_species: Number of images per similar species

    Returns:
        Dict mapping species codes to their images and names
    """
    similar_codes = WikimediaImageFetcher.get_similar_species(species_code)

    result = {}
    for code in similar_codes:
        images = get_species_images(code, limit=images_per_species)
        if images:
            search_term = WikimediaImageFetcher.SPECIES_SEARCH_TERMS.get(code, code)
            # Extract common name (first part before scientific name)
            name = search_term.split(" Pelecanus")[0].split(" Ardea")[0].split(" Egretta")[0]
            name = name.split(" Phalacrocorax")[0].split(" Leucophaeus")[0].split(" Thalasseus")[0]

            result[code] = {
                "name": name,
                "images": images
            }

    return result


if __name__ == "__main__":
    # Test the fetcher
    print("🧪 Testing Wikimedia Image Fetcher\n")

    test_species = ["BRPE", "GREG", "SNEG"]

    for species in test_species:
        print(f"\n{'='*60}")
        print(f"Testing: {species}")
        print('='*60)

        images = get_species_images(species, limit=5)
        print(f"\nFetched {len(images)} images:")
        for i, url in enumerate(images, 1):
            print(f"  {i}. {url[:80]}...")

        # Test similar species
        similar = WikimediaImageFetcher.get_similar_species(species)
        if similar:
            print(f"\nSimilar species: {', '.join(similar)}")
