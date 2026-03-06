#!/usr/bin/env python3
"""
S3 Crawler - Discover and catalog dotted images and source images from S3 bucket
"""

import json
import re
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from pathlib import Path
import requests
from xml.etree import ElementTree as ET
from collections import defaultdict

class S3Crawler:
    """Crawl TWI S3 bucket to catalog images and build matching index"""

    def __init__(self, bucket="twi-aviandata"):
        self.bucket = bucket
        self.base_url = f"https://{bucket}.s3.amazonaws.com"

    def list_s3_folder(self, prefix: str, max_keys: int = 1000) -> List[Dict]:
        """
        List contents of an S3 folder using AWS S3 REST API
        Returns list of objects with Key, Size, LastModified
        """
        url = f"{self.base_url}/?prefix={prefix}&max-keys={max_keys}"

        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()

            # Parse XML response
            root = ET.fromstring(response.content)
            ns = {'s3': 'http://s3.amazonaws.com/doc/2006-03-01/'}

            objects = []
            for content in root.findall('s3:Contents', ns):
                key = content.find('s3:Key', ns).text
                size = int(content.find('s3:Size', ns).text)
                last_modified = content.find('s3:LastModified', ns).text

                objects.append({
                    'Key': key,
                    'Size': size,
                    'LastModified': last_modified
                })

            return objects
        except Exception as e:
            print(f"Error listing {prefix}: {e}")
            return []

    def parse_dotted_filename(self, filename: str) -> Optional[Dict]:
        """
        Extract metadata from dotted image filename

        Patterns:
        - 7May10DLJ1Area1.JPG          (2010-2013)
        - 18May2015AudubonArea02.JPG   (2015)
        - 21May18_CookeIsl_Area1.JPG   (2018)
        - 19June21BB12Area1.JPG        (2021)
        - 24June23BRETArea1.JPG        (2023)
        """
        patterns = [
            # Pattern 1: DDMonyYY[Colony]Area# (2010-2013)
            r'(?P<day>\d{1,2})(?P<month>[A-Za-z]+)(?P<year>\d{2})(?P<colony>[A-Z0-9]+)(?:AREA)?(?P<area>\d+)',

            # Pattern 2: DDMony20YY[Colony]Area## (2015)
            r'(?P<day>\d{1,2})(?P<month>[A-Za-z]+)(?P<year>\d{4})(?P<colony>[A-Za-z]+)Area(?P<area>\d+)',

            # Pattern 3: DDMonyYY_[Colony]_Area# (2018)
            r'(?P<day>\d{1,2})(?P<month>[A-Za-z]+)(?P<year>\d{2})_(?P<colony>[A-Za-z]+)_Area(?P<area>\d+)',

            # Pattern 4: DDMonyYY[Colony]Area### (2021+)
            r'(?P<day>\d{1,2})(?P<month>[A-Za-z]+)(?P<year>\d{2,4})(?P<colony>[A-Z0-9]+)Area(?P<area>\d+)',
        ]

        for pattern in patterns:
            match = re.search(pattern, filename, re.IGNORECASE)
            if match:
                data = match.groupdict()

                # Normalize year to 4 digits
                year = data['year']
                if len(year) == 2:
                    year = '20' + year if int(year) < 50 else '19' + year

                return {
                    'day': int(data['day']),
                    'month': data['month'].capitalize(),
                    'year': int(year),
                    'colony': data['colony'].upper(),
                    'area': int(data['area']),
                    'filename': filename
                }

        return None

    def catalog_dotted_images(self, save_to: Optional[Path] = None) -> Dict:
        """
        Catalog all dotted images from S3 bucket
        Returns structured catalog with parsed metadata
        """
        print("Cataloging dotted images from S3...")

        # Collection prefixes to explore
        collections = [
            "DottedImages/2010-2013 Dotted Images/",
            "DottedImages/2018 LA Waterbird Colony Photo Analysis/",
            "DottedImages/Task 1 2015 Waterbird Colony Photo Analysis/",
            "DottedImages/Task 2 2021 Waterbird Colony Photo Analysis/",
            "DottedImages/2023/",
        ]

        catalog = {
            'total_images': 0,
            'by_year': defaultdict(list),
            'by_colony': defaultdict(list),
            'unmatched': [],
            'images': []
        }

        for collection in collections:
            print(f"  Exploring {collection}...")
            objects = self.list_s3_folder(collection, max_keys=2000)

            image_count = 0
            for obj in objects:
                key = obj['Key']

                # Only process image files
                if not key.lower().endswith(('.jpg', '.jpeg', '.png', '.tif', '.tiff')):
                    continue

                filename = Path(key).name
                parsed = self.parse_dotted_filename(filename)

                image_data = {
                    's3_key': key,
                    's3_url': f"{self.base_url}/{key}",
                    'filename': filename,
                    'size': obj['Size'],
                    'last_modified': obj['LastModified'],
                    'collection': collection
                }

                if parsed:
                    image_data.update(parsed)
                    catalog['by_year'][parsed['year']].append(image_data)
                    catalog['by_colony'][parsed['colony']].append(image_data)
                else:
                    catalog['unmatched'].append(image_data)

                catalog['images'].append(image_data)
                image_count += 1

            print(f"    Found {image_count} images")
            catalog['total_images'] += image_count

        print(f"\n Cataloged {catalog['total_images']} dotted images")
        print(f"    Years: {sorted(catalog['by_year'].keys())}")
        print(f"    Colonies: {len(catalog['by_colony'])} unique colonies")
        print(f"     Unmatched: {len(catalog['unmatched'])} images")

        # Convert defaultdicts to regular dicts for JSON serialization
        catalog['by_year'] = dict(catalog['by_year'])
        catalog['by_colony'] = dict(catalog['by_colony'])

        if save_to:
            save_to.parent.mkdir(parents=True, exist_ok=True)
            with open(save_to, 'w') as f:
                json.dump(catalog, f, indent=2)
            print(f"\n Saved catalog to {save_to}")

        return catalog

    def find_test_samples(self, catalog: Dict, n_per_year: int = 5) -> List[Dict]:
        """
        Select diverse test samples for validation

        Criteria:
        - n_per_year images from each year
        - Mix of colonies
        - Various area numbers (different image densities)
        """
        print(f"\n Selecting test samples ({n_per_year} per year)...")

        test_samples = []

        for year, images in sorted(catalog['by_year'].items()):
            # Group by colony for this year
            by_colony = defaultdict(list)
            for img in images:
                by_colony[img['colony']].append(img)

            # Select samples from different colonies
            year_samples = []
            colonies = list(by_colony.keys())

            for i in range(min(n_per_year, len(images))):
                colony = colonies[i % len(colonies)]
                colony_images = by_colony[colony]

                if colony_images:
                    # Pick image with diverse area numbers
                    img = colony_images[i % len(colony_images)]
                    year_samples.append(img)

            test_samples.extend(year_samples)
            print(f"  {year}: Selected {len(year_samples)} samples from {len(by_colony)} colonies")

        print(f"\n Total test samples: {len(test_samples)}")
        return test_samples


def main():
    """Run S3 crawler and generate catalog"""
    output_dir = Path("/home/olisemeka.dev/Projects/nexus/Social_Engineering/data")

    crawler = S3Crawler()

    # Catalog all dotted images
    catalog = crawler.catalog_dotted_images(
        save_to=output_dir / "dotted_images_catalog.json"
    )

    # Select test samples
    test_samples = crawler.find_test_samples(catalog, n_per_year=5)

    # Save test samples
    with open(output_dir / "test_samples.json", 'w') as f:
        json.dump(test_samples, f, indent=2)
    print(f"\n Saved test samples to {output_dir / 'test_samples.json'}")

    # Print summary statistics
    print("\n" + "="*60)
    print("SUMMARY STATISTICS")
    print("="*60)

    print(f"\nTotal Images: {catalog['total_images']}")

    print("\nBy Year:")
    for year, images in sorted(catalog['by_year'].items()):
        print(f"  {year}: {len(images):,} images")

    print("\nTop 10 Colonies by Image Count:")
    colony_counts = [(colony, len(images)) for colony, images in catalog['by_colony'].items()]
    colony_counts.sort(key=lambda x: x[1], reverse=True)
    for colony, count in colony_counts[:10]:
        print(f"  {colony}: {count:,} images")

    print(f"\nTest Samples: {len(test_samples)}")
    for sample in test_samples[:5]:
        print(f"  {sample['filename']}")
    print("  ...")


if __name__ == "__main__":
    main()
