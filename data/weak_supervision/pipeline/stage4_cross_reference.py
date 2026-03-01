"""
Stage 4: Cross-Reference Validation & Iterative Refinement

This stage orchestrates the iterative process:
  1. Classify all multi-species images using current prototypes
  2. Expand prototypes using high-confidence assignments
  3. Reclassify and repeat until convergence

Key insight — cascading coverage:
  Not all 35 species have single-species images. But through process of
  elimination, we bootstrap prototypes for unknown species:

    Round 0: ~8-12 species from single-species images
    Round 1: PoE gives soft prototypes for ~22 more species
    Round 2: Re-classify with expanded prototypes → covers all 35

  This cascading effect is WHY iterative refinement works — each round
  unlocks more species prototypes, which enable better matching in the
  next round.

Quality controls:
  - Ground truth crops are NEVER removed from prototypes
  - New crops must have confidence >= 0.7 to be included in prototype expansion
  - Soft prototypes (from PoE) require minimum 10 crops
  - Convergence detected when < 1% of assignments change between rounds
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

from data.weak_supervision.pipeline.stage3_classify_multi_species import MultiSpeciesClassifier


class CrossReferenceValidator:
    """
    Iteratively refines species prototypes and assignments.
    """

    def __init__(self, crops_dir: str, embeddings_dir: str,
                 prototypes_path: str, image_metadata_path: str,
                 max_rounds: int = 5,
                 expansion_confidence: float = 0.7,
                 min_soft_prototype_crops: int = 10,
                 convergence_threshold: float = 0.01):
        """
        Args:
            crops_dir: Path to bird_crops directory
            embeddings_dir: Path to embeddings directory
            prototypes_path: Path to ground truth prototypes from Stage 2
            image_metadata_path: Path to image_metadata.json
            max_rounds: Maximum refinement rounds
            expansion_confidence: Min confidence for crops to be included in prototypes
            min_soft_prototype_crops: Min crops needed to create a soft prototype
            convergence_threshold: Fraction of assignment changes to consider converged
        """
        self.crops_dir = Path(crops_dir)
        self.embeddings_dir = Path(embeddings_dir)
        self.max_rounds = max_rounds
        self.expansion_confidence = expansion_confidence
        self.min_soft_prototype_crops = min_soft_prototype_crops
        self.convergence_threshold = convergence_threshold

        # Load ground truth prototypes
        print("Loading ground truth prototypes...")
        with open(prototypes_path, 'r') as f:
            proto_data = json.load(f)
        self.ground_truth_prototypes = proto_data['prototypes']
        print(f"  Ground truth species: {sorted(self.ground_truth_prototypes.keys())}")

        # Load embeddings
        print("Loading embeddings...")
        self.embeddings = np.load(self.embeddings_dir / "embeddings_all.npy")
        with open(self.embeddings_dir / "embeddings_index.json", 'r') as f:
            self.embedding_index = json.load(f)

        # Load crop metadata
        with open(self.crops_dir / "metadata.json", 'r') as f:
            metadata = json.load(f)
        self.crops = metadata['crops']

        # Initialize classifier (will be reused each round with updated prototypes)
        self.classifier = MultiSpeciesClassifier(
            crops_dir=str(crops_dir),
            embeddings_dir=str(embeddings_dir),
            prototypes_path=prototypes_path
        )

        # Output directory
        self.output_dir = self.crops_dir / "assignments"
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Refinement log
        self.round_logs = []

    def _get_embeddings_batch(self, crop_ids: list) -> np.ndarray:
        """Get embeddings for multiple crops."""
        indices = [int(self.embedding_index[str(cid)]) for cid in crop_ids]
        return self.embeddings[indices]

    def run_iterative_refinement(self):
        """
        Main method: run iterative refinement until convergence.

        Returns:
            Final assignments dict and final prototypes
        """
        print("\n" + "=" * 60)
        print("ITERATIVE CROSS-REFERENCE REFINEMENT")
        print("=" * 60)

        current_prototypes = dict(self.ground_truth_prototypes)
        previous_assignments = None

        for round_num in range(self.max_rounds):
            print(f"\n{'─' * 40}")
            print(f"ROUND {round_num + 1}/{self.max_rounds}")
            print(f"{'─' * 40}")
            print(f"Active prototypes: {len(current_prototypes)} species")

            # Run classification with current prototypes
            stats, assignments = self.classifier.classify_all_images(
                prototypes_override=current_prototypes
            )

            # Check convergence
            if previous_assignments is not None:
                n_changed = self._count_assignment_changes(
                    previous_assignments, assignments
                )
                change_rate = n_changed / max(len(assignments), 1)
                print(f"\nAssignment changes: {n_changed} ({100*change_rate:.2f}%)")

                if change_rate < self.convergence_threshold:
                    print(f"CONVERGED (< {100*self.convergence_threshold:.1f}% change)")
                    self._log_round(round_num + 1, stats, current_prototypes,
                                    n_changed, converged=True)
                    break
            else:
                n_changed = len(assignments)
                change_rate = 1.0

            self._log_round(round_num + 1, stats, current_prototypes,
                            n_changed, converged=False)

            # Expand prototypes with high-confidence assignments
            current_prototypes = self._expand_prototypes(
                current_prototypes, assignments
            )

            previous_assignments = assignments

        else:
            print(f"\nReached max rounds ({self.max_rounds})")

        # Save final outputs
        final_path = self._save_final_outputs(assignments, current_prototypes)

        print("\n" + "=" * 60)
        print("ITERATIVE REFINEMENT COMPLETE")
        print("=" * 60)
        print(f"Rounds: {len(self.round_logs)}")
        print(f"Final prototypes: {len(current_prototypes)} species")
        print(f"Final assigned crops: {stats['assigned_crops']}")
        print(f"Final excluded crops: {stats['excluded_crops']}")
        print(f"Output: {final_path}")

        return assignments, current_prototypes

    def _expand_prototypes(self, current_prototypes: dict,
                            assignments: dict) -> dict:
        """
        Expand prototypes using high-confidence assignments.

        Rules:
        1. Ground truth crops are ALWAYS kept (never removed)
        2. New crops must have confidence >= expansion_confidence
        3. New species get soft prototypes if >= min_soft_prototype_crops

        Args:
            current_prototypes: Current prototype dict
            assignments: Dict of crop_id → assignment info

        Returns:
            Expanded prototype dict
        """
        print("\nExpanding prototypes...")

        # Group assignments by species
        species_crops = defaultdict(list)
        for crop_id, assignment in assignments.items():
            if assignment['confidence'] >= self.expansion_confidence:
                species_crops[assignment['species']].append({
                    'crop_id': crop_id,
                    'confidence': assignment['confidence'],
                    'method': assignment['method']
                })

        expanded = {}
        new_species_count = 0

        for species_code, high_conf_crops in species_crops.items():
            if species_code in self.ground_truth_prototypes:
                # Species has ground truth — merge with ground truth weighted higher
                gt_proto = self.ground_truth_prototypes[species_code]
                gt_crop_ids = gt_proto['crop_ids']
                new_crop_ids = [c['crop_id'] for c in high_conf_crops
                                if c['crop_id'] not in set(gt_crop_ids)]

                if not new_crop_ids:
                    # No new crops — keep ground truth prototype as-is
                    expanded[species_code] = dict(gt_proto)
                    continue

                # Compute weighted centroid: ground truth weighted 2x
                gt_embs = self._get_embeddings_batch(gt_crop_ids)
                new_embs = self._get_embeddings_batch(new_crop_ids)

                # Weight ground truth embeddings 2x by duplicating
                weighted_embs = np.vstack([gt_embs, gt_embs, new_embs])
                new_centroid = weighted_embs.mean(axis=0)

                # Recompute similarity stats
                all_crop_ids = gt_crop_ids + new_crop_ids
                all_embs = self._get_embeddings_batch(all_crop_ids)
                sims = cosine_similarity(
                    all_embs, new_centroid.reshape(1, -1)
                ).flatten()

                mean_sim = float(sims.mean())
                std_sim = float(sims.std())

                expanded[species_code] = {
                    "species_code": species_code,
                    "centroid": new_centroid.tolist(),
                    "crop_ids": all_crop_ids,
                    "n_crops": len(all_crop_ids),
                    "n_original": gt_proto['n_original'],
                    "n_excluded": gt_proto['n_excluded'],
                    "n_images": gt_proto['n_images'],
                    "mean_similarity": mean_sim,
                    "std_similarity": std_sim,
                    "min_acceptable_similarity": mean_sim - 1.5 * std_sim,
                    "source": "ground_truth_expanded"
                }

            elif species_code in current_prototypes:
                # Species has soft prototype from previous round — update
                old_proto = current_prototypes[species_code]
                new_crop_ids = [c['crop_id'] for c in high_conf_crops]

                if len(new_crop_ids) < self.min_soft_prototype_crops:
                    expanded[species_code] = dict(old_proto)
                    continue

                embs = self._get_embeddings_batch(new_crop_ids)
                centroid = embs.mean(axis=0)
                sims = cosine_similarity(embs, centroid.reshape(1, -1)).flatten()

                mean_sim = float(sims.mean())
                std_sim = float(sims.std())

                expanded[species_code] = {
                    "species_code": species_code,
                    "centroid": centroid.tolist(),
                    "crop_ids": new_crop_ids,
                    "n_crops": len(new_crop_ids),
                    "n_original": len(new_crop_ids),
                    "n_excluded": 0,
                    "n_images": 0,
                    "mean_similarity": mean_sim,
                    "std_similarity": std_sim,
                    "min_acceptable_similarity": mean_sim - 1.5 * std_sim,
                    "source": "soft_prototype_updated"
                }

            else:
                # NEW species — create soft prototype if enough crops
                new_crop_ids = [c['crop_id'] for c in high_conf_crops]

                if len(new_crop_ids) < self.min_soft_prototype_crops:
                    print(f"  {species_code}: only {len(new_crop_ids)} crops, "
                          f"need {self.min_soft_prototype_crops} — skipping")
                    continue

                embs = self._get_embeddings_batch(new_crop_ids)
                centroid = embs.mean(axis=0)
                sims = cosine_similarity(embs, centroid.reshape(1, -1)).flatten()

                mean_sim = float(sims.mean())
                std_sim = float(sims.std())

                expanded[species_code] = {
                    "species_code": species_code,
                    "centroid": centroid.tolist(),
                    "crop_ids": new_crop_ids,
                    "n_crops": len(new_crop_ids),
                    "n_original": len(new_crop_ids),
                    "n_excluded": 0,
                    "n_images": 0,
                    "mean_similarity": mean_sim,
                    "std_similarity": std_sim,
                    "min_acceptable_similarity": mean_sim - 1.5 * std_sim,
                    "source": "soft_prototype_new"
                }
                new_species_count += 1
                print(f"  NEW soft prototype: {species_code} ({len(new_crop_ids)} crops)")

        # Keep any existing prototypes that didn't get new assignments
        for sp, proto in current_prototypes.items():
            if sp not in expanded:
                expanded[sp] = dict(proto)

        print(f"  Expanded prototypes: {len(expanded)} species "
              f"(+{new_species_count} new)")

        return expanded

    def _count_assignment_changes(self, old_assignments: dict,
                                   new_assignments: dict) -> int:
        """Count how many crop assignments changed between rounds."""
        changes = 0
        all_crop_ids = set(old_assignments.keys()) | set(new_assignments.keys())

        for crop_id in all_crop_ids:
            old = old_assignments.get(crop_id, {}).get('species')
            new = new_assignments.get(crop_id, {}).get('species')
            if old != new:
                changes += 1

        return changes

    def _log_round(self, round_num: int, stats: dict, prototypes: dict,
                    n_changed: int, converged: bool):
        """Log round statistics."""
        log_entry = {
            "round": round_num,
            "n_prototypes": len(prototypes),
            "prototype_species": sorted(prototypes.keys()),
            "assigned_crops": stats['assigned_crops'],
            "excluded_crops": stats['excluded_crops'],
            "method_counts": dict(stats['method_counts']),
            "n_changed": n_changed,
            "converged": converged,
            "timestamp": datetime.now().isoformat()
        }
        self.round_logs.append(log_entry)

    def _save_final_outputs(self, assignments: dict, prototypes: dict) -> Path:
        """Save final assignments, prototypes, and refinement log."""
        # Final assignments
        final_assignments = {
            "assignments": {
                str(crop_id): assignment
                for crop_id, assignment in assignments.items()
            },
            "metadata": {
                "total_assigned": len(assignments),
                "refinement_rounds": len(self.round_logs),
                "generated_at": datetime.now().isoformat()
            }
        }
        assignments_path = self.output_dir / "final_assignments.json"
        with open(assignments_path, 'w') as f:
            json.dump(final_assignments, f, indent=2)

        # Final prototypes
        final_prototypes = {
            "prototypes": prototypes,
            "metadata": {
                "total_species": len(prototypes),
                "ground_truth_species": len(self.ground_truth_prototypes),
                "soft_prototype_species": len(prototypes) - len(self.ground_truth_prototypes),
                "generated_at": datetime.now().isoformat()
            }
        }
        prototypes_path = self.output_dir / "final_prototypes.json"
        with open(prototypes_path, 'w') as f:
            json.dump(final_prototypes, f, indent=2)

        # Refinement log
        log_path = self.output_dir / "refinement_log.json"
        with open(log_path, 'w') as f:
            json.dump(self.round_logs, f, indent=2)

        print(f"\nSaved final assignments: {assignments_path}")
        print(f"Saved final prototypes: {prototypes_path}")
        print(f"Saved refinement log: {log_path}")

        return assignments_path


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Stage 4: Cross-reference validation')
    parser.add_argument('--crops-dir', type=str,
                        default='data/weak_supervision/bird_crops',
                        help='Path to bird_crops directory')
    parser.add_argument('--embeddings-dir', type=str,
                        default='data/weak_supervision/bird_crops/embeddings',
                        help='Path to embeddings directory')
    parser.add_argument('--prototypes', type=str,
                        default='data/weak_supervision/bird_crops/ground_truth/prototypes.json',
                        help='Path to ground truth prototypes from Stage 2')
    parser.add_argument('--image-metadata', type=str,
                        default='data/weak_supervision/image_metadata.json',
                        help='Path to image_metadata.json')
    parser.add_argument('--max-rounds', type=int, default=5,
                        help='Maximum refinement rounds')
    parser.add_argument('--expansion-confidence', type=float, default=0.7,
                        help='Min confidence for prototype expansion')
    parser.add_argument('--min-soft-crops', type=int, default=10,
                        help='Min crops for soft prototype creation')

    args = parser.parse_args()

    validator = CrossReferenceValidator(
        crops_dir=args.crops_dir,
        embeddings_dir=args.embeddings_dir,
        prototypes_path=args.prototypes,
        image_metadata_path=args.image_metadata,
        max_rounds=args.max_rounds,
        expansion_confidence=args.expansion_confidence,
        min_soft_prototype_crops=args.min_soft_crops
    )
    validator.run_iterative_refinement()


if __name__ == '__main__':
    main()
