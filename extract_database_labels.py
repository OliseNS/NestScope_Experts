#!/usr/bin/env python3
"""
Extract Species Labels from Original Database

This script links aerial images in your dataset to the expert species labels
that already exist in the original organizational database.

Educational Context:
-------------------
This demonstrates a common ML workflow challenge: matching training labels
(from a database) to actual image files (in your filesystem). The connection
is made through metadata like photo numbers, dates, and camera IDs.

Key Insight:
The "dotting" records show which species were present in each photo, but
not the EXACT bounding boxes. You'll need to:
1. Use these as image-level labels (multi-label classification)
2. Or match dotted photos to your detected birds using visual clustering
"""

import sqlite3
import os
import json
from pathlib import Path
from collections import defaultdict, Counter
from typing import Dict, List, Set


class DatabaseLabelExtractor:
    """Extract and match species labels from organizational database"""

    def __init__(self, db_path: str = "data/bird_data_complete.db",
                 images_dir: str = "labeller/nestvision/images"):
        self.db_path = Path(db_path)
        self.images_dir = Path(images_dir)

        if not self.db_path.exists():
            raise FileNotFoundError(f"Database not found: {self.db_path}")

        self.conn = sqlite3.connect(str(self.db_path))
        self.cursor = self.conn.cursor()

    def get_all_species_codes(self) -> Dict[str, str]:
        """Get species code to name mapping"""
        self.cursor.execute("SELECT SpeciesCode, SpeciesName FROM tblSpeciesCodes")
        return {code: name for code, name in self.cursor.fetchall()}

    def extract_all_labels(self) -> Dict[str, List[Dict]]:
        """
        Extract all photo-species labels from database.

        Returns:
            {photo_identifier: [list of species records]}
        """
        labels = defaultdict(list)

        # Extract from each table
        tables = [
            'tblSpeciesData2010',
            '"tblSpeciesData2011-2013"',
            '"tblSpeciesData2015_2018_2021"'
        ]

        for table in tables:
            query = f"""
                SELECT
                    Year, Date, ColonyName,
                    CameraNumber, CardNumber, PhotoNumber,
                    SpeciesCode, WBN, PQ,
                    Dotter, DateDotted
                FROM {table}
                WHERE PhotoNumber IS NOT NULL
                  AND SpeciesCode IS NOT NULL
            """

            self.cursor.execute(query)

            for row in self.cursor.fetchall():
                year, date, colony, camera, card, photo, species, wbn, pq, dotter, date_dotted = row

                # Create photo identifier
                photo_id = self._build_photo_identifier(year, date, camera, card, photo)

                labels[photo_id].append({
                    'year': year,
                    'date': date,
                    'colony': colony,
                    'camera': camera,
                    'card': card,
                    'photo': photo,
                    'species': species,
                    'wbn': wbn,  # Nests with birds
                    'pq': pq,     # Photo quality
                    'dotter': dotter,
                    'date_dotted': date_dotted
                })

        return dict(labels)

    def _build_photo_identifier(self, year, date, camera, card, photo):
        """
        Build photo identifier from metadata.

        This tries to match the naming convention used in your image files.
        Example: "10June2010Camera1Card1 471"
        """
        # Clean up components
        year = str(year).strip() if year else ""
        date = str(date).strip() if date else ""
        camera = str(camera).strip() if camera else ""
        card = str(card).strip() if card else ""
        photo = str(photo).strip() if photo else ""

        # Try to match filename patterns
        # Pattern 1: "10June2010Camera1Card1 471"
        if date and camera and card and photo:
            return f"{date}Camera{camera}Card{card} {photo}"

        # Pattern 2: "10 June 2010 Camera 1 Card 1 471"
        return f"{date} Camera {camera} Card {card} {photo}".replace("  ", " ")

    def match_labels_to_images(self) -> Dict[str, Dict]:
        """
        Match database labels to actual image files in nestvision/images.

        Returns:
            {image_filename: {species: [...], metadata: {...}}}
        """
        print("Extracting labels from database...")
        db_labels = self.extract_all_labels()

        print(f"Found {len(db_labels)} labeled photos in database")

        # Get all images in nestvision
        if not self.images_dir.exists():
            print(f"Warning: Images directory not found: {self.images_dir}")
            return {}

        image_files = list(self.images_dir.glob("*.jpg"))
        print(f"Found {len(image_files)} images in {self.images_dir}")

        matches = {}
        unmatched_db = []

        # Try to match each database label to an image file
        for photo_id, species_list in db_labels.items():
            matched = False

            # Try exact match first
            for img_file in image_files:
                img_name = img_file.stem  # filename without extension

                # Check if photo_id is in the image filename
                if photo_id in img_name or img_name.startswith(photo_id):
                    # Get unique species in this photo
                    species_codes = list(set(s['species'] for s in species_list))

                    matches[img_file.name] = {
                        'species': species_codes,
                        'records': species_list,
                        'photo_id': photo_id,
                        'colony': species_list[0]['colony'] if species_list else None,
                        'date': species_list[0]['date'] if species_list else None,
                    }
                    matched = True
                    break

            if not matched:
                unmatched_db.append(photo_id)

        print(f"\n✅ Matched {len(matches)} images to database labels")
        print(f"❌ Unmatched database records: {len(unmatched_db)}")

        return matches

    def generate_report(self):
        """Generate comprehensive label matching report"""
        print("=" * 80)
        print("DATABASE SPECIES LABELS EXTRACTION REPORT")
        print("=" * 80)

        # Get all labels
        db_labels = self.extract_all_labels()

        # Species statistics
        species_counts = Counter()
        photo_species_counts = Counter()

        for photo_id, species_list in db_labels.items():
            unique_species = set(s['species'] for s in species_list)
            photo_species_counts[len(unique_species)] += 1

            for s in species_list:
                species_counts[s['species']] += 1

        print(f"\n📊 DATABASE STATISTICS")
        print(f"{'─' * 80}")
        print(f"Total labeled photos: {len(db_labels):,}")
        print(f"Total species records: {sum(len(v) for v in db_labels.values()):,}")
        print(f"Unique species codes: {len(species_counts)}")

        print(f"\n🐦 TOP 20 SPECIES BY PHOTO COUNT")
        print(f"{'─' * 80}")
        for species, count in species_counts.most_common(20):
            print(f"  {species:<8} → {count:>5} photos")

        print(f"\n📸 SPECIES PER PHOTO DISTRIBUTION")
        print(f"{'─' * 80}")
        for num_species, num_photos in sorted(photo_species_counts.items()):
            print(f"  Photos with {num_species} species: {num_photos:,}")

        # Match to actual images
        print(f"\n🔗 MATCHING TO NESTVISION IMAGES")
        print(f"{'─' * 80}")
        matches = self.match_labels_to_images()

        if matches:
            print(f"\n✅ SUCCESSFULLY MATCHED IMAGES:")
            for img_name, data in list(matches.items())[:10]:
                species_str = ", ".join(data['species'])
                print(f"  {img_name}")
                print(f"    Species: {species_str}")
                print(f"    Colony: {data['colony']}")

        # Save to JSON
        output_file = "database_species_labels.json"
        with open(output_file, 'w') as f:
            json.dump({
                'matches': matches,
                'statistics': {
                    'total_labeled_photos': len(db_labels),
                    'total_matched_images': len(matches),
                    'species_counts': dict(species_counts.most_common()),
                }
            }, f, indent=2)

        print(f"\n💾 Saved results to: {output_file}")
        print("=" * 80)

    def close(self):
        """Close database connection"""
        self.conn.close()


def main():
    """Main entry point"""
    try:
        extractor = DatabaseLabelExtractor()
        extractor.generate_report()
        extractor.close()

    except FileNotFoundError as e:
        print(f"❌ Error: {e}")
        print("\nMake sure you run this from the project root directory:")
        print("  python3 extract_database_labels.py")

    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
