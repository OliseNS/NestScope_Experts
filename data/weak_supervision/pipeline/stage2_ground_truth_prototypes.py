"""
Stage 2: Build Ground Truth Prototypes

Uses single-species images as ground truth to build clean species prototypes.
These prototypes anchor all subsequent clustering decisions.

Key concept:
  If an image has exactly 1 species in the database, ALL bird crops from that
  image are that species. We aggregate these into a "prototype" — a mean
  embedding vector that represents what the species looks like in embedding space.

Two levels of outlier cleaning:
  1. INTRA-IMAGE: Within each single-species image, remove crops that look
     nothing like the others (detection errors: rocks, water, occluded birds)
  2. INTER-IMAGE: Across all images for a species, remove crops that are
     far from the global centroid (unusual angles, lighting artifacts)
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


class GroundTruthBuilder:
    """
    Builds species prototypes from single-species images.

    A "prototype" is a cleaned centroid embedding for a species, computed from
    crops that we are confident about (because they came from single-species images).
    """

    def __init__(self, crops_dir: str, embeddings_dir: str, image_metadata_path: str,
                 intra_image_threshold: float = 2.0, inter_image_threshold: float = 2.0,
                 acceptance_sigma: float = 1.5):
        """
        Args:
            crops_dir: Path to bird_crops directory (contains metadata.json)
            embeddings_dir: Path to embeddings directory (contains embeddings_all.npy)
            image_metadata_path: Path to image_metadata.json
            intra_image_threshold: Std deviations for intra-image outlier removal
            inter_image_threshold: Std deviations for inter-image outlier removal
            acceptance_sigma: Std deviations below mean for min acceptable similarity
        """
        self.crops_dir = Path(crops_dir)
        self.embeddings_dir = Path(embeddings_dir)
        self.intra_threshold = intra_image_threshold
        self.inter_threshold = inter_image_threshold
        self.acceptance_sigma = acceptance_sigma

        # Load crop metadata
        print("Loading crop metadata...")
        with open(self.crops_dir / "metadata.json", 'r') as f:
            metadata = json.load(f)
        self.crops = metadata['crops']
        self.crops_by_id = {c['crop_id']: c for c in self.crops}
        print(f"  Loaded {len(self.crops)} crops")

        # Load image metadata (photo_id → species info)
        print("Loading image metadata...")
        with open(image_metadata_path, 'r') as f:
            self.image_metadata = json.load(f)
        print(f"  Loaded {len(self.image_metadata)} image records")

        # Load embeddings
        print("Loading embeddings...")
        self.embeddings = np.load(self.embeddings_dir / "embeddings_all.npy")
        with open(self.embeddings_dir / "embeddings_index.json", 'r') as f:
            self.embedding_index = json.load(f)
        print(f"  Loaded embeddings: {self.embeddings.shape}")

        # Group crops by source_photo_id
        self.crops_by_image = defaultdict(list)
        for crop in self.crops:
            self.crops_by_image[crop['source_photo_id']].append(crop)

        # Output directory
        self.output_dir = self.crops_dir / "ground_truth"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _get_embedding(self, crop_id: int) -> np.ndarray:
        """Get embedding vector for a crop by its ID."""
        idx = int(self.embedding_index[str(crop_id)])
        return self.embeddings[idx]

    def _get_embeddings_batch(self, crop_ids: list) -> np.ndarray:
        """Get embeddings for multiple crops. Returns (N, dim) array."""
        indices = [int(self.embedding_index[str(cid)]) for cid in crop_ids]
        return self.embeddings[indices]

    def find_single_species_images(self) -> dict:
        """
        Find all single-species images and group their crops by species.

        Returns:
            Dict: {species_code: [(photo_id, [crop_ids]), ...]}
        """
        species_images = defaultdict(list)

        for photo_id, crops in self.crops_by_image.items():
            # Check if this image is single-species
            if not crops[0].get('is_single_species', False):
                continue
            if len(crops[0].get('species_candidates', [])) != 1:
                continue

            species = crops[0]['species_candidates'][0]
            crop_ids = [c['crop_id'] for c in crops]
            species_images[species].append((photo_id, crop_ids))

        return dict(species_images)

    def clean_intra_image(self, crop_ids: list) -> list:
        """
        Remove outlier crops within a single image.

        Strategy: Compute mean pairwise similarity. Crops whose average
        similarity to all other crops is very low are likely detection
        errors (not birds, or very different objects).

        Args:
            crop_ids: Crop IDs from a single image

        Returns:
            Cleaned list of crop IDs (outliers removed)
        """
        if len(crop_ids) <= 3:
            # Too few crops to reliably detect outliers
            return crop_ids

        embeddings = self._get_embeddings_batch(crop_ids)

        # Compute pairwise cosine similarities
        sim_matrix = cosine_similarity(embeddings)

        # For each crop, compute its mean similarity to all others
        # (exclude self-similarity on diagonal)
        np.fill_diagonal(sim_matrix, 0)
        mean_sims = sim_matrix.sum(axis=1) / (len(crop_ids) - 1)

        # Compute threshold
        global_mean = mean_sims.mean()
        global_std = mean_sims.std()

        if global_std < 1e-6:
            # All crops are very similar — no outliers
            return crop_ids

        threshold = global_mean - self.intra_threshold * global_std

        # Keep crops above threshold
        clean_ids = [cid for cid, sim in zip(crop_ids, mean_sims) if sim >= threshold]
        return clean_ids

    def clean_inter_image(self, crop_ids: list) -> tuple:
        """
        Remove outlier crops across all images for a species.

        Strategy: Compute global centroid, remove crops that are too
        far from it. This catches unusual lighting, odd angles, or
        crops that slipped through intra-image cleaning.

        Args:
            crop_ids: All crop IDs for a species (across all images)

        Returns:
            (clean_ids, centroid, mean_sim, std_sim)
        """
        if len(crop_ids) <= 5:
            embeddings = self._get_embeddings_batch(crop_ids)
            centroid = embeddings.mean(axis=0)
            return crop_ids, centroid, 1.0, 0.0

        embeddings = self._get_embeddings_batch(crop_ids)

        # Compute initial centroid
        centroid = embeddings.mean(axis=0)

        # Compute similarities to centroid
        sims = cosine_similarity(embeddings, centroid.reshape(1, -1)).flatten()

        mean_sim = sims.mean()
        std_sim = sims.std()

        if std_sim < 1e-6:
            return crop_ids, centroid, float(mean_sim), float(std_sim)

        # Remove outliers
        threshold = mean_sim - self.inter_threshold * std_sim
        mask = sims >= threshold
        clean_ids = [cid for cid, keep in zip(crop_ids, mask) if keep]

        # Recompute centroid from cleaned set
        clean_embeddings = self._get_embeddings_batch(clean_ids)
        centroid = clean_embeddings.mean(axis=0)

        # Recompute stats with cleaned centroid
        clean_sims = cosine_similarity(clean_embeddings, centroid.reshape(1, -1)).flatten()
        mean_sim = float(clean_sims.mean())
        std_sim = float(clean_sims.std())

        return clean_ids, centroid, mean_sim, std_sim

    def build_prototypes(self) -> dict:
        """
        Main method: build ground truth prototypes for all species
        that have single-species images.

        Returns:
            Dict of species prototypes
        """
        print("\n" + "=" * 60)
        print("BUILDING GROUND TRUTH PROTOTYPES")
        print("=" * 60)

        # Step 1: Find single-species images
        species_images = self.find_single_species_images()
        print(f"\nFound {len(species_images)} species with single-species images:")
        for sp, images in sorted(species_images.items(), key=lambda x: -len(x[1])):
            total_crops = sum(len(cids) for _, cids in images)
            print(f"  {sp}: {len(images)} images, {total_crops} crops")

        prototypes = {}
        excluded_log = {}
        total_excluded = 0
        total_kept = 0

        # Step 2: Process each species
        for species_code in tqdm(sorted(species_images.keys()), desc="Building prototypes"):
            images = species_images[species_code]
            original_crop_ids = []
            for _, cids in images:
                original_crop_ids.extend(cids)
            n_original = len(original_crop_ids)

            # Intra-image cleaning
            cleaned_per_image = []
            intra_excluded = []
            for photo_id, crop_ids in images:
                clean = self.clean_intra_image(crop_ids)
                cleaned_per_image.extend(clean)
                excluded = set(crop_ids) - set(clean)
                for cid in excluded:
                    intra_excluded.append({
                        "crop_id": cid,
                        "photo_id": photo_id,
                        "reason": "intra_image_outlier"
                    })

            # Inter-image cleaning
            clean_ids, centroid, mean_sim, std_sim = self.clean_inter_image(cleaned_per_image)
            inter_excluded = []
            for cid in set(cleaned_per_image) - set(clean_ids):
                inter_excluded.append({
                    "crop_id": cid,
                    "reason": "inter_image_outlier"
                })

            n_kept = len(clean_ids)
            n_excluded = n_original - n_kept
            total_excluded += n_excluded
            total_kept += n_kept

            # Compute min acceptable similarity for future matching
            min_acceptable = mean_sim - self.acceptance_sigma * std_sim

            # Store prototype
            prototypes[species_code] = {
                "species_code": species_code,
                "centroid": centroid.tolist(),
                "crop_ids": clean_ids,
                "n_crops": n_kept,
                "n_original": n_original,
                "n_excluded": n_excluded,
                "n_images": len(images),
                "mean_similarity": mean_sim,
                "std_similarity": std_sim,
                "min_acceptable_similarity": float(min_acceptable),
                "source": "ground_truth"
            }

            # Store exclusion log
            excluded_log[species_code] = {
                "intra_image_excluded": intra_excluded,
                "inter_image_excluded": inter_excluded,
                "total_excluded": n_excluded
            }

        # Save prototypes
        prototypes_path = self.output_dir / "prototypes.json"
        prototypes_data = {
            "prototypes": prototypes,
            "metadata": {
                "total_species": len(prototypes),
                "total_crops_kept": total_kept,
                "total_crops_excluded": total_excluded,
                "intra_image_threshold": self.intra_threshold,
                "inter_image_threshold": self.inter_threshold,
                "acceptance_sigma": self.acceptance_sigma,
                "generated_at": datetime.now().isoformat()
            }
        }
        with open(prototypes_path, 'w') as f:
            json.dump(prototypes_data, f, indent=2)

        # Save exclusion log
        excluded_path = self.output_dir / "excluded_crops.json"
        with open(excluded_path, 'w') as f:
            json.dump(excluded_log, f, indent=2)

        # Print summary
        print("\n" + "=" * 60)
        print("GROUND TRUTH PROTOTYPES BUILT")
        print("=" * 60)
        print(f"Species with prototypes: {len(prototypes)}")
        print(f"Total crops kept: {total_kept}")
        print(f"Total crops excluded: {total_excluded} ({100*total_excluded/(total_kept+total_excluded):.1f}%)")
        print(f"\nPer-species summary:")
        for sp, proto in sorted(prototypes.items()):
            print(f"  {sp}: {proto['n_crops']}/{proto['n_original']} crops kept "
                  f"(mean_sim={proto['mean_similarity']:.3f}, "
                  f"min_accept={proto['min_acceptable_similarity']:.3f})")
        print(f"\nOutput: {prototypes_path}")

        return prototypes


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Stage 2: Build ground truth prototypes')
    parser.add_argument('--crops-dir', type=str,
                        default='data/weak_supervision/bird_crops',
                        help='Path to bird_crops directory')
    parser.add_argument('--embeddings-dir', type=str,
                        default='data/weak_supervision/bird_crops/embeddings',
                        help='Path to embeddings directory')
    parser.add_argument('--image-metadata', type=str,
                        default='data/weak_supervision/image_metadata.json',
                        help='Path to image_metadata.json')
    parser.add_argument('--intra-threshold', type=float, default=2.0,
                        help='Std devs for intra-image outlier removal')
    parser.add_argument('--inter-threshold', type=float, default=2.0,
                        help='Std devs for inter-image outlier removal')
    parser.add_argument('--acceptance-sigma', type=float, default=1.5,
                        help='Std devs below mean for min acceptable similarity')

    args = parser.parse_args()

    builder = GroundTruthBuilder(
        crops_dir=args.crops_dir,
        embeddings_dir=args.embeddings_dir,
        image_metadata_path=args.image_metadata,
        intra_image_threshold=args.intra_threshold,
        inter_image_threshold=args.inter_threshold,
        acceptance_sigma=args.acceptance_sigma
    )
    builder.build_prototypes()


if __name__ == '__main__':
    main()
