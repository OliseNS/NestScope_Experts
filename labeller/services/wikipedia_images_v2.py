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

        # Search for files on Commons - Updated for 2024/2025 API
        params = {
            "action": "query",
            "format": "json",
            "formatversion": "2",
            "generator": "search",  # Use search generator
            "gsrsearch": f"File:{search_query}",  # Search in File namespace
            "gsrnamespace": "6",  # Namespace 6 = File
            "gsrlimit": str(max_results + 5),  # Get extra to filter
            "prop": "imageinfo",  # Get image information
            "iiprop": "url|size|mime",  # Get URL, dimensions, and mime type
            "iiurlwidth": "800",  # Get 800px wide thumbnail
            "origin": "*"  # Enable CORS
        }

        print(f"🔍 Searching Commons with query: '{search_query}'")
        response = requests.get(api_url, params=params, headers=HEADERS, timeout=15)
        response.raise_for_status()
        data = response.json()

        # Debug output
        if "query" not in data:
            print(f"⚠️  No 'query' in response for '{search_query}'")
            if "error" in data:
                print(f"❌ API Error: {data['error']}")
            return []

        # Extract image URLs
        image_urls = []
        pages = data.get("query", {}).get("pages", [])
        print(f"   Found {len(pages)} pages")

        for page in pages:
            # Skip if not an image
            if "imageinfo" not in page or not page["imageinfo"]:
                continue

            info = page["imageinfo"][0]

            # Filter out non-image files and icons
            mime_type = info.get("mime", "")
            if not mime_type.startswith("image/"):
                continue

            # Skip SVG and very small images (likely icons)
            if mime_type == "image/svg+xml":
                continue

            width = info.get("width", 0)
            height = info.get("height", 0)
            if width < 200 or height < 200:  # Skip tiny images
                continue

            # Get thumb URL (good size for display)
            if "thumburl" in info:
                image_urls.append(info["thumburl"])
            # Fallback to full URL
            elif "url" in info:
                image_urls.append(info["url"])

            if len(image_urls) >= max_results:
                break

        if image_urls:
            print(f"✓ Found {len(image_urls)} valid Commons images for '{search_query}'")
        else:
            print(f"⚠️  No suitable Commons images found for '{search_query}'")

        return image_urls

    except requests.RequestException as e:
        print(f"❌ Network error searching Commons for '{search_query}': {e}")
        return []
    except Exception as e:
        print(f"❌ Error searching Commons for '{search_query}': {e}")
        import traceback
        traceback.print_exc()
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

        # Get page info with thumbnail - Updated for 2024/2025 API
        params = {
            "action": "query",
            "format": "json",
            "formatversion": "2",
            "titles": page_title,
            "prop": "pageimages",
            "piprop": "thumbnail|original",
            "pithumbsize": "800",  # Get large thumbnail
            "pilicense": "any",  # Accept any license
            "origin": "*"  # Enable CORS
        }

        print(f"🔍 Getting Wikipedia page image for '{species_name}'")
        response = requests.get(api_url, params=params, headers=HEADERS, timeout=15)
        response.raise_for_status()
        data = response.json()

        pages = data.get("query", {}).get("pages", [])
        if not pages:
            print(f"⚠️  No Wikipedia page found for '{species_name}'")
            return None

        page = pages[0]

        # Check if page exists and has an image
        if "missing" in page:
            print(f"⚠️  Wikipedia page doesn't exist for '{species_name}'")
            return None

        # Try to get thumbnail URL
        if "thumbnail" in page and "source" in page["thumbnail"]:
            thumbnail_url = page["thumbnail"]["source"]
            print(f"✓ Found Wikipedia page image for '{species_name}'")
            return thumbnail_url

        # Try original image
        if "original" in page and "source" in page["original"]:
            original_url = page["original"]["source"]
            print(f"✓ Found Wikipedia original image for '{species_name}'")
            return original_url

        print(f"⚠️  No Wikipedia page image for '{species_name}'")
        return None

    except requests.RequestException as e:
        print(f"❌ Network error getting Wikipedia image for '{species_name}': {e}")
        return None
    except Exception as e:
        print(f"❌ Error getting Wikipedia image for '{species_name}': {e}")
        import traceback
        traceback.print_exc()
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
    print(f"\n{'='*60}")
    print(f"📸 Fetching images for: {species_name}")
    print(f"   Requested: {max_images} images, offset: {offset}")
    print(f"{'='*60}")

    # Fetch a larger batch to support pagination
    fetch_limit = offset + max_images + 15  # Get extra for filtering
    all_images = []

    # Strategy 1: Get main Wikipedia article image (only on first page)
    if offset == 0:
        print("\n1️⃣  Trying Wikipedia article image...")
        wiki_image = get_wikipedia_page_image(species_name)
        if wiki_image:
            all_images.append(wiki_image)
            print(f"   ✓ Added Wikipedia image")
        else:
            print(f"   ⚠️  No Wikipedia article image")

    # Strategy 2: Search Commons for more images
    print(f"\n2️⃣  Searching Wikimedia Commons...")
    commons_images = search_commons_images(species_name, max_results=fetch_limit)

    # Avoid duplicates
    added = 0
    for img in commons_images:
        if img not in all_images:
            all_images.append(img)
            added += 1

    print(f"   ✓ Added {added} unique Commons images")
    print(f"   📊 Total images before pagination: {len(all_images)}")

    # Apply pagination (skip offset, take max_images)
    paginated_images = all_images[offset:offset + max_images]

    print(f"   📤 Returning {len(paginated_images)} images after pagination")
    print(f"{'='*60}\n")

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
