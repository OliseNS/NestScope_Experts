"""
Stage 3: Classify Multi-Species Images

For each multi-species image:
  1. Cluster crops into K groups (K = number of species candidates)
  2. Match clusters to species using Hungarian algorithm
     (optimal 1-to-1 matching based on similarity to ground truth prototypes)
  3. Reject outlier crops that don't match their assigned species well

Key improvement over old pipeline:
  OLD: cluster 0 → species[0], cluster 1 → species[1] (RANDOM — K-means IDs are arbitrary)
  NEW: Use cosine similarity to ground truth prototypes + Hungarian algorithm for OPTIMAL matching

Hungarian algorithm:
  Given N clusters and M species with prototypes, build a cost matrix where
  cost[i][j] = -similarity(cluster_i_centroid, species_j_prototype). Then
  scipy.optimize.linear_sum_assignment finds the assignment that minimizes
  total cost (= maximizes total similarity). This is guaranteed optimal.
"""

import sys
from pathlib import Path
import json
import numpy as np
from datetime import datetime
from collections import defaultdict
from tqdm import tqdm
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from scipy.optimize import linear_sum_assignment

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))


class MultiSpeciesClassifier:
    """
    Classifies bird crops in multi-species images using ground truth prototypes.
    """

    def __init__(self, crops_dir: str, embeddings_dir: str, prototypes_path: str,
                 outlier_sigma: float = 2.0):
        """
        Args:
            crops_dir: Path to bird_crops directory
            embeddings_dir: Path to embeddings directory
            prototypes_path: Path to ground_truth/prototypes.json from Stage 2
            outlier_sigma: Std deviations for per-crop outlier rejection
        """
        self.crops_dir = Path(crops_dir)
        self.embeddings_dir = Path(embeddings_dir)
        self.outlier_sigma = outlier_sigma

        # Load crop metadata
        print("Loading crop metadata...")
        with open(self.crops_dir / "metadata.json", 'r') as f:
            metadata = json.load(f)
        self.crops = metadata['crops']
        self.crops_by_id = {c['crop_id']: c for c in self.crops}
        print(f"  Loaded {len(self.crops)} crops")

        # Load embeddings
        print("Loading embeddings...")
        self.embeddings = np.load(self.embeddings_dir / "embeddings_all.npy")
        with open(self.embeddings_dir / "embeddings_index.json", 'r') as f:
            self.embedding_index = json.load(f)
        print(f"  Loaded embeddings: {self.embeddings.shape}")

        # Load prototypes
        print("Loading ground truth prototypes...")
        with open(prototypes_path, 'r') as f:
            proto_data = json.load(f)
        self.prototypes = proto_data['prototypes']
        # Convert centroids from lists to numpy arrays for fast computation
        self.prototype_centroids = {
            sp: np.array(p['centroid'])
            for sp, p in self.prototypes.items()
        }
        print(f"  Loaded {len(self.prototypes)} species prototypes")

        # Group crops by source_photo_id
        self.crops_by_image = defaultdict(list)
        for crop in self.crops:
            self.crops_by_image[crop['source_photo_id']].append(crop)

        # Output directories
        self.output_dir = self.crops_dir / "assignments"
        self.image_assignments_dir = self.output_dir / "image_assignments"
        self.image_assignments_dir.mkdir(parents=True, exist_ok=True)

    def _get_embeddings_batch(self, crop_ids: list) -> np.ndarray:
        """Get embeddings for multiple crops."""
        indices = [int(self.embedding_index[str(cid)]) for cid in crop_ids]
        return self.embeddings[indices]

    def classify_all_images(self, prototypes_override: dict = None) -> dict:
        """
        Main method: classify crops in all multi-species images.

        Args:
            prototypes_override: Optional dict of prototypes to use instead of
                                 the loaded ones (used during iterative refinement)

        Returns:
            Summary statistics
        """
        if prototypes_override is not None:
            self.prototypes = prototypes_override
            self.prototype_centroids = {
                sp: np.array(p['centroid'])
                for sp, p in self.prototypes.items()
            }

        print("\n" + "=" * 60)
        print("CLASSIFYING MULTI-SPECIES IMAGES")
        print("=" * 60)
        print(f"Available prototypes: {sorted(self.prototypes.keys())}")

        stats = {
            "total_images": 0,
            "total_crops": 0,
            "assigned_crops": 0,
            "excluded_crops": 0,
            "method_counts": {"hungarian": 0, "poe": 0, "ground_truth": 0},
            "species_counts": defaultdict(int),
        }

        all_assignments = {}  # crop_id → assignment info

        # Process single-species images first (ground truth — direct assignment)
        print("\nAssigning single-species images (ground truth)...")
        for photo_id, crops in tqdm(self.crops_by_image.items(), desc="Single-species"):
            if not crops[0].get('is_single_species', False):
                continue
            if len(crops[0].get('species_candidates', [])) != 1:
                continue

            species = crops[0]['species_candidates'][0]
            assignments = []
            for crop in crops:
                assignment = {
                    "crop_id": crop['crop_id'],
                    "species": species,
                    "confidence": 1.0,
                    "method": "ground_truth"
                }
                assignments.append(assignment)
                all_assignments[crop['crop_id']] = assignment
                stats['method_counts']['ground_truth'] += 1
                stats['species_counts'][species] += 1
                stats['assigned_crops'] += 1
                stats['total_crops'] += 1

            # Save per-image result
            result = {
                "photo_id": photo_id,
                "species_candidates": [species],
                "is_single_species": True,
                "assignments": assignments,
                "excluded": []
            }
            with open(self.image_assignments_dir / f"{photo_id}.json", 'w') as f:
                json.dump(result, f, indent=2)
            stats['total_images'] += 1

        # Process multi-species images
        print("\nClassifying multi-species images...")
        for photo_id, crops in tqdm(self.crops_by_image.items(), desc="Multi-species"):
            if crops[0].get('is_single_species', False):
                continue

            species_candidates = crops[0].get('species_candidates', [])
            if not species_candidates:
                continue

            result = self.classify_single_image(photo_id, crops, species_candidates)

            # Aggregate stats
            for a in result['assignments']:
                all_assignments[a['crop_id']] = a
                stats['method_counts'][a['method']] += 1
                stats['species_counts'][a['species']] += 1
                stats['assigned_crops'] += 1
            stats['excluded_crops'] += len(result['excluded'])
            stats['total_crops'] += len(crops)
            stats['total_images'] += 1

            # Save per-image result
            with open(self.image_assignments_dir / f"{photo_id}.json", 'w') as f:
                json.dump(result, f, indent=2)

        # Save global assignments
        self._save_all_assignments(all_assignments, stats)

        print("\n" + "=" * 60)
        print("CLASSIFICATION COMPLETE")
        print("=" * 60)
        print(f"Images processed: {stats['total_images']}")
        print(f"Crops assigned: {stats['assigned_crops']}")
        print(f"Crops excluded: {stats['excluded_crops']}")
        print(f"Methods: {dict(stats['method_counts'])}")
        print(f"Species: {len(stats['species_counts'])} unique")

        return stats, all_assignments

    def classify_single_image(self, photo_id: str, crops: list,
                               species_candidates: list) -> dict:
        """
        Classify crops from one multi-species image.

        Args:
            photo_id: Source photo ID
            crops: List of crop metadata for this image
            species_candidates: List of species codes expected in this image

        Returns:
            Dict with assignments and excluded crops
        """
        crop_ids = [c['crop_id'] for c in crops]
        n_crops = len(crop_ids)
        n_species = len(species_candidates)

        # Edge case: 1 crop, multiple species — can't cluster
        if n_crops == 1:
            return self._handle_single_crop(photo_id, crops[0], species_candidates)

        # Edge case: fewer crops than species
        if n_crops < n_species:
            return self._handle_too_few_crops(photo_id, crops, species_candidates)

        # Get embeddings
        crop_embeddings = self._get_embeddings_batch(crop_ids)

        # Run K-means to get K clusters
        cluster_labels = self._run_kmeans(crop_embeddings, n_species)

        # Compute cluster centroids
        cluster_centroids = []
        cluster_crop_ids = []
        for k in range(n_species):
            mask = cluster_labels == k
            cluster_embs = crop_embeddings[mask]
            centroid = cluster_embs.mean(axis=0)
            cluster_centroids.append(centroid)
            cluster_crop_ids.append([crop_ids[i] for i in range(n_crops) if mask[i]])

        cluster_centroids = np.array(cluster_centroids)

        # Split species into known (have prototype) and unknown
        known_species = [s for s in species_candidates if s in self.prototype_centroids]
        unknown_species = [s for s in species_candidates if s not in self.prototype_centroids]

        # Build assignment: cluster_idx → species
        cluster_to_species = {}
        used_clusters = set()

        # HUNGARIAN MATCHING for known species
        if known_species:
            cluster_to_species, used_clusters = self._hungarian_match(
                cluster_centroids, known_species
            )

        # PROCESS OF ELIMINATION for unknown species
        remaining_clusters = [i for i in range(n_species) if i not in used_clusters]
        for i, cluster_idx in enumerate(remaining_clusters):
            if i < len(unknown_species):
                cluster_to_species[cluster_idx] = unknown_species[i]

        # Build assignments with per-crop outlier rejection
        assignments = []
        excluded = []

        for cluster_idx, species in cluster_to_species.items():
            cids = cluster_crop_ids[cluster_idx]
            is_known = species in self.prototype_centroids

            if is_known:
                # Compare each crop to species prototype
                prototype = self.prototype_centroids[species]
                min_sim = self.prototypes[species]['min_acceptable_similarity']
                method = "hungarian"

                crop_embs = self._get_embeddings_batch(cids)
                sims = cosine_similarity(crop_embs, prototype.reshape(1, -1)).flatten()

                for cid, sim in zip(cids, sims):
                    if sim >= min_sim:
                        assignments.append({
                            "crop_id": cid,
                            "species": species,
                            "confidence": float(sim),
                            "method": method
                        })
                    else:
                        excluded.append({
                            "crop_id": cid,
                            "reason": "below_similarity_threshold",
                            "assigned_species": species,
                            "similarity": float(sim),
                            "threshold": float(min_sim)
                        })
            else:
                # No prototype — use intra-cluster cleaning only
                method = "poe"
                crop_embs = self._get_embeddings_batch(cids)
                centroid = crop_embs.mean(axis=0)
                sims = cosine_similarity(crop_embs, centroid.reshape(1, -1)).flatten()

                if len(sims) > 3:
                    mean_s = sims.mean()
                    std_s = sims.std()
                    threshold = mean_s - self.outlier_sigma * std_s
                else:
                    threshold = 0.0  # Can't compute reliable threshold with few crops

                for cid, sim in zip(cids, sims):
                    if sim >= threshold:
                        # Use raw intra-cluster similarity as confidence.
                        # This allows tight PoE clusters (sim >= 0.7) to bootstrap
                        # into soft prototypes during iterative refinement.
                        # PoE crops are still distinguishable by method="poe".
                        assignments.append({
                            "crop_id": cid,
                            "species": species,
                            "confidence": float(sim),
                            "method": method
                        })
                    else:
                        excluded.append({
                            "crop_id": cid,
                            "reason": "intra_cluster_outlier",
                            "assigned_species": species,
                            "similarity": float(sim),
                            "threshold": float(threshold)
                        })

        # Handle any unassigned clusters (shouldn't happen, but defensive)
        for cluster_idx in range(n_species):
            if cluster_idx not in cluster_to_species:
                for cid in cluster_crop_ids[cluster_idx]:
                    excluded.append({
                        "crop_id": cid,
                        "reason": "unmatched_cluster",
                        "cluster_idx": cluster_idx
                    })

        return {
            "photo_id": photo_id,
            "species_candidates": species_candidates,
            "is_single_species": False,
            "n_known_species": len(known_species),
            "n_unknown_species": len(unknown_species),
            "assignments": assignments,
            "excluded": excluded
        }

    def _hungarian_match(self, cluster_centroids: np.ndarray,
                          known_species: list) -> tuple:
        """
        Use Hungarian algorithm to optimally match clusters to species.

        The cost matrix is built using negative cosine similarity (because
        the algorithm minimizes cost, and we want to maximize similarity).

        Args:
            cluster_centroids: (K, dim) array of cluster centroids
            known_species: List of species codes that have prototypes

        Returns:
            (cluster_to_species dict, set of used cluster indices)
        """
        n_clusters = len(cluster_centroids)
        n_known = len(known_species)

        # Get prototype centroids for known species
        proto_centroids = np.array([
            self.prototype_centroids[s] for s in known_species
        ])

        # Build cost matrix: (n_clusters, n_known)
        # Similarity = cosine_similarity(cluster, prototype)
        # Cost = -similarity (because we minimize)
        sim_matrix = cosine_similarity(cluster_centroids, proto_centroids)
        cost_matrix = -sim_matrix

        # Hungarian algorithm — finds optimal 1-to-1 assignment
        # row_ind = cluster indices, col_ind = species indices
        row_ind, col_ind = linear_sum_assignment(cost_matrix)

        cluster_to_species = {}
        used_clusters = set()

        for r, c in zip(row_ind, col_ind):
            cluster_to_species[int(r)] = known_species[c]
            used_clusters.add(int(r))

        return cluster_to_species, used_clusters

    def _run_kmeans(self, embeddings: np.ndarray, n_clusters: int) -> np.ndarray:
        """Run K-means clustering on embeddings."""
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(embeddings)
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10, max_iter=300)
        return kmeans.fit_predict(X_scaled)

    def _handle_single_crop(self, photo_id: str, crop: dict,
                             species_candidates: list) -> dict:
        """Handle image with only 1 crop but multiple species candidates."""
        # If one species has a prototype, assign to the most similar one
        crop_emb = self._get_embeddings_batch([crop['crop_id']])
        best_species = None
        best_sim = -1

        for sp in species_candidates:
            if sp in self.prototype_centroids:
                sim = cosine_similarity(
                    crop_emb, self.prototype_centroids[sp].reshape(1, -1)
                )[0, 0]
                if sim > best_sim:
                    best_sim = sim
                    best_species = sp

        if best_species and best_sim >= self.prototypes[best_species]['min_acceptable_similarity']:
            return {
                "photo_id": photo_id,
                "species_candidates": species_candidates,
                "is_single_species": False,
                "assignments": [{
                    "crop_id": crop['crop_id'],
                    "species": best_species,
                    "confidence": float(best_sim),
                    "method": "hungarian"
                }],
                "excluded": []
            }
        else:
            # Can't confidently assign — exclude
            return {
                "photo_id": photo_id,
                "species_candidates": species_candidates,
                "is_single_species": False,
                "assignments": [],
                "excluded": [{
                    "crop_id": crop['crop_id'],
                    "reason": "single_crop_multi_species_ambiguous",
                    "best_species": best_species,
                    "best_similarity": float(best_sim) if best_sim > 0 else None
                }]
            }

    def _handle_too_few_crops(self, photo_id: str, crops: list,
                               species_candidates: list) -> dict:
        """Handle image with fewer crops than species candidates."""
        # Assign each crop to its best-matching prototype
        assignments = []
        excluded = []

        for crop in crops:
            crop_emb = self._get_embeddings_batch([crop['crop_id']])
            best_species = None
            best_sim = -1

            for sp in species_candidates:
                if sp in self.prototype_centroids:
                    sim = cosine_similarity(
                        crop_emb, self.prototype_centroids[sp].reshape(1, -1)
                    )[0, 0]
                    if sim > best_sim:
                        best_sim = sim
                        best_species = sp

            if best_species and best_sim >= self.prototypes[best_species]['min_acceptable_similarity']:
                assignments.append({
                    "crop_id": crop['crop_id'],
                    "species": best_species,
                    "confidence": float(best_sim),
                    "method": "hungarian"
                })
            else:
                excluded.append({
                    "crop_id": crop['crop_id'],
                    "reason": "too_few_crops_ambiguous",
                    "best_species": best_species,
                    "best_similarity": float(best_sim) if best_sim > 0 else None
                })

        return {
            "photo_id": photo_id,
            "species_candidates": species_candidates,
            "is_single_species": False,
            "assignments": assignments,
            "excluded": excluded
        }

    def _save_all_assignments(self, all_assignments: dict, stats: dict):
        """Save global assignment summary."""
        summary = {
            "total_images": stats['total_images'],
            "total_crops": stats['total_crops'],
            "assigned_crops": stats['assigned_crops'],
            "excluded_crops": stats['excluded_crops'],
            "assignment_rate": stats['assigned_crops'] / max(stats['total_crops'], 1),
            "method_counts": dict(stats['method_counts']),
            "species_counts": dict(stats['species_counts']),
            "generated_at": datetime.now().isoformat()
        }

        summary_path = self.output_dir / "classification_summary.json"
        with open(summary_path, 'w') as f:
            json.dump(summary, f, indent=2)

        print(f"\nSaved summary: {summary_path}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Stage 3: Classify multi-species images')
    parser.add_argument('--crops-dir', type=str,
                        default='data/weak_supervision/bird_crops',
                        help='Path to bird_crops directory')
    parser.add_argument('--embeddings-dir', type=str,
                        default='data/weak_supervision/bird_crops/embeddings',
                        help='Path to embeddings directory')
    parser.add_argument('--prototypes', type=str,
                        default='data/weak_supervision/bird_crops/ground_truth/prototypes.json',
                        help='Path to ground truth prototypes from Stage 2')
    parser.add_argument('--outlier-sigma', type=float, default=2.0,
                        help='Std devs for per-crop outlier rejection')

    args = parser.parse_args()

    classifier = MultiSpeciesClassifier(
        crops_dir=args.crops_dir,
        embeddings_dir=args.embeddings_dir,
        prototypes_path=args.prototypes,
        outlier_sigma=args.outlier_sigma
    )
    classifier.classify_all_images()


if __name__ == '__main__':
    main()
