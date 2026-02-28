"""
Stage 4: Export for Frontend

Generate frontend-compatible JSON for visualization in the Nestperts clustering dashboard.
"""

import sys
from pathlib import Path
import json
import numpy as np
from datetime import datetime
from tqdm import tqdm
import cv2
from PIL import Image
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))


class FrontendExporter:
    """
    Exports clustering results to frontend-compatible format.

    Mimics the structure from existing clustering_service.py but
    organizes clusters by species rather than arbitrary IDs.
    """

    def __init__(self, crops_dir: str, embeddings_dir: str, species_clusters_dir: str):
        """
        Args:
            crops_dir: Path to bird_crops directory
            embeddings_dir: Path to embeddings directory
            species_clusters_dir: Path to species_clusters directory
        """
        self.crops_dir = Path(crops_dir)
        self.embeddings_dir = Path(embeddings_dir)
        self.species_clusters_dir = Path(species_clusters_dir)
        self.images_dir = self.crops_dir / "images"

        # Load data
        print(f"Loading data...")
        with open(self.crops_dir / "metadata.json", 'r') as f:
            self.metadata = json.load(f)
        self.crops = {c['crop_id']: c for c in self.metadata['crops']}

        self.embeddings = np.load(self.embeddings_dir / "embeddings_all.npy")

        with open(self.species_clusters_dir / "global_cluster_map.json", 'r') as f:
            self.global_map = json.load(f)

        print(f"✓ Loaded {len(self.crops)} crops")
        print(f"✓ Loaded {self.embeddings.shape} embeddings")
        print(f"✓ Loaded {len(self.global_map['species_summary'])} species")

    def generate_visualization_data(self):
        """
        Create frontend JSON with t-SNE/UMAP visualization.

        Steps:
        1. Run UMAP/t-SNE on all embeddings (100K crops → 2D)
        2. Build clusters_for_labeling.json with species as cluster IDs
        3. Generate cluster preview images
        """
        print("\n" + "=" * 60)
        print("FRONTEND EXPORT")
        print("=" * 60)

        # Step 1: Run dimensionality reduction
        print("\n[1/3] Running dimensionality reduction...")
        positions_2d = self.run_dimensionality_reduction()

        # Step 2: Build cluster JSON
        print("\n[2/3] Building clusters_for_labeling.json...")
        self.build_cluster_json(positions_2d)

        # Step 3: Generate cluster previews
        print("\n[3/3] Generating cluster preview images...")
        self.generate_cluster_previews()

        print("\n" + "=" * 60)
        print("✅ FRONTEND EXPORT COMPLETE")
        print("=" * 60)
        print(f"Output: {self.species_clusters_dir}")
        print(f"Clusters: {len(self.global_map['species_summary'])} species")
        print("\n🎯 Next step: View in Nestperts dashboard")
        print("   cd labeller/")
        print("   python app.py --data nestvision")
        print("   Open: http://localhost:5000/clusters")

    def run_dimensionality_reduction(self) -> np.ndarray:
        """
        Run UMAP or t-SNE dimensionality reduction for visualization.

        Returns:
            (n_crops, 2) array of 2D positions
        """
        print("Reducing dimensions for visualization...")
        print(f"Input shape: {self.embeddings.shape}")

        try:
            # Try UMAP first (faster, better separation)
            from umap import UMAP
            print("Using UMAP (fast, recommended)...")
            reducer = UMAP(
                n_components=2,
                random_state=42,
                n_neighbors=30,
                min_dist=0.5,
                metric='cosine'
            )
            positions_2d = reducer.fit_transform(self.embeddings)
            print("✓ UMAP complete")

        except ImportError:
            # Fallback to t-SNE
            from sklearn.manifold import TSNE
            print("UMAP not available, using t-SNE (slower)...")
            reducer = TSNE(
                n_components=2,
                random_state=42,
                perplexity=30,
                max_iter=1000,  # Changed from n_iter for newer scikit-learn
                metric='cosine'
            )
            positions_2d = reducer.fit_transform(self.embeddings)
            print("✓ t-SNE complete")

        print(f"Output shape: {positions_2d.shape}")
        return positions_2d

    def build_cluster_json(self, positions_2d: np.ndarray):
        """
        Build the clusters_for_labeling.json structure.

        Format matches existing frontend expectations.

        Args:
            positions_2d: (n_crops, 2) array of 2D positions
        """
        print("Building cluster JSON...")

        # Build clusters dict (organized by species)
        clusters_dict = {}
        positions_list = []

        for species_code, species_info in tqdm(self.global_map['species_summary'].items(),
                                               desc="Processing species"):
            # Find all cluster assignments for this species
            species_clusters = [
                cluster_info
                for cluster_id, cluster_info in self.global_map['cluster_assignments'].items()
                if cluster_info['assigned_species'] == species_code
            ]

            # Collect all crop_ids for this species
            species_crop_ids = []
            for cluster in species_clusters:
                species_crop_ids.extend(cluster['crop_ids'])

            # Build bird entries
            birds = []
            for crop_id in species_crop_ids:
                crop_meta = self.crops[crop_id]

                # Get 2D position (embedding_index maps crop_id to row)
                row_idx = crop_id  # Since crops are ordered by crop_id
                x, y = positions_2d[row_idx]

                bird_entry = {
                    "crop_id": crop_id,
                    "bird_id": crop_id,  # Same as crop_id
                    "image_name": crop_meta['crop_filename'],
                    "source_photo_id": crop_meta['source_photo_id'],
                    "x": float(x),
                    "y": float(y),
                    "z": 0.0  # Not using 3D visualization
                }
                birds.append(bird_entry)

                # Add to positions list
                position_entry = {
                    "x": float(x),
                    "y": float(y),
                    "cluster": species_code,
                    "bird_id": crop_id,
                    "image_name": crop_meta['crop_filename'],
                    "crop_path": f"/api/bird_crop/{crop_id}"
                }
                positions_list.append(position_entry)

            # Add species cluster
            clusters_dict[species_code] = {
                "size": len(species_crop_ids),
                "total_birds": len(species_crop_ids),
                "species_label": species_code,
                "confidence": species_info['consistency_score'],
                "birds": birds
            }

        # Build final JSON
        clusters_json = {
            "total_birds": len(self.crops),
            "n_clusters": len(clusters_dict),
            "clusters": clusters_dict,
            "positions": positions_list,
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "visualization_method": "umap",  # or tsne
                "n_dimensions": 2
            }
        }

        # Save
        output_path = self.species_clusters_dir / "clusters_for_labeling.json"
        with open(output_path, 'w') as f:
            json.dump(clusters_json, f, indent=2)

        print(f"✓ Saved: {output_path}")
        print(f"  Total birds: {clusters_json['total_birds']}")
        print(f"  Clusters: {clusters_json['n_clusters']}")

    def generate_cluster_previews(self):
        """
        Generate preview images for each species cluster.

        Structure:
        species_clusters/
        ├── cluster_GREG/
        │   ├── preview.jpg    # Grid of 20 sample birds
        │   └── info.json      # Cluster metadata
        """
        print("Generating cluster preview images...")

        for species_code, species_info in tqdm(self.global_map['species_summary'].items(),
                                               desc="Creating previews"):
            # Create cluster directory
            cluster_dir = self.species_clusters_dir / f"cluster_{species_code}"
            cluster_dir.mkdir(exist_ok=True)

            # Find cluster assignments for this species
            species_clusters = [
                cluster_info
                for cluster_id, cluster_info in self.global_map['cluster_assignments'].items()
                if cluster_info['assigned_species'] == species_code
            ]

            # Collect sample crop_ids (up to 20)
            sample_crop_ids = []
            for cluster in species_clusters:
                sample_crop_ids.extend(cluster['crop_ids'][:5])  # 5 from each cluster
                if len(sample_crop_ids) >= 20:
                    break
            sample_crop_ids = sample_crop_ids[:20]

            # Generate preview grid
            if sample_crop_ids:
                preview_path = self._create_preview_grid(
                    sample_crop_ids,
                    cluster_dir / "preview.jpg"
                )

            # Save info.json
            info = {
                "cluster_id": species_code,
                "species_code": species_code,
                "size": species_info['total_crops'],
                "consistency_score": species_info['consistency_score'],
                "n_clusters": species_info['total_clusters'],
                "outlier_clusters": species_info['outlier_clusters']
            }

            info_path = cluster_dir / "info.json"
            with open(info_path, 'w') as f:
                json.dump(info, f, indent=2)

        print(f"✓ Created {len(self.global_map['species_summary'])} cluster preview directories")

    def _create_preview_grid(self, crop_ids: list, output_path: Path, grid_size: int = 5) -> Path:
        """
        Create a grid image showing sample crops.

        Args:
            crop_ids: List of crop IDs to display
            output_path: Where to save the grid
            grid_size: Grid dimensions (grid_size x grid_size)

        Returns:
            Path to saved preview image
        """
        n_samples = min(len(crop_ids), grid_size * grid_size)
        sample_ids = crop_ids[:n_samples]

        # Load images
        images = []
        for crop_id in sample_ids:
            crop_meta = self.crops[crop_id]
            img_path = self.images_dir / crop_meta['crop_filename']

            try:
                img = cv2.imread(str(img_path))
                img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                # Resize to 128x128 for grid
                img = cv2.resize(img, (128, 128))
                images.append(img)
            except Exception as e:
                print(f"\n⚠️  Error loading {img_path}: {e}")
                # Use black placeholder
                images.append(np.zeros((128, 128, 3), dtype=np.uint8))

        # Create grid
        fig, axes = plt.subplots(grid_size, grid_size, figsize=(10, 10))
        axes = axes.flatten()

        for idx, ax in enumerate(axes):
            if idx < len(images):
                ax.imshow(images[idx])
            ax.axis('off')

        plt.tight_layout()
        plt.savefig(output_path, dpi=100, bbox_inches='tight')
        plt.close()

        return output_path


def main():
    """
    Main entry point for Stage 4.
    """
    import argparse

    parser = argparse.ArgumentParser(description='Stage 4: Export for frontend')
    parser.add_argument('--crops-dir', type=str,
                        default='data/weak_supervision/bird_crops',
                        help='Path to bird_crops directory')
    parser.add_argument('--embeddings-dir', type=str,
                        default='data/weak_supervision/bird_crops/embeddings',
                        help='Path to embeddings directory')
    parser.add_argument('--species-clusters-dir', type=str,
                        default='data/weak_supervision/bird_crops/species_clusters',
                        help='Path to species_clusters directory')

    args = parser.parse_args()

    # Create exporter
    exporter = FrontendExporter(
        crops_dir=args.crops_dir,
        embeddings_dir=args.embeddings_dir,
        species_clusters_dir=args.species_clusters_dir
    )

    # Generate visualization data
    exporter.generate_visualization_data()


if __name__ == '__main__':
    main()
