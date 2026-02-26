#!/usr/bin/env python3
"""
Query Expert Classification Data

This script analyzes the Nestperts labeling database to show:
1. Which images experts have worked on
2. What species they identified
3. Classification methods used (decision tree vs quick search)
4. Progress by cluster
5. Temporal labeling patterns

Educational Note:
-----------------
This demonstrates how to track human expert annotations in a
machine learning pipeline. The labels experts create become
"ground truth" training data for future automated classification models.
"""

import json
import os
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple


class ExpertLabelAnalyzer:
    """Analyzes expert classification data from Nestperts"""

    def __init__(self, dataset_path: str = "labeller/nestvision"):
        self.dataset_path = Path(dataset_path)
        self.labels_file = self.dataset_path / "bird_crops" / "bird_labels.json"
        self.metadata_file = self.dataset_path / "bird_crops" / "metadata.json"

        # Load data
        self.labels_data = self._load_json(self.labels_file)
        self.metadata = self._load_json(self.metadata_file)

        # Build bird ID to source image mapping
        self.bird_to_image = self._build_bird_mapping()

    def _load_json(self, filepath: Path) -> Dict:
        """Load JSON file"""
        if not filepath.exists():
            raise FileNotFoundError(f"File not found: {filepath}")

        with open(filepath, 'r') as f:
            return json.load(f)

    def _build_bird_mapping(self) -> Dict[str, Dict]:
        """
        Build mapping from bird_id to source image and metadata.

        Returns:
            {bird_id: {source_image, crop_filename, bbox, cluster_id}}
        """
        mapping = {}

        for crop in self.metadata.get('crops', []):
            crop_id = str(crop['crop_id'])
            mapping[crop_id] = {
                'source_image': crop['source_image'],
                'crop_filename': crop['crop_filename'],
                'bbox_pixel': crop['bbox_pixel'],
                'bbox_yolo': crop['bbox_yolo'],
            }

        return mapping

    def get_labeled_images(self) -> Dict[str, List[Dict]]:
        """
        Get all images that experts have labeled, grouped by image.

        Returns:
            {image_name: [list of labeled birds in that image]}
        """
        images = defaultdict(list)

        for bird_id, label_info in self.labels_data.get('birds', {}).items():
            if bird_id in self.bird_to_image:
                bird_metadata = self.bird_to_image[bird_id]
                source_image = bird_metadata['source_image']

                images[source_image].append({
                    'bird_id': bird_id,
                    'species': label_info['species'],
                    'confidence': label_info['confidence'],
                    'cluster_id': label_info.get('cluster_id'),
                    'timestamp': label_info.get('timestamp'),
                    'bbox_pixel': bird_metadata['bbox_pixel'],
                    'classification_method': label_info.get('classification_method', 'unknown'),
                    'decision_path': label_info.get('decision_path', {})
                })

        return dict(images)

    def get_species_summary(self) -> Dict:
        """Get summary statistics by species"""
        species_counts = Counter()
        species_clusters = defaultdict(set)
        species_images = defaultdict(set)

        for bird_id, label_info in self.labels_data.get('birds', {}).items():
            species = label_info['species']
            cluster_id = label_info.get('cluster_id')

            species_counts[species] += 1

            if cluster_id is not None:
                species_clusters[species].add(cluster_id)

            if bird_id in self.bird_to_image:
                source_image = self.bird_to_image[bird_id]['source_image']
                species_images[species].add(source_image)

        return {
            'counts': dict(species_counts),
            'clusters_per_species': {sp: len(clusters) for sp, clusters in species_clusters.items()},
            'images_per_species': {sp: len(imgs) for sp, imgs in species_images.items()}
        }

    def get_cluster_progress(self) -> Dict[int, Dict]:
        """Get labeling progress by cluster"""
        cluster_data = defaultdict(lambda: {
            'labeled': 0,
            'species': Counter()
        })

        for bird_id, label_info in self.labels_data.get('birds', {}).items():
            cluster_id = label_info.get('cluster_id')
            if cluster_id is not None:
                cluster_data[cluster_id]['labeled'] += 1
                cluster_data[cluster_id]['species'][label_info['species']] += 1

        return dict(cluster_data)

    def get_temporal_analysis(self) -> List[Dict]:
        """Analyze labeling over time"""
        labels_with_time = []

        for bird_id, label_info in self.labels_data.get('birds', {}).items():
            if 'timestamp' in label_info:
                labels_with_time.append({
                    'bird_id': bird_id,
                    'species': label_info['species'],
                    'timestamp': label_info['timestamp'],
                    'datetime': datetime.fromtimestamp(label_info['timestamp']).strftime('%Y-%m-%d %H:%M:%S'),
                    'cluster_id': label_info.get('cluster_id'),
                    'method': label_info.get('classification_method', 'unknown')
                })

        # Sort by timestamp
        labels_with_time.sort(key=lambda x: x['timestamp'])

        return labels_with_time

    def print_report(self):
        """Print comprehensive analysis report"""
        print("=" * 80)
        print("NESTPERTS EXPERT CLASSIFICATION REPORT")
        print("=" * 80)

        # Overall statistics
        metadata = self.labels_data.get('metadata', {})
        total_birds = metadata.get('total_birds', 0)
        labeled_count = metadata.get('labeled_count', 0)
        last_updated = metadata.get('last_updated')

        print(f"\n📊 OVERALL PROGRESS")
        print(f"{'─' * 80}")
        print(f"Total birds detected: {total_birds:,}")
        print(f"Birds labeled by experts: {labeled_count:,}")
        print(f"Percentage complete: {(labeled_count/total_birds*100):.2f}%")
        if last_updated:
            print(f"Last updated: {datetime.fromtimestamp(last_updated).strftime('%Y-%m-%d %H:%M:%S')}")

        # Species summary
        print(f"\n🐦 SPECIES IDENTIFIED")
        print(f"{'─' * 80}")
        species_summary = self.get_species_summary()

        for species, count in sorted(species_summary['counts'].items(), key=lambda x: -x[1]):
            clusters = species_summary['clusters_per_species'].get(species, 0)
            images = species_summary['images_per_species'].get(species, 0)
            print(f"  {species:8} → {count:3} birds | {clusters:2} clusters | {images:2} images")

        # Cluster progress
        print(f"\n📦 CLUSTER PROGRESS")
        print(f"{'─' * 80}")
        cluster_progress = self.get_cluster_progress()

        for cluster_id in sorted(cluster_progress.keys()):
            data = cluster_progress[cluster_id]
            species_str = ", ".join(f"{sp}:{cnt}" for sp, cnt in data['species'].most_common())
            print(f"  Cluster {cluster_id:3} → {data['labeled']:3} birds labeled → [{species_str}]")

        # Images worked on
        print(f"\n🖼️  IMAGES LABELED")
        print(f"{'─' * 80}")
        labeled_images = self.get_labeled_images()

        print(f"Total images with expert labels: {len(labeled_images)}")

        for image_name in sorted(labeled_images.keys()):
            birds = labeled_images[image_name]
            species_in_image = Counter(b['species'] for b in birds)
            species_str = ", ".join(f"{sp}:{cnt}" for sp, cnt in species_in_image.most_common())
            print(f"\n  📸 {image_name}")
            print(f"     Birds labeled: {len(birds)} → [{species_str}]")

            for bird in birds:
                method = bird.get('classification_method', 'unknown')
                print(f"       • Bird {bird['bird_id']}: {bird['species']} "
                      f"(confidence: {bird['confidence']}, method: {method})")

        # Temporal analysis
        print(f"\n⏱️  LABELING TIMELINE")
        print(f"{'─' * 80}")
        temporal = self.get_temporal_analysis()

        for entry in temporal:
            print(f"  {entry['datetime']} → Bird {entry['bird_id']:4} → "
                  f"{entry['species']:6} (Cluster {entry['cluster_id']}, {entry['method']})")

        # Decision tree usage
        print(f"\n🌳 CLASSIFICATION METHOD ANALYSIS")
        print(f"{'─' * 80}")
        method_counts = Counter()

        for bird_id, label_info in self.labels_data.get('birds', {}).items():
            method = label_info.get('classification_method', 'unknown')
            method_counts[method] += 1

        for method, count in method_counts.most_common():
            print(f"  {method:20} → {count:3} birds")

        print("\n" + "=" * 80)


def main():
    """Main entry point"""
    try:
        analyzer = ExpertLabelAnalyzer()
        analyzer.print_report()

    except FileNotFoundError as e:
        print(f"❌ Error: {e}")
        print("\nMake sure you run this from the project root directory:")
        print("  python query_expert_labels.py")

    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
