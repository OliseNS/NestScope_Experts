"""
Stage 2: Per-Image Clustering

For each source image, cluster its crops into N groups where N = number of species.
"""

import sys
from pathlib import Path
import json
import numpy as np
from datetime import datetime
from collections import defaultdict
from tqdm import tqdm
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))


class PerImageClusterer:
    """
    Performs clustering on crops from individual images.

    Strategy:
    - Single-species images: Skip clustering, assign directly
    - Multi-species images: Run K-means where K = len(species_candidates)
    """

    def __init__(self, crops_dir: str, embeddings_dir: str, output_dir: str):
        """
        Args:
            crops_dir: Path to bird_crops directory
            embeddings_dir: Path to embeddings directory
            output_dir: Path to output directory for clustering results
        """
        self.crops_dir = Path(crops_dir)
        self.embeddings_dir = Path(embeddings_dir)
        self.output_dir = Path(output_dir) / "species_clusters"
        self.image_clusters_dir = self.output_dir / "image_clusters"
        self.image_clusters_dir.mkdir(parents=True, exist_ok=True)

        # Load metadata
        print(f"Loading crop metadata...")
        with open(self.crops_dir / "metadata.json", 'r') as f:
            self.metadata = json.load(f)
        self.crops = self.metadata['crops']
        print(f"✓ Loaded {len(self.crops)} crops")

        # Load embeddings
        print(f"Loading embeddings...")
        self.embeddings = np.load(self.embeddings_dir / "embeddings_all.npy")
        print(f"✓ Loaded embeddings: {self.embeddings.shape}")

        # Load embedding index
        with open(self.embeddings_dir / "embeddings_index.json", 'r') as f:
            self.embedding_index = json.load(f)

        # Group crops by source_photo_id
        print(f"Grouping crops by source image...")
        self.crops_by_image = self._group_crops_by_image()
        print(f"✓ Found {len(self.crops_by_image)} unique source images")

    def _group_crops_by_image(self) -> dict:
        """
        Group crops by their source_photo_id.

        Returns:
            Dict: {photo_id: [crop_dict, crop_dict, ...]}
        """
        crops_by_image = defaultdict(list)
        for crop in self.crops:
            crops_by_image[crop['source_photo_id']].append(crop)
        return dict(crops_by_image)

    def process_all_images(self):
        """
        Main processing loop: cluster crops within each image.

        Returns:
            Path to summary.json
        """
        print("\n" + "=" * 60)
        print("PER-IMAGE CLUSTERING")
        print("=" * 60)

        stats = {
            "single_species_images": 0,
            "multi_species_images": 0,
            "single_species_crops": 0,
            "multi_species_crops": 0,
            "total_local_clusters": 0,
            "species_distribution": defaultdict(int),
        }

        # Process each image
        print(f"\nProcessing {len(self.crops_by_image)} images...")
        for photo_id, image_crops in tqdm(self.crops_by_image.items(), desc="Clustering images"):
            result = self.cluster_single_image(photo_id, image_crops)

            # Update stats
            if result['is_single_species']:
                stats['single_species_images'] += 1
                stats['single_species_crops'] += result['n_crops']
            else:
                stats['multi_species_images'] += 1
                stats['multi_species_crops'] += result['n_crops']

            stats['total_local_clusters'] += len(result['clusters'])

            # Count species
            for species in result['species_candidates']:
                stats['species_distribution'][species] += result['n_crops']

            # Save per-image result
            output_path = self.image_clusters_dir / f"{photo_id}.json"
            with open(output_path, 'w') as f:
                json.dump(result, f, indent=2)

        # Save summary
        summary_path = self._save_summary(stats)

        print("\n" + "=" * 60)
        print("✅ PER-IMAGE CLUSTERING COMPLETE")
        print("=" * 60)
        print(f"Total images: {len(self.crops_by_image)}")
        print(f"Single-species images: {stats['single_species_images']} ({stats['single_species_crops']} crops)")
        print(f"Multi-species images: {stats['multi_species_images']} ({stats['multi_species_crops']} crops)")
        print(f"Total local clusters: {stats['total_local_clusters']}")
        print(f"Output: {self.image_clusters_dir}")

        return summary_path

    def cluster_single_image(self, photo_id: str, crops: list) -> dict:
        """
        Cluster crops from one image.

        Args:
            photo_id: Source photo ID (e.g., "2015_1_1_00094")
            crops: List of crop metadata dicts for this image

        Returns:
            Dict with clustering results
        """
        # Extract species info from first crop (all crops from same image have same species_candidates)
        species_candidates = crops[0]['species_candidates']
        is_single_species = crops[0]['is_single_species']
        n_species = len(species_candidates)

        # Extract embeddings for these crops
        crop_ids = [c['crop_id'] for c in crops]
        crop_embeddings = self._extract_crop_embeddings(crop_ids)

        # Handle edge case: no species candidates (data quality issue)
        if n_species == 0:
            # Create a single cluster with "UNKNOWN" label
            clusters = [{
                "local_cluster_id": 0,
                "species_candidate": "UNKNOWN",
                "centroid": crop_embeddings.mean(axis=0).tolist(),
                "crop_ids": crop_ids,
                "size": len(crop_ids),
                "confidence": 0.0  # Zero confidence - no species info
            }]
            print(f"\n⚠️  Warning: Image {photo_id} has no species candidates")

        # Handle single-species case
        elif is_single_species or n_species == 1:
            # No clustering needed - assign all to species_candidates[0]
            clusters = [{
                "local_cluster_id": 0,
                "species_candidate": species_candidates[0],
                "centroid": crop_embeddings.mean(axis=0).tolist(),
                "crop_ids": crop_ids,
                "size": len(crop_ids),
                "confidence": 1.0
            }]

        # Handle edge case: single crop but multiple species
        elif len(crops) == 1:
            # Can't cluster 1 crop into N species - assign to first with low confidence
            clusters = [{
                "local_cluster_id": 0,
                "species_candidate": species_candidates[0],
                "centroid": crop_embeddings[0].tolist(),
                "crop_ids": crop_ids,
                "size": 1,
                "confidence": 0.5  # Low confidence - uncertain assignment
            }]

        # Handle edge case: fewer crops than species (can't cluster N crops into M>N groups)
        elif len(crops) < n_species:
            # Assign each crop to a separate cluster with first N species
            clusters = []
            for i in range(len(crops)):
                species = species_candidates[i] if i < len(species_candidates) else species_candidates[0]
                clusters.append({
                    "local_cluster_id": i,
                    "species_candidate": species,
                    "centroid": crop_embeddings[i].tolist(),
                    "crop_ids": [crop_ids[i]],
                    "size": 1,
                    "confidence": 0.3  # Low confidence - not enough crops for proper clustering
                })
            print(f"\n⚠️  Warning: Image {photo_id} has {len(crops)} crops but {n_species} species (under-sampled)")

        # Handle multi-species case
        else:
            # Run K-means clustering
            cluster_labels = self._run_kmeans(crop_embeddings, n_clusters=n_species)

            # Build clusters
            clusters = []
            for cluster_id in range(n_species):
                # Find crops in this cluster
                cluster_mask = (cluster_labels == cluster_id)
                cluster_crop_ids = [crop_ids[i] for i in range(len(crop_ids)) if cluster_mask[i]]
                cluster_embeddings = crop_embeddings[cluster_mask]

                # Compute centroid
                centroid = cluster_embeddings.mean(axis=0)

                # Assign species candidate (in order of cluster_id)
                species_candidate = species_candidates[cluster_id] if cluster_id < len(species_candidates) else species_candidates[-1]

                clusters.append({
                    "local_cluster_id": cluster_id,
                    "species_candidate": species_candidate,
                    "centroid": centroid.tolist(),
                    "crop_ids": cluster_crop_ids,
                    "size": len(cluster_crop_ids),
                    "confidence": 0.8  # Moderate confidence - clustering-based assignment
                })

        # Build result
        result = {
            "photo_id": photo_id,
            "n_crops": len(crops),
            "species_candidates": species_candidates,
            "is_single_species": is_single_species,
            "n_species": n_species,
            "clusters": clusters
        }

        return result

    def _run_kmeans(self, embeddings: np.ndarray, n_clusters: int) -> np.ndarray:
        """
        Run K-means clustering on embeddings.

        Uses StandardScaler + KMeans (pattern from clustering_service.py)

        Args:
            embeddings: (n_crops, embedding_dim) array
            n_clusters: Number of clusters (= number of species)

        Returns:
            Cluster labels (0 to n_clusters-1)
        """
        # Standardize features
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(embeddings)

        # Run K-means
        kmeans = KMeans(
            n_clusters=n_clusters,
            random_state=42,
            n_init=10,
            max_iter=300
        )
        labels = kmeans.fit_predict(X_scaled)

        return labels

    def _extract_crop_embeddings(self, crop_ids: list) -> np.ndarray:
        """
        Extract embeddings for specific crops.

        Uses embedding_index to map crop_id → array row.

        Args:
            crop_ids: List of crop IDs

        Returns:
            (n_crops, embedding_dim) array of embeddings
        """
        # Convert crop_ids to string keys (JSON stores as strings)
        indices = [int(self.embedding_index[str(cid)]) for cid in crop_ids]
        return self.embeddings[indices]

    def _save_summary(self, stats: dict) -> Path:
        """
        Save clustering summary statistics.

        Args:
            stats: Statistics dictionary

        Returns:
            Path to summary.json
        """
        summary = {
            "total_images_processed": len(self.crops_by_image),
            "total_crops": len(self.crops),
            "single_species_images": stats['single_species_images'],
            "multi_species_images": stats['multi_species_images'],
            "single_species_crops": stats['single_species_crops'],
            "multi_species_crops": stats['multi_species_crops'],
            "total_local_clusters": stats['total_local_clusters'],
            "unique_species": len(stats['species_distribution']),
            "species_distribution": dict(stats['species_distribution']),
            "generated_at": datetime.now().isoformat()
        }

        summary_path = self.output_dir / "summary.json"
        with open(summary_path, 'w') as f:
            json.dump(summary, f, indent=2)

        print(f"\n✓ Saved summary: {summary_path}")
        return summary_path


def main():
    """
    Main entry point for Stage 2.
    """
    import argparse

    parser = argparse.ArgumentParser(description='Stage 2: Per-image clustering')
    parser.add_argument('--crops-dir', type=str,
                        default='data/weak_supervision/bird_crops',
                        help='Path to bird_crops directory')
    parser.add_argument('--embeddings-dir', type=str,
                        default='data/weak_supervision/bird_crops/embeddings',
                        help='Path to embeddings directory')
    parser.add_argument('--output-dir', type=str,
                        default='data/weak_supervision/bird_crops',
                        help='Path to output directory')

    args = parser.parse_args()

    # Create clusterer
    clusterer = PerImageClusterer(
        crops_dir=args.crops_dir,
        embeddings_dir=args.embeddings_dir,
        output_dir=args.output_dir
    )

    # Run clustering
    clusterer.process_all_images()


if __name__ == '__main__':
    main()
