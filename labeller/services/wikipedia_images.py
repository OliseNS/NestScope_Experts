"""
Wikipedia/Wikimedia Commons Image Fetcher

This module fetches bird reference images from Wikipedia using the Wikimedia API.

Educational Note:
-----------------
Why use Wikipedia images?
- ✓ Free and open (public domain or Creative Commons)
- ✓ Direct image URLs that work in <img> tags
- ✓ High quality, community-curated photos
- ✓ No authentication required
- ✓ Great for educational projects

API Flow:
1. Search Wikipedia for species page (e.g., "Brown Pelican")
2. Extract image filenames from the page
3. Build direct Wikimedia Commons URLs
4. Return up to 3 images per species

API Documentation:
https://www.mediawiki.org/wiki/API:Images
"""

import requests
from typing import List, Dict, Optional
from urllib.parse import quote

# IMPORTANT: Wikipedia requires a User-Agent header
# This identifies our app and helps them monitor API usage
# See: https://meta.wikimedia.org/wiki/User-Agent_policy
HEADERS = {
    "User-Agent": "NestScope/1.0 (Educational bird monitoring project; https://github.com/yourusername/nestscope)"
}


def get_wikipedia_images(species_name: str, max_images: int = 3) -> List[str]:
    """
    Fetch reference images for a bird species from Wikipedia/Wikimedia Commons.

    Uses the Wikipedia API to find images associated with a species page,
    then constructs direct image URLs.

    Args:
        species_name: Common name of the bird (e.g., "Brown Pelican")
        max_images: Maximum number of images to return (default: 3)

    Returns:
        List of direct image URLs (empty list if no images found)

    Example:
        >>> get_wikipedia_images("Brown Pelican")
        ['https://commons.wikimedia.org/wiki/Special:FilePath/Brown_Pelican.jpg',
         'https://commons.wikimedia.org/wiki/Special:FilePath/Pelecanus_occidentalis.jpg']
    """
    try:
        # Step 1: Get the Wikipedia page for this species
        # We use the Wikipedia API's "query" action with "prop=images"
        api_url = "https://en.wikipedia.org/w/api.php"

        # Format species name for Wikipedia (spaces → underscores)
        page_title = species_name.replace(" ", "_")

        params = {
            "action": "query",
            "titles": page_title,
            "prop": "images",  # Get all images on the page
            "imlimit": max_images + 5,  # Get a few extra (we'll filter later)
            "format": "json",
            "formatversion": "2"  # Use cleaner JSON format
        }

        response = requests.get(api_url, params=params, headers=HEADERS, timeout=10)
        response.raise_for_status()
        data = response.json()

        # Step 2: Extract image filenames from the response
        pages = data.get("query", {}).get("pages", [])
        if not pages or "missing" in pages[0]:
            print(f"⚠️  No Wikipedia page found for '{species_name}'")
            return []

        images = pages[0].get("images", [])
        if not images:
            print(f"⚠️  No images found on Wikipedia page for '{species_name}'")
            return []

        # Step 3: Build direct image URLs
        # Filter out non-photo files (SVG icons, logos, etc.)
        image_urls = []
        for img in images:
            filename = img.get("title", "")

            # Skip non-photo files (commons icons, flags, etc.)
            if any(skip in filename.lower() for skip in [
                "commons-logo", "wikispecies", "wikimedia", "wiki.svg",
                "question_book", "icon", "ambox", "symbol", "sound"
            ]):
                continue

            # Skip non-image files
            if not any(ext in filename.lower() for ext in [".jpg", ".jpeg", ".png", ".gif"]):
                continue

            # Build direct URL using Wikimedia's Special:FilePath
            # This redirects to the actual image file
            # Remove "File:" prefix if present
            if filename.startswith("File:"):
                filename = filename[5:]

            direct_url = f"https://commons.wikimedia.org/wiki/Special:FilePath/{quote(filename)}"
            image_urls.append(direct_url)

            if len(image_urls) >= max_images:
                break

        print(f"✓ Found {len(image_urls)} images for '{species_name}'")
        return image_urls

    except requests.RequestException as e:
        print(f"❌ Network error fetching images for '{species_name}': {e}")
        return []
    except Exception as e:
        print(f"❌ Error processing images for '{species_name}': {e}")
        return []


def get_high_quality_image(species_name: str) -> Optional[str]:
    """
    Get a single high-quality primary image for a species.

    Uses Wikipedia's "pageimages" API which returns the main article image
    (usually the best quality, most representative photo).

    Args:
        species_name: Common name of the bird

    Returns:
        Direct URL to the primary species image, or None if not found
    """
    try:
        api_url = "https://en.wikipedia.org/w/api.php"
        page_title = species_name.replace(" ", "_")

        params = {
            "action": "query",
            "titles": page_title,
            "prop": "pageimages",  # Get primary page image
            "piprop": "original",   # Get original size (not thumbnail)
            "format": "json",
            "formatversion": "2"
        }

        response = requests.get(api_url, params=params, headers=HEADERS, timeout=10)
        response.raise_for_status()
        data = response.json()

        pages = data.get("query", {}).get("pages", [])
        if pages and "original" in pages[0]:
            image_url = pages[0]["original"]["source"]
            print(f"✓ Found primary image for '{species_name}'")
            return image_url

        print(f"⚠️  No primary image found for '{species_name}'")
        return None

    except Exception as e:
        print(f"❌ Error fetching primary image for '{species_name}': {e}")
        return None


def test_species_images(species_name: str):
    """
    Test function to preview images for a species.
    Prints URLs and metadata.
    """
    print(f"\n🔍 Testing Wikipedia images for: {species_name}")
    print("=" * 60)

    # Test regular images
    print("\n📸 Regular images (from page gallery):")
    images = get_wikipedia_images(species_name, max_images=3)
    if images:
        for i, url in enumerate(images, 1):
            print(f"   {i}. {url}")
    else:
        print("   (No images found)")

    # Test primary image
    print("\n🌟 Primary image (main article photo):")
    primary = get_high_quality_image(species_name)
    if primary:
        print(f"   {primary}")
    else:
        print("   (No primary image found)")


if __name__ == "__main__":
    # Test with a few species
    test_species = [
        "Brown Pelican",
        "Great Egret",
        "Roseate Spoonbill",
        "Magnificent Frigatebird"
    ]

    print("🧪 WIKIPEDIA IMAGE API TEST")
    print("=" * 60)

    for species in test_species:
        test_species_images(species)
        print()

    print("\n✅ Test complete! Check if URLs load in your browser.")
