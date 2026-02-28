"""
Labeling Service - Cluster-Aware Species Labeling

This service provides intelligent labeling assistance by:
1. Filtering species references based on cluster characteristics
2. Tracking labeling progress per cluster
3. Suggesting species based on visual similarity
4. Detecting outliers and inconsistencies

Educational Context:
---------------------------------------------------------------------------
This demonstrates how AI assists humans rather than replacing them.
The clustering (unsupervised ML) helps organize the work, but human
judgment makes the final species identification.

This is called "Human-in-the-Loop ML" - a critical pattern in production AI.
"""

import json
import os
import numpy as np
from pathlib import Path
from collections import Counter, defaultdict
from typing import Dict, List, Optional, Tuple


class LabelingService:
    """
    Service for cluster-aware species labeling workflow.

    Key concepts:
    - Uses cluster features to filter relevant species
    - Tracks progress to keep labelers motivated
    - Detects outliers to catch mistakes
    """

    def __init__(self, dataset_path: str):
        """
        Args:
            dataset_path: Path to dataset (e.g., labeller/nestvision)
        """
        self.dataset_path = Path(dataset_path)
        self.crops_dir = self.dataset_path / "bird_crops"
        self.clusters_dir = self.crops_dir / "clusters"
        self.labels_file = self.crops_dir / "bird_labels.json"
        self.cluster_mapping_file = self.clusters_dir / "cluster_species_mapping.json"
        self.metadata_file = self.crops_dir / "metadata.json"

        # Load cluster data
        self.clusters_data = self._load_clusters()

        # Load or initialize labels
        self.labels = self._load_labels()

        # Load or initialize cluster species mapping
        # This stores which species are commonly found in each cluster
        self.cluster_species = self._load_cluster_species_mapping()

        # Load bird metadata (contains bounding box information)
        self.bird_metadata = self._load_bird_metadata()

    def _load_clusters(self) -> Dict:
        """Load cluster data from clustering pipeline"""
        clusters_file = self.clusters_dir / "clusters_for_labeling.json"

        if not clusters_file.exists():
            raise FileNotFoundError(
                f"Clusters not found at {clusters_file}\n"
                "Run clustering first: python scripts/cluster_birds.py"
            )

        with open(clusters_file, 'r') as f:
            return json.load(f)

    def _load_labels(self) -> Dict:
        """Load existing labels or create new label store"""
        if self.labels_file.exists():
            with open(self.labels_file, 'r') as f:
                return json.load(f)

        # Initialize empty label store
        return {
            'birds': {},  # bird_id -> {species, confidence, cluster_id, timestamp}
            'metadata': {
                'total_birds': self.clusters_data.get('total_birds', 0),
                'labeled_count': 0,
                'last_updated': None
            }
        }

    def _load_cluster_species_mapping(self) -> Dict:
        """
        Load cluster-to-species mapping.

        This mapping helps filter species options per cluster.
        It's built dynamically as birds are labeled.

        Structure:
        {
            "0": {
                "dominant_species": ["BRPE", "DCCO"],  # Most common in cluster
                "all_species": ["BRPE", "DCCO", "ANHI"],  # All found so far
                "confidence": "high"  # How pure is this cluster?
            }
        }
        """
        if self.cluster_mapping_file.exists():
            with open(self.cluster_mapping_file, 'r') as f:
                return json.load(f)

        # Initialize empty mapping
        return {}

    def _load_bird_metadata(self) -> Dict:
        """
        Load bird crop metadata including bounding box information.

        Returns a dict mapping crop_id to metadata including bbox_yolo
        (normalized YOLO format: [x_center, y_center, width, height])
        """
        if self.metadata_file.exists():
            with open(self.metadata_file, 'r') as f:
                metadata = json.load(f)
                # Create lookup dict by crop_id for fast access
                return {crop['crop_id']: crop for crop in metadata['crops']}

        return {}

    def _save_labels(self):
        """Persist labels to disk"""
        self.labels_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.labels_file, 'w') as f:
            json.dump(self.labels, f, indent=2)

    def _save_cluster_mapping(self):
        """Persist cluster species mapping"""
        self.cluster_mapping_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.cluster_mapping_file, 'w') as f:
            json.dump(self.cluster_species, f, indent=2)

    def get_cluster_info(self, cluster_id: str) -> Dict:
        """
        Get detailed info about a cluster.

        Returns:
            - Total birds in cluster
            - Labeled count
            - Progress percentage
            - Species distribution (if any labeled)
            - Suggested species for this cluster
        """
        cluster_data = self.clusters_data['clusters'].get(str(cluster_id))
        if not cluster_data:
            return None

        # Count labeled birds in this cluster
        # Support both numeric and string (species code) cluster IDs
        cluster_id_str = str(cluster_id)
        labeled_in_cluster = sum(
            1 for bird_id, label_data in self.labels['birds'].items()
            if str(label_data.get('cluster_id')) == cluster_id_str
        )

        total_in_cluster = cluster_data['total_birds']
        progress = labeled_in_cluster / total_in_cluster if total_in_cluster > 0 else 0

        # Get species distribution for this cluster
        species_counts = Counter()
        for bird_id, label_data in self.labels['birds'].items():
            if str(label_data.get('cluster_id')) == cluster_id_str:
                species_counts[label_data['species']] += 1

        # Get suggested species (from mapping + current labels)
        suggested_species = self._get_suggested_species(cluster_id)

        return {
            'cluster_id': cluster_id_str,
            'total_birds': total_in_cluster,
            'labeled_count': labeled_in_cluster,
            'unlabeled_count': total_in_cluster - labeled_in_cluster,
            'progress': progress,
            'species_distribution': dict(species_counts.most_common()),
            'suggested_species': suggested_species
        }

    def _get_suggested_species(self, cluster_id: str) -> List[str]:
        """
        Get suggested species for a cluster based on:
        1. Previously labeled birds in this cluster
        2. Cluster species mapping (learned over time)
        3. Visual features (future enhancement)

        This is the SMART FILTERING that reduces 72 options to ~5-10!
        """
        suggested = set()
        cluster_id_str = str(cluster_id)

        # Method 1: Species already found in this cluster
        for bird_id, label_data in self.labels['birds'].items():
            if str(label_data.get('cluster_id')) == cluster_id_str:
                suggested.add(label_data['species'])

        # Method 2: Cluster mapping (if available)
        mapping = self.cluster_species.get(str(cluster_id), {})
        suggested.update(mapping.get('dominant_species', []))
        suggested.update(mapping.get('all_species', []))

        # Method 3: Similar clusters (future enhancement)
        # TODO: Find clusters with similar visual features and suggest their species

        # If no suggestions yet, return empty (show all species)
        # After first few labels, this will narrow down quickly!
        return sorted(list(suggested))

    def get_next_unlabeled_bird(self, cluster_id: str) -> Optional[Dict]:
        """
        Get next bird to label in a cluster.

        Returns bird info including image path, bounding box, and surrounding context.
        """
        cluster_data = self.clusters_data['clusters'].get(str(cluster_id))
        if not cluster_data:
            return None

        # Find first unlabeled bird in cluster
        for bird in cluster_data['birds']:
            bird_id = str(bird['bird_id'])
            if bird_id not in self.labels['birds']:
                # Add cluster context (show some labeled neighbors)
                context_birds = self._get_context_birds(cluster_id, bird_id, n=6)

                # Get bbox from metadata
                crop_id = bird.get('crop_id', bird['bird_id'])
                metadata = self.bird_metadata.get(crop_id, {})
                bbox_yolo = metadata.get('bbox_yolo')  # [x_center, y_center, width, height]

                return {
                    'bird_id': int(bird_id),
                    'crop_id': crop_id,
                    'crop_filename': bird['crop_filename'],
                    'image_name': bird['image_name'],
                    'cluster_id': str(cluster_id),  # Support string cluster IDs (species codes)
                    'bbox': bbox_yolo,  # Add bbox for full image highlighting
                    # Direct URLs for frontend (no URL construction needed)
                    'crop_url': f"/api/bird_crop/{bird_id}",
                    'full_image_url': f"/api/original_image/{bird['image_name']}",
                    'context_birds': context_birds,
                    'suggested_species': self._get_suggested_species(cluster_id)
                }

        # All birds in cluster are labeled
        return None

    def _get_context_birds(self, cluster_id: str, current_bird_id: str, n: int = 6) -> List[Dict]:
        """
        Get labeled birds from same cluster to show as context.

        This helps non-experts see patterns:
        "Oh, the other birds in this cluster are BRPE, so this is probably BRPE too"
        """
        context = []
        cluster_id_str = str(cluster_id)

        for bird_id, label_data in self.labels['birds'].items():
            if str(label_data.get('cluster_id')) == cluster_id_str and bird_id != current_bird_id:
                context.append({
                    'bird_id': bird_id,
                    'species': label_data['species'],
                    'confidence': label_data.get('confidence', 'unknown')
                })

                if len(context) >= n:
                    break

        return context

    def save_label(self, bird_id: str, species: str, confidence: str = 'high',
                   cluster_id: Optional[int] = None) -> Dict:
        """
        Save a label for a bird.

        This also updates the cluster species mapping to improve suggestions
        for future birds in the same cluster.

        Args:
            bird_id: Unique bird identifier
            species: Species code (e.g., "BRPE")
            confidence: "high", "medium", "low"
            cluster_id: Which cluster this bird belongs to

        Returns:
            Updated label data
        """
        import time

        # Save label
        self.labels['birds'][str(bird_id)] = {
            'species': species,
            'confidence': confidence,
            'cluster_id': cluster_id,
            'timestamp': time.time()
        }

        # Update metadata
        self.labels['metadata']['labeled_count'] = len(self.labels['birds'])
        self.labels['metadata']['last_updated'] = time.time()

        # Update cluster species mapping
        if cluster_id is not None:
            self._update_cluster_mapping(cluster_id, species)

        # Persist
        self._save_labels()

        return self.labels['birds'][str(bird_id)]

    def _update_cluster_mapping(self, cluster_id: int, species: str):
        """
        Update cluster species mapping when a bird is labeled.

        This makes suggestions better for future birds in same cluster!
        """
        cluster_key = str(cluster_id)

        if cluster_key not in self.cluster_species:
            self.cluster_species[cluster_key] = {
                'dominant_species': [],
                'all_species': [],
                'confidence': 'unknown'
            }

        mapping = self.cluster_species[cluster_key]

        # Add to all_species if not present
        if species not in mapping['all_species']:
            mapping['all_species'].append(species)

        # Calculate species distribution in this cluster
        species_counts = Counter()
        for bird_id, label_data in self.labels['birds'].items():
            if label_data.get('cluster_id') == cluster_id:
                species_counts[label_data['species']] += 1

        # Top 3 most common = dominant species
        mapping['dominant_species'] = [
            species for species, count in species_counts.most_common(3)
        ]

        # Calculate cluster purity (confidence)
        if len(species_counts) > 0:
            total = sum(species_counts.values())
            top_species_ratio = species_counts.most_common(1)[0][1] / total

            if top_species_ratio > 0.9:
                mapping['confidence'] = 'high'  # >90% one species
            elif top_species_ratio > 0.7:
                mapping['confidence'] = 'medium'  # 70-90% one species
            else:
                mapping['confidence'] = 'low'  # Mixed cluster

        self._save_cluster_mapping()

    def get_overall_progress(self) -> Dict:
        """Get labeling progress across all clusters"""
        total_birds = self.labels['metadata']['total_birds']
        labeled_count = self.labels['metadata']['labeled_count']

        # Progress per cluster
        cluster_progress = []
        for cluster_id in self.clusters_data['clusters'].keys():
            info = self.get_cluster_info(cluster_id)
            cluster_progress.append({
                'cluster_id': str(cluster_id),  # Support string cluster IDs (species codes)
                'total': info['total_birds'],
                'labeled': info['labeled_count'],
                'progress': info['progress']
            })

        # Sort by progress (show incomplete clusters first)
        cluster_progress.sort(key=lambda x: x['progress'])

        return {
            'total_birds': total_birds,
            'labeled_count': labeled_count,
            'unlabeled_count': total_birds - labeled_count,
            'progress': labeled_count / total_birds if total_birds > 0 else 0,
            'clusters': cluster_progress,
            'estimated_time_remaining': self._estimate_time_remaining()
        }

    def _estimate_time_remaining(self) -> str:
        """
        Estimate time remaining based on average labeling speed.

        Assumes ~7 seconds per bird (realistic for non-experts with keyboard shortcuts)
        """
        unlabeled = self.labels['metadata']['total_birds'] - self.labels['metadata']['labeled_count']

        # 7 seconds per bird average
        seconds = unlabeled * 7
        hours = seconds / 3600

        if hours < 1:
            return f"{int(seconds / 60)} minutes"
        else:
            return f"{hours:.1f} hours"

    def detect_outliers(self, cluster_id: str, threshold: float = 0.1) -> List[Dict]:
        """
        Detect potentially mislabeled birds in a cluster.

        Strategy: If a cluster is >90% BRPE, but has a few SNEG labels,
        flag those SNEG birds for review (might be mistakes).

        Args:
            cluster_id: Cluster to check
            threshold: Minimum ratio to be considered an outlier (default 10%)

        Returns:
            List of suspicious labels to review
        """
        outliers = []

        # Get species distribution
        species_counts = Counter()
        cluster_labels = {}
        cluster_id_str = str(cluster_id)

        for bird_id, label_data in self.labels['birds'].items():
            if str(label_data.get('cluster_id')) == cluster_id_str:
                species = label_data['species']
                species_counts[species] += 1
                cluster_labels[bird_id] = label_data

        if len(species_counts) == 0:
            return []

        total = sum(species_counts.values())

        # Find rare species in this cluster
        for species, count in species_counts.items():
            ratio = count / total

            if ratio < threshold:  # Less than 10% of cluster
                # Flag all birds with this species
                for bird_id, label_data in cluster_labels.items():
                    if label_data['species'] == species:
                        outliers.append({
                            'bird_id': bird_id,
                            'species': species,
                            'reason': f"Only {count}/{total} ({ratio:.1%}) birds in cluster are {species}",
                            'confidence': label_data.get('confidence', 'unknown')
                        })

        return outliers
