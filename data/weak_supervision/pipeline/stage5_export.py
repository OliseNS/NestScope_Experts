"""
Stage 5: Quality Control & Export

Produces:
  1. final_species_labels.json — The definitive crop-to-species mapping
  2. quality_report.json — Per-species and per-method quality metrics
  3. clusters_for_labeling.json — Frontend visualization data (Nestperts dashboard)

Assignment categories (ordered by confidence):
  - ground_truth (1.0): From single-species images
  - hungarian (0.5-1.0): Matched to prototype via Hungarian algorithm
  - poe (0.3-0.6): Process of elimination (no prototype to compare against)
  - EXCLUDED: Below threshold or ambiguous — NOT in final dataset
"""

import sys
from pathlib import Path
import json
import numpy as np
from datetime import datetime
from collections import defaultdict
from tqdm import tqdm

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))


class QualityExporter:
    """
    Generates final labeled dataset, quality report, and frontend exports.
    """

    def __init__(self, crops_dir: str, embeddings_dir: str,
                 assignments_path: str, prototypes_path: str,
                 min_export_confidence: float = 0.0):
        """
        Args:
            crops_dir: Path to bird_crops directory
            embeddings_dir: Path to embeddings directory
            assignments_path: Path to final_assignments.json from Stage 4
            prototypes_path: Path to final_prototypes.json from Stage 4
            min_export_confidence: Minimum confidence for export (0 = include all assigned)
        """
        self.crops_dir = Path(crops_dir)
        self.embeddings_dir = Path(embeddings_dir)
        self.min_export_confidence = min_export_confidence

        # Load crop metadata
        print("Loading crop metadata...")
        with open(self.crops_dir / "metadata.json", 'r') as f:
            metadata = json.load(f)
        self.crops = {c['crop_id']: c for c in metadata['crops']}
        self.total_crops = len(self.crops)
        print(f"  Loaded {self.total_crops} crops")

        # Load assignments
        print("Loading final assignments...")
        with open(assignments_path, 'r') as f:
            assignments_data = json.load(f)
        self.assignments = assignments_data['assignments']
        self.refinement_rounds = assignments_data['metadata'].get('refinement_rounds', 0)
        print(f"  Loaded {len(self.assignments)} assignments")

        # Load embeddings (needed for 2D visualization)
        print("Loading embeddings...")
        self.embeddings = np.load(self.embeddings_dir / "embeddings_all.npy")
        with open(self.embeddings_dir / "embeddings_index.json", 'r') as f:
            self.embedding_index = json.load(f)
        print(f"  Loaded embeddings: {self.embeddings.shape}")

        # Load prototypes
        print("Loading final prototypes...")
        with open(prototypes_path, 'r') as f:
            proto_data = json.load(f)
        self.prototypes = proto_data['prototypes']
        print(f"  Loaded {len(self.prototypes)} prototypes")

        # Output directories
        self.output_dir = self.crops_dir / "export"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def export_all(self):
        """Run all exports."""
        print("\n" + "=" * 60)
        print("QUALITY CONTROL & EXPORT")
        print("=" * 60)

        # 1. Final species labels
        print("\n[1/3] Generating final species labels...")
        labels_path = self._export_final_labels()

        # 2. Quality report
        print("\n[2/3] Generating quality report...")
        report_path = self._export_quality_report()

        # 3. Frontend visualization
        print("\n[3/3] Generating frontend export...")
        frontend_path = self._export_for_frontend()

        print("\n" + "=" * 60)
        print("EXPORT COMPLETE")
        print("=" * 60)
        print(f"Final labels: {labels_path}")
        print(f"Quality report: {report_path}")
        print(f"Frontend data: {frontend_path}")

    def _export_final_labels(self) -> Path:
        """
        Generate the definitive crop-to-species mapping.

        This is the primary output — what you'd use for training a classifier.
        """
        labels = {}
        species_counts = defaultdict(int)
        method_counts = defaultdict(int)
        excluded_count = 0

        for crop_id_str, assignment in self.assignments.items():
            confidence = assignment['confidence']
            if confidence < self.min_export_confidence:
                excluded_count += 1
                continue

            labels[crop_id_str] = {
                "species": assignment['species'],
                "confidence": confidence,
                "method": assignment['method']
            }
            species_counts[assignment['species']] += 1
            method_counts[assignment['method']] += 1

        # Count crops that were never assigned (excluded during classification)
        assigned_crop_ids = set(int(k) for k in self.assignments.keys())
        never_assigned = [cid for cid in self.crops.keys() if cid not in assigned_crop_ids]
        total_excluded = excluded_count + len(never_assigned)

        output = {
            "total_crops": self.total_crops,
            "labeled_crops": len(labels),
            "excluded_crops": total_excluded,
            "label_rate": len(labels) / max(self.total_crops, 1),
            "species_counts": dict(sorted(species_counts.items(),
                                          key=lambda x: -x[1])),
            "method_counts": dict(method_counts),
            "min_export_confidence": self.min_export_confidence,
            "labels": labels,
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "refinement_rounds": self.refinement_rounds,
                "n_prototypes": len(self.prototypes)
            }
        }

        path = self.output_dir / "final_species_labels.json"
        with open(path, 'w') as f:
            json.dump(output, f, indent=2)

        print(f"  Total crops: {self.total_crops}")
        print(f"  Labeled: {len(labels)} ({100*len(labels)/self.total_crops:.1f}%)")
        print(f"  Excluded: {total_excluded} ({100*total_excluded/self.total_crops:.1f}%)")
        print(f"  Species: {len(species_counts)}")
        print(f"  Methods: {dict(method_counts)}")

        return path

    def _export_quality_report(self) -> Path:
        """
        Generate detailed quality metrics.
        """
        # Per-species stats
        species_stats = defaultdict(lambda: {
            "total_assigned": 0,
            "ground_truth_count": 0,
            "hungarian_count": 0,
            "poe_count": 0,
            "mean_confidence": 0,
            "confidence_sum": 0,
            "min_confidence": 1.0,
            "max_confidence": 0.0,
            "has_ground_truth_prototype": False,
            "has_soft_prototype": False,
        })

        for crop_id_str, assignment in self.assignments.items():
            sp = assignment['species']
            stats = species_stats[sp]
            stats['total_assigned'] += 1
            stats[f"{assignment['method']}_count"] += 1
            stats['confidence_sum'] += assignment['confidence']
            stats['min_confidence'] = min(stats['min_confidence'], assignment['confidence'])
            stats['max_confidence'] = max(stats['max_confidence'], assignment['confidence'])

        # Finalize per-species
        for sp, stats in species_stats.items():
            if stats['total_assigned'] > 0:
                stats['mean_confidence'] = stats['confidence_sum'] / stats['total_assigned']
            del stats['confidence_sum']

            if sp in self.prototypes:
                source = self.prototypes[sp].get('source', '')
                stats['has_ground_truth_prototype'] = 'ground_truth' in source
                stats['has_soft_prototype'] = 'soft' in source

        # Per-method stats
        method_stats = defaultdict(lambda: {
            "total_crops": 0,
            "mean_confidence": 0,
            "confidence_sum": 0,
        })

        for crop_id_str, assignment in self.assignments.items():
            method = assignment['method']
            method_stats[method]['total_crops'] += 1
            method_stats[method]['confidence_sum'] += assignment['confidence']

        for method, stats in method_stats.items():
            if stats['total_crops'] > 0:
                stats['mean_confidence'] = stats['confidence_sum'] / stats['total_crops']
            del stats['confidence_sum']

        # Confidence distribution
        confidences = [a['confidence'] for a in self.assignments.values()]
        if confidences:
            conf_array = np.array(confidences)
            confidence_distribution = {
                "mean": float(conf_array.mean()),
                "std": float(conf_array.std()),
                "median": float(np.median(conf_array)),
                "p10": float(np.percentile(conf_array, 10)),
                "p25": float(np.percentile(conf_array, 25)),
                "p75": float(np.percentile(conf_array, 75)),
                "p90": float(np.percentile(conf_array, 90)),
            }
        else:
            confidence_distribution = {}

        # Count excluded
        assigned_ids = set(int(k) for k in self.assignments.keys())
        never_assigned = self.total_crops - len(assigned_ids)

        # Build report
        report = {
            "summary": {
                "total_crops": self.total_crops,
                "assigned_crops": len(self.assignments),
                "never_assigned_crops": never_assigned,
                "unique_species": len(species_stats),
                "species_with_gt_prototype": sum(
                    1 for s in species_stats.values() if s['has_ground_truth_prototype']
                ),
                "species_with_soft_prototype": sum(
                    1 for s in species_stats.values() if s['has_soft_prototype']
                ),
                "refinement_rounds": self.refinement_rounds,
            },
            "confidence_distribution": confidence_distribution,
            "per_species": dict(sorted(species_stats.items(),
                                       key=lambda x: -x[1]['total_assigned'])),
            "per_method": dict(method_stats),
            "metadata": {
                "generated_at": datetime.now().isoformat()
            }
        }

        path = self.output_dir / "quality_report.json"
        with open(path, 'w') as f:
            json.dump(report, f, indent=2)

        # Print highlights
        print(f"  Confidence: mean={confidence_distribution.get('mean', 0):.3f}, "
              f"median={confidence_distribution.get('median', 0):.3f}")
        print(f"  Species with GT prototype: "
              f"{report['summary']['species_with_gt_prototype']}")
        print(f"  Species with soft prototype: "
              f"{report['summary']['species_with_soft_prototype']}")

        # Flag species with low confidence
        low_conf_species = [
            (sp, stats['mean_confidence'])
            for sp, stats in species_stats.items()
            if stats['mean_confidence'] < 0.5 and stats['total_assigned'] > 10
        ]
        if low_conf_species:
            print(f"\n  Low-confidence species (mean < 0.5):")
            for sp, conf in sorted(low_conf_species, key=lambda x: x[1]):
                print(f"    {sp}: mean_confidence={conf:.3f}")

        return path

    def _compute_2d_positions(self, crop_ids: list) -> np.ndarray:
        """
        Compute 2D positions for visualization via dimensionality reduction.

        Tries UMAP first (better separation), falls back to PCA (fast, no deps).

        Args:
            crop_ids: List of crop IDs to compute positions for

        Returns:
            (N, 2) array of 2D positions
        """
        # Get embeddings for assigned crops only
        indices = [int(self.embedding_index[str(cid)]) for cid in crop_ids]
        embeddings = self.embeddings[indices]

        print(f"  Computing 2D positions for {len(crop_ids)} crops...")

        try:
            from umap import UMAP
            print("  Using UMAP...")
            reducer = UMAP(
                n_components=2, random_state=42,
                n_neighbors=30, min_dist=0.5, metric='cosine'
            )
            positions_2d = reducer.fit_transform(embeddings)
            print("  UMAP complete")
        except ImportError:
            from sklearn.decomposition import PCA
            print("  UMAP not available, using PCA...")
            reducer = PCA(n_components=2, random_state=42)
            positions_2d = reducer.fit_transform(embeddings)
            print("  PCA complete")

        return positions_2d

    def _export_for_frontend(self) -> Path:
        """
        Generate clusters_for_labeling.json for the Nestperts dashboard.

        Format matches existing frontend expectations: needs both per-cluster
        bird lists AND a top-level 'positions' list for the 2D visualization.
        """
        # Collect all assigned crop IDs in order
        assigned_crop_ids = []
        assigned_species = []
        assigned_meta = {}

        for crop_id_str, assignment in self.assignments.items():
            crop_id = int(crop_id_str)
            if crop_id not in self.crops:
                continue
            assigned_crop_ids.append(crop_id)
            assigned_species.append(assignment['species'])
            assigned_meta[crop_id] = assignment

        # Compute real 2D positions
        positions_2d = self._compute_2d_positions(assigned_crop_ids)

        # Build position lookup: crop_id → (x, y)
        pos_lookup = {}
        for i, crop_id in enumerate(assigned_crop_ids):
            pos_lookup[crop_id] = (float(positions_2d[i, 0]), float(positions_2d[i, 1]))

        # Build clusters organized by species
        clusters_dict = {}
        species_birds = defaultdict(list)

        for crop_id in assigned_crop_ids:
            assignment = assigned_meta[crop_id]
            species = assignment['species']
            crop_meta = self.crops[crop_id]
            x, y = pos_lookup[crop_id]

            bird_entry = {
                "crop_id": crop_id,
                "bird_id": crop_id,
                "image_name": crop_meta['crop_filename'],
                "source_photo_id": crop_meta['source_photo_id'],
                "confidence": assignment['confidence'],
                "method": assignment['method'],
                "x": x,
                "y": y,
                "z": 0.0
            }
            species_birds[species].append(bird_entry)

        # Build cluster entries
        for species_code, birds in species_birds.items():
            proto = self.prototypes.get(species_code, {})
            clusters_dict[species_code] = {
                "size": len(birds),
                "total_birds": len(birds),
                "species_label": species_code,
                "confidence": proto.get('mean_similarity', 0.0),
                "source": proto.get('source', 'unknown'),
                "birds": birds
            }

        # Build top-level positions list (required by frontend /api/cluster-positions-packed)
        positions_list = []
        for crop_id in assigned_crop_ids:
            assignment = assigned_meta[crop_id]
            crop_meta = self.crops[crop_id]
            x, y = pos_lookup[crop_id]

            positions_list.append({
                "x": x,
                "y": y,
                "cluster": assignment['species'],
                "bird_id": crop_id,
                "image_name": crop_meta['crop_filename'],
                "crop_path": f"/api/bird_crop/{crop_id}"
            })

        # Build final JSON
        clusters_json = {
            "total_birds": len(assigned_crop_ids),
            "n_clusters": len(clusters_dict),
            "clusters": clusters_dict,
            "positions": positions_list,
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "pipeline_version": "ground_truth_anchored_v2",
                "refinement_rounds": self.refinement_rounds
            }
        }

        path = self.output_dir / "clusters_for_labeling.json"
        with open(path, 'w') as f:
            json.dump(clusters_json, f, indent=2)

        print(f"  Clusters: {len(clusters_dict)} species")
        print(f"  Total birds: {len(assigned_crop_ids)}")

        # Also copy to frontend location
        frontend_dir = project_root / "labeller" / "nestvision" / "bird_crops"
        if frontend_dir.exists():
            clusters_dir = frontend_dir / "clusters"
            clusters_dir.mkdir(exist_ok=True)
            frontend_path = clusters_dir / "clusters_for_labeling.json"
            with open(frontend_path, 'w') as f:
                json.dump(clusters_json, f, indent=2)
            print(f"  Copied to frontend: {frontend_path}")

        return path


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Stage 5: Quality control and export')
    parser.add_argument('--crops-dir', type=str,
                        default='data/weak_supervision/bird_crops',
                        help='Path to bird_crops directory')
    parser.add_argument('--embeddings-dir', type=str,
                        default='data/weak_supervision/bird_crops/embeddings',
                        help='Path to embeddings directory')
    parser.add_argument('--assignments', type=str,
                        default='data/weak_supervision/bird_crops/assignments/final_assignments.json',
                        help='Path to final assignments from Stage 4')
    parser.add_argument('--prototypes', type=str,
                        default='data/weak_supervision/bird_crops/assignments/final_prototypes.json',
                        help='Path to final prototypes from Stage 4')
    parser.add_argument('--min-confidence', type=float, default=0.0,
                        help='Minimum confidence for export (0 = include all)')

    args = parser.parse_args()

    exporter = QualityExporter(
        crops_dir=args.crops_dir,
        embeddings_dir=args.embeddings_dir,
        assignments_path=args.assignments,
        prototypes_path=args.prototypes,
        min_export_confidence=args.min_confidence
    )
    exporter.export_all()


if __name__ == '__main__':
    main()
