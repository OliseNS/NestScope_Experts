"""
Wikipedia/Wikimedia Commons Image Fetcher - Version 2

Uses Wikimedia Commons search API directly to find bird images.
This is more reliable than querying English Wikipedia pages.

Educational Note:
-----------------
Why search Commons directly?
- Wikimedia Commons is the central repository for all Wikipedia images
- Searching Commons directly is more reliable than page-based queries
- We can search by both common and scientific names
- Returns actual image URLs that work in <img> tags
"""

import requests
from typing import List, Dict, Optional
from urllib.parse import quote

# Wikipedia requires User-Agent identification
HEADERS = {
    "User-Agent": "NestScope/1.0 (Educational bird monitoring project; contact: admin@nestscope.org)"
}


def search_commons_images(search_query: str, max_results: int = 3) -> List[str]:
    """
    Search Wikimedia Commons for images matching a query.

    Uses the Commons API search to find images, then constructs direct URLs.

    Args:
        search_query: Search term (e.g., "Brown Pelican" or "Pelecanus occidentalis")
        max_results: Maximum number of images to return

    Returns:
        List of direct image URLs from Wikimedia Commons
    """
    try:
        api_url = "https://commons.wikimedia.org/w/api.php"

        # Search for files on Commons
        params = {
            "action": "query",
            "format": "json",
            "formatversion": "2",
            "generator": "search",  # Use search generator
            "gsrsearch": f"{search_query} filetype:bitmap",  # Search for bitmap images
            "gsrnamespace": "6",  # Namespace 6 = File
            "gsrlimit": max_results + 5,  # Get extra to filter
            "prop": "imageinfo",  # Get image information
            "iiprop": "url|size",  # Get URL and dimensions
            "iiurlwidth": "800"  # Get 800px wide version
        }

        response = requests.get(api_url, params=params, headers=HEADERS, timeout=10)
        response.raise_for_status()
        data = response.json()

        # Extract image URLs
        image_urls = []
        pages = data.get("query", {}).get("pages", [])

        for page in pages:
            if "imageinfo" in page and page["imageinfo"]:
                info = page["imageinfo"][0]

                # Get thumb URL (good size for display)
                if "thumburl" in info:
                    image_urls.append(info["thumburl"])
                # Fallback to full URL
                elif "url" in info:
                    image_urls.append(info["url"])

                if len(image_urls) >= max_results:
                    break

        if image_urls:
            print(f"✓ Found {len(image_urls)} Commons images for '{search_query}'")
        else:
            print(f"⚠️  No Commons images found for '{search_query}'")

        return image_urls

    except Exception as e:
        print(f"❌ Error searching Commons for '{search_query}': {e}")
        return []


def get_wikipedia_page_image(species_name: str) -> Optional[str]:
    """
    Get the main image from a Wikipedia article.

    Uses the Wikipedia API to find the primary article image,
    then constructs a direct URL.

    Args:
        species_name: Common name (e.g., "Brown Pelican")

    Returns:
        Direct image URL or None
    """
    try:
        api_url = "https://en.wikipedia.org/w/api.php"
        page_title = species_name.replace(" ", "_")

        # Get page info with thumbnail
        params = {
            "action": "query",
            "format": "json",
            "formatversion": "2",
            "titles": page_title,
            "prop": "pageimages|pageterms",
            "piprop": "thumbnail|original",
            "pithumbsize": 800  # Get large thumbnail
        }

        response = requests.get(api_url, params=params, headers=HEADERS, timeout=10)
        response.raise_for_status()
        data = response.json()

        pages = data.get("query", {}).get("pages", [])
        if pages and "thumbnail" in pages[0]:
            thumbnail_url = pages[0]["thumbnail"]["source"]
            print(f"✓ Found Wikipedia page image for '{species_name}'")
            return thumbnail_url

        print(f"⚠️  No Wikipedia page image for '{species_name}'")
        return None

    except Exception as e:
        print(f"❌ Error getting Wikipedia image for '{species_name}': {e}")
        return None


def get_wikipedia_images(species_name: str, max_images: int = 3, offset: int = 0) -> List[str]:
    """
    Get reference images for a bird species with pagination support.

    Strategy:
    1. Try to get Wikipedia article main image (usually best quality)
    2. Search Wikimedia Commons for additional images
    3. Combine results
    4. Support offset for "Load More" functionality

    Args:
        species_name: Common name of bird (e.g., "Brown Pelican")
        max_images: Maximum number of images to return
        offset: Number of images to skip (for pagination)

    Returns:
        List of direct image URLs
    """
    # Fetch a larger batch to support pagination
    fetch_limit = offset + max_images + 10  # Get extra for filtering
    all_images = []

    # Strategy 1: Get main Wikipedia article image (only on first page)
    if offset == 0:
        wiki_image = get_wikipedia_page_image(species_name)
        if wiki_image:
            all_images.append(wiki_image)

    # Strategy 2: Search Commons for more images
    # We need to fetch more than needed because some might be filtered
    commons_images = search_commons_images(species_name, max_results=fetch_limit)

    # Avoid duplicates
    for img in commons_images:
        if img not in all_images:
            all_images.append(img)

    # Apply pagination (skip offset, take max_images)
    paginated_images = all_images[offset:offset + max_images]

    return paginated_images


def test_species_images(species_name: str):
    """Test image fetching for a species"""
    print(f"\n{'='*60}")
    print(f"Testing: {species_name}")
    print(f"{'='*60}")

    images = get_wikipedia_images(species_name, max_images=3)

    if images:
        print(f"\n✅ Found {len(images)} images:")
        for i, url in enumerate(images, 1):
            print(f"   {i}. {url[:80]}...")
    else:
        print("\n❌ No images found")

    return images


if __name__ == "__main__":
    # Test with real species
    test_species = [
        "Brown Pelican",
        "Great Egret",
        "Roseate Spoonbill",
    ]

    print("🧪 WIKIPEDIA COMMONS IMAGE API TEST")
    print("="*60)

    for species in test_species:
        test_species_images(species)
        print()

    print("\n✅ Test complete!")
