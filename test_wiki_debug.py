"""
Debug script to see what Wikipedia API actually returns
"""
import requests
import json

HEADERS = {
    "User-Agent": "NestScope/1.0 (Educational bird monitoring project)"
}

def test_wikipedia_api(species_name):
    """Test what Wikipedia returns for a species"""
    api_url = "https://en.wikipedia.org/w/api.php"
    page_title = species_name.replace(" ", "_")

    print(f"\n{'='*60}")
    print(f"Testing: {species_name}")
    print(f"{'='*60}")

    # Test 1: Check if page exists
    params = {
        "action": "query",
        "titles": page_title,
        "format": "json",
        "formatversion": "2"
    }

    response = requests.get(api_url, params=params, headers=HEADERS, timeout=10)
    data = response.json()

    print("\n1️⃣  Page existence check:")
    print(json.dumps(data, indent=2))

    # Test 2: Get page images
    params = {
        "action": "query",
        "titles": page_title,
        "prop": "images",
        "imlimit": 5,
        "format": "json",
        "formatversion": "2"
    }

    response = requests.get(api_url, params=params, headers=HEADERS, timeout=10)
    data = response.json()

    print("\n2️⃣  Images on page:")
    print(json.dumps(data, indent=2))

    # Test 3: Get primary page image
    params = {
        "action": "query",
        "titles": page_title,
        "prop": "pageimages",
        "piprop": "original",
        "format": "json",
        "formatversion": "2"
    }

    response = requests.get(api_url, params=params, headers=HEADERS, timeout=10)
    data = response.json()

    print("\n3️⃣  Primary image:")
    print(json.dumps(data, indent=2))

if __name__ == "__main__":
    test_wikipedia_api("Brown Pelican")
