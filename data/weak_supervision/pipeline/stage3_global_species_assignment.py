"""
Stage 3: Global Species Assignment (Cross-Image Resolution)

Compare cluster centroids across images to validate species assignments and detect outliers.
"""

import sys
from pathlib import Path
import json
import numpy as np
from datetime import datetime
from collections import defaultdict
from tqdm import tqdm
from sklearn.metrics.pairwise import cosine_similarity

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))


class GlobalSpeciesResolver:
    """
    Resolves species assignments across images using cluster centroids.

    Strategy:
    1. Collect all cluster centroids from Stage 2
    2. Group centroids by species_candidate label
    3. For each species, compute mean centroid and similarity scores
    4. Detect outliers (clusters that don't match their species well)
    5. Assign confidence scores
    """

    def __init__(self, image_clusters_dir: str, output_dir: str):
        """
        Args:
            image_clusters_dir: Path to image_clusters directory from Stage 2
            output_dir: Path to output directory
        """
        self.image_clusters_dir = Path(image_clusters_dir)
        self.output_dir = Path(output_dir)

        # Load all per-image cluster files
        print(f"Loading per-image cluster files...")
        self.image_clusters = self._load_all_image_clusters()
        print(f"✓ Loaded {len(self.image_clusters)} image cluster files")

    def _load_all_image_clusters(self) -> list:
        """
        Load all per-image cluster JSON files.

        Returns:
            List of cluster result dicts
        """
        cluster_files = list(self.image_clusters_dir.glob("*.json"))
        image_clusters = []

        for fpath in cluster_files:
            with open(fpath, 'r') as f:
                image_clusters.append(json.load(f))

        return image_clusters

    def build_global_cluster_map(self):
        """
        Main processing: compare clusters across images.

        Returns:
            Path to global_cluster_map.json
        """
        print("\n" + "=" * 60)
        print("GLOBAL SPECIES RESOLUTION")
        print("=" * 60)

        # Collect all clusters
        print("\nCollecting clusters...")
        all_clusters = []
        for img_result in self.image_clusters:
            for cluster in img_result['clusters']:
                # Add photo_id to cluster for reference
                cluster_with_id = {
                    **cluster,
                    "photo_id": img_result['photo_id']
                }
                all_clusters.append(cluster_with_id)

        print(f"✓ Total clusters: {len(all_clusters)}")

        # Group by species_candidate
        print("Grouping by species...")
        clusters_by_species = defaultdict(list)
        for cluster in all_clusters:
            species = cluster['species_candidate']
            clusters_by_species[species].append(cluster)

        print(f"✓ Unique species: {len(clusters_by_species)}")

        # Compute species-level statistics
        print("\nComputing species statistics...")
        species_summary = {}
        cluster_assignments = {}

        for species_code in tqdm(clusters_by_species.keys(), desc="Analyzing species"):
            species_result = self.compute_species_centroids(
                species_code,
                clusters_by_species[species_code]
            )

            species_summary[species_code] = species_result['summary']

            # Add cluster assignments
            for cluster_info in species_result['clusters']:
                cluster_key = f"{cluster_info['photo_id']}_cluster_{cluster_info['local_cluster_id']}"
                cluster_assignments[cluster_key] = cluster_info

        # Save global cluster map
        output_path = self._save_global_map(species_summary, cluster_assignments)

        print("\n" + "=" * 60)
        print("✅ GLOBAL SPECIES RESOLUTION COMPLETE")
        print("=" * 60)
        print(f"Species analyzed: {len(species_summary)}")
        print(f"Total clusters: {len(cluster_assignments)}")
        print(f"Output: {output_path}")

        return output_path

    def compute_species_centroids(self, species_code: str, clusters: list) -> dict:
        """
        For a given species, compute consistency metrics across all its clusters.

        Args:
            species_code: Species code (e.g., "GREG")
            clusters: List of cluster dicts for this species

        Returns:
            Dict with species summary and per-cluster info
        """
        # Extract centroids
        centroids = np.array([c['centroid'] for c in clusters])
        n_clusters = len(clusters)
        total_crops = sum(c['size'] for c in clusters)

        # Compute mean centroid (species prototype)
        mean_centroid = centroids.mean(axis=0)

        # Compute similarities to mean
        similarities = cosine_similarity(centroids, mean_centroid.reshape(1, -1)).flatten()

        # Compute consistency score (higher = more consistent)
        consistency_score = float(similarities.mean())
        std_similarity = float(similarities.std())

        # Detect outliers (>2 std deviations below mean)
        outlier_threshold = similarities.mean() - 2 * std_similarity
        outliers = similarities < outlier_threshold

        # Build per-cluster info
        cluster_infos = []
        for i, cluster in enumerate(clusters):
            cluster_info = {
                "photo_id": cluster['photo_id'],
                "local_cluster_id": cluster['local_cluster_id'],
                "assigned_species": species_code,
                "confidence": float(similarities[i]),
                "similarity_to_species_mean": float(similarities[i]),
                "is_outlier": bool(outliers[i]),
                "crop_ids": cluster['crop_ids'],
                "size": cluster['size']
            }
            cluster_infos.append(cluster_info)

        # Build result
        result = {
            "summary": {
                "species_code": species_code,
                "total_clusters": n_clusters,
                "total_crops": total_crops,
                "mean_centroid": mean_centroid.tolist(),
                "consistency_score": consistency_score,
                "std_similarity": std_similarity,
                "outlier_clusters": int(outliers.sum()),
                "min_similarity": float(similarities.min()),
                "max_similarity": float(similarities.max())
            },
            "clusters": cluster_infos
        }

        return result

    def _save_global_map(self, species_summary: dict, cluster_assignments: dict) -> Path:
        """
        Save global cluster map to JSON.

        Args:
            species_summary: Species-level statistics
            cluster_assignments: Per-cluster assignments

        Returns:
            Path to global_cluster_map.json
        """
        global_map = {
            "species_summary": species_summary,
            "cluster_assignments": cluster_assignments,
            "metadata": {
                "total_species": len(species_summary),
                "total_clusters": len(cluster_assignments),
                "generated_at": datetime.now().isoformat()
            }
        }

        output_path = self.output_dir / "global_cluster_map.json"
        with open(output_path, 'w') as f:
            json.dump(global_map, f, indent=2)

        print(f"\n✓ Saved global cluster map: {output_path}")
        return output_path


def main():
    """
    Main entry point for Stage 3.
    """
    import argparse

    parser = argparse.ArgumentParser(description='Stage 3: Global species resolution')
    parser.add_argument('--image-clusters-dir', type=str,
                        default='data/weak_supervision/bird_crops/species_clusters/image_clusters',
                        help='Path to image_clusters directory from Stage 2')
    parser.add_argument('--output-dir', type=str,
                        default='data/weak_supervision/bird_crops/species_clusters',
                        help='Path to output directory')

    args = parser.parse_args()

    # Create resolver
    resolver = GlobalSpeciesResolver(
        image_clusters_dir=args.image_clusters_dir,
        output_dir=args.output_dir
    )

    # Build global map
    resolver.build_global_cluster_map()


if __name__ == '__main__':
    main()
