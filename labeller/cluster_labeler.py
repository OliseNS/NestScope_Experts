#!/usr/bin/env python3
"""
Cluster-Based Species Labeling for Nestperts

This module extends Nestperts to support cluster-based labeling where experts
label representative clusters instead of individual birds.

Workflow:
1. Load clusters from clustering pipeline
2. Show expert one representative image per cluster (30-50 clusters)
3. Expert assigns species to entire cluster in ~5 minutes
4. All birds in that cluster get the same label
5. Export labeled data for training

Time savings:
- Traditional: 50,000 birds × 30 sec = 416 hours
- Cluster-based: 30 clusters × 5 min = 2.5 hours
- 99.4% time reduction!
"""

import json
import cv2
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class ClusterInfo:
    """Information about a bird cluster"""
    cluster_id: int
    size: int  # Number of birds in cluster
    species_label: Optional[str] = None
    confidence: Optional[str] = None  # 'high', 'medium', 'low'
    notes: Optional[str] = None


class ClusterLabeler:
    """
    Manages cluster-based labeling workflow for experts.

    This dramatically reduces annotation time by having experts label
    clusters of similar birds rather than individual birds.
    """

    def __init__(self, clusters_file: str, output_dir: str):
        """
        Args:
            clusters_file: Path to clusters_for_labeling.json
            output_dir: Where to save labeled results
        """
        self.clusters_file = Path(clusters_file)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Load cluster data
        with open(self.clusters_file, 'r') as f:
            self.data = json.load(f)

        self.clusters = self.data['clusters']
        self.cluster_info = {}  # cluster_id -> ClusterInfo

        # Initialize cluster info
        for cluster_id, cluster_data in self.clusters.items():
            self.cluster_info[cluster_id] = ClusterInfo(
                cluster_id=int(cluster_id),
                size=cluster_data['total_birds'],
                species_label=cluster_data.get('species_label'),
                confidence=cluster_data.get('confidence')
            )

    def get_unlabeled_clusters(self) -> List[str]:
        """Get list of cluster IDs that haven't been labeled yet"""
        return [
            cid for cid, info in self.cluster_info.items()
            if info.species_label is None
        ]

    def get_cluster_progress(self) -> Dict:
        """Get labeling progress statistics"""
        total = len(self.cluster_info)
        labeled = sum(1 for info in self.cluster_info.values()
                     if info.species_label is not None)

        total_birds = sum(info.size for info in self.cluster_info.values())
        labeled_birds = sum(info.size for info in self.cluster_info.values()
                           if info.species_label is not None)

        return {
            'clusters_total': total,
            'clusters_labeled': labeled,
            'clusters_remaining': total - labeled,
            'clusters_progress': labeled / total if total > 0 else 0,
            'birds_total': total_birds,
            'birds_labeled': labeled_birds,
            'birds_progress': labeled_birds / total_birds if total_birds > 0 else 0
        }

    def label_cluster(self, cluster_id: str, species: str,
                     confidence: str = 'high', notes: str = ''):
        """
        Assign species label to an entire cluster.

        Args:
            cluster_id: ID of cluster to label
            species: Species code (e.g., 'BRPE', 'ROTE')
            confidence: Expert's confidence ('high', 'medium', 'low')
            notes: Optional notes about the cluster
        """
        if cluster_id not in self.cluster_info:
            raise ValueError(f"Cluster {cluster_id} not found")

        info = self.cluster_info[cluster_id]
        info.species_label = species
        info.confidence = confidence
        info.notes = notes

        # Update in original data structure
        self.clusters[cluster_id]['species_label'] = species
        self.clusters[cluster_id]['confidence'] = confidence
        self.clusters[cluster_id]['notes'] = notes

        print(f"✅ Labeled cluster {cluster_id} as {species} "
              f"({info.size} birds)")

    def export_labels(self, output_file: Optional[str] = None):
        """
        Export cluster labels back to individual bird labels.

        This creates YOLO-format label files with species assignments
        for all birds based on their cluster membership.
        """
        if output_file is None:
            output_file = self.output_dir / 'cluster_labels.json'

        # Build mapping: (image_name, bbox_index) -> species
        bird_labels = {}

        for cluster_id, cluster_data in self.clusters.items():
            species = cluster_data.get('species_label')
            if species is None:
                continue  # Skip unlabeled clusters

            for bird in cluster_data['birds']:
                key = (bird['image_name'], bird['bbox_index'])
                bird_labels[key] = {
                    'species': species,
                    'cluster_id': int(cluster_id),
                    'confidence': cluster_data.get('confidence', 'unknown'),
                    'bbox_yolo': bird['bbox_yolo']
                }

        # Group by image
        labels_by_image = {}
        for (image_name, bbox_idx), label_info in bird_labels.items():
            if image_name not in labels_by_image:
                labels_by_image[image_name] = []
            labels_by_image[image_name].append({
                'bbox_index': bbox_idx,
                **label_info
            })

        # Export
        export_data = {
            'total_images': len(labels_by_image),
            'total_birds': len(bird_labels),
            'labels_by_image': labels_by_image,
            'cluster_info': {
                cid: {
                    'species': info.species_label,
                    'confidence': info.confidence,
                    'size': info.size,
                    'notes': info.notes
                }
                for cid, info in self.cluster_info.items()
            }
        }

        with open(output_file, 'w') as f:
            json.dump(export_data, f, indent=2)

        print(f"📋 Exported labels to: {output_file}")
        print(f"   Images: {len(labels_by_image)}")
        print(f"   Birds: {len(bird_labels)}")

        return labels_by_image

    def update_yolo_labels(self, yolo_dataset_dir: str):
        """
        Update YOLO label files with cluster-assigned species.

        This modifies the original label files to include species codes
        in the 6th field: class_id x y w h species_code

        Args:
            yolo_dataset_dir: Path to YOLO dataset directory
        """
        dataset_dir = Path(yolo_dataset_dir)
        labels_dir = dataset_dir / 'labels'

        # Get labels by image
        labels_by_image = self.export_labels()

        updated_count = 0

        for image_name, bird_labels in labels_by_image.items():
            label_file = labels_dir / f"{image_name}.txt"

            if not label_file.exists():
                print(f"Warning: Label file not found: {label_file}")
                continue

            # Read existing labels
            with open(label_file, 'r') as f:
                lines = f.readlines()

            # Update labels with species
            updated_lines = []
            for line_idx, line in enumerate(lines):
                parts = line.strip().split()
                if len(parts) < 5:
                    updated_lines.append(line)
                    continue

                # Find if this bbox has a cluster label
                species = None
                for bird_label in bird_labels:
                    if bird_label['bbox_index'] == line_idx:
                        species = bird_label['species']
                        break

                # Add or update species field
                if species:
                    # YOLO format: class_id x y w h species
                    updated_line = ' '.join(parts[:5]) + f' {species}\n'
                    updated_lines.append(updated_line)
                else:
                    updated_lines.append(line)

            # Write updated labels
            with open(label_file, 'w') as f:
                f.writelines(updated_lines)

            updated_count += 1

        print(f"✅ Updated {updated_count} label files with species")

    def save_progress(self):
        """Save current labeling progress"""
        progress_file = self.output_dir / 'labeling_progress.json'

        progress_data = {
            'progress': self.get_cluster_progress(),
            'clusters': {
                cid: {
                    'cluster_id': info.cluster_id,
                    'size': info.size,
                    'species_label': info.species_label,
                    'confidence': info.confidence,
                    'notes': info.notes
                }
                for cid, info in self.cluster_info.items()
            }
        }

        with open(progress_file, 'w') as f:
            json.dump(progress_data, f, indent=2)

        print(f"💾 Progress saved to: {progress_file}")


def demo_workflow():
    """
    Demonstrates the cluster labeling workflow.

    This shows how an expert would label clusters in practice.
    """
    print("=" * 60)
    print("🦅 CLUSTER LABELING DEMO")
    print("=" * 60)

    # Example: Load clusters
    clusters_file = "labeller/nestvision/clusters/clusters_for_labeling.json"
    labeler = ClusterLabeler(clusters_file, output_dir="labeller/nestvision/clusters")

    # Show progress
    progress = labeler.get_cluster_progress()
    print(f"\n📊 Current Progress:")
    print(f"   Clusters: {progress['clusters_labeled']}/{progress['clusters_total']} "
          f"({progress['clusters_progress']:.1%})")
    print(f"   Birds: {progress['birds_labeled']}/{progress['birds_total']} "
          f"({progress['birds_progress']:.1%})")

    # Get unlabeled clusters
    unlabeled = labeler.get_unlabeled_clusters()
    print(f"\n📋 Unlabeled clusters: {len(unlabeled)}")

    # Simulate expert labeling a cluster
    if unlabeled:
        cluster_id = unlabeled[0]
        print(f"\n👨‍🔬 Expert reviews cluster {cluster_id}...")
        print(f"   (Shows preview image with ~20 representative birds)")
        print(f"   Expert identifies: Brown Pelican")

        labeler.label_cluster(
            cluster_id=cluster_id,
            species='BRPE',
            confidence='high',
            notes='Large brown birds, distinctive pelican shape'
        )

    # Save and export
    labeler.save_progress()
    labeler.export_labels()

    print("\n" + "=" * 60)
    print("✅ Demo complete!")
    print("=" * 60)


if __name__ == '__main__':
    demo_workflow()
