"""
Integrated Clustering Service

Handles the complete clustering workflow:
1. Load embeddings
2. Run clustering (K-means or DBSCAN)
3. Generate t-SNE visualization
4. Export results for web visualization
"""

import numpy as np
import json
from pathlib import Path
from typing import Dict, List, Tuple
import pickle
from sklearn.cluster import KMeans, DBSCAN
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE
from sklearn.preprocessing import StandardScaler
from sklearn.neighbors import NearestNeighbors
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
from collections import defaultdict


class ClusteringService:
    """
    Performs clustering on bird embeddings and generates visualizations.
    """

    def __init__(self, crops_dir: str):
        """
        Args:
            crops_dir: Path to bird_crops directory (contains embeddings.npy)
        """
        self.crops_dir = Path(crops_dir)
        self.clusters_dir = self.crops_dir / "clusters"
        self.clusters_dir.mkdir(exist_ok=True)

    def _estimate_eps(self, X, min_samples=10, percentile=90):
        """
        Auto-estimate optimal eps for DBSCAN using k-distance graph.

        Strategy:
        1. Find k-th nearest neighbor distance for each point (k = min_samples)
        2. Sort these distances
        3. Use high percentile (90th) as eps to capture most dense regions

        Args:
            X: Standardized feature matrix
            min_samples: DBSCAN min_samples parameter
            percentile: Percentile of k-distances to use (default 90)

        Returns:
            Estimated eps value
        """
        print(f"  • Auto-tuning eps parameter...")
        print(f"    Computing {min_samples}-nearest neighbors for {len(X)} points...")

        # Find k-nearest neighbors
        nbrs = NearestNeighbors(n_neighbors=min_samples)
        nbrs.fit(X)
        distances, indices = nbrs.kneighbors(X)

        # Get k-th nearest neighbor distance for each point
        k_distances = distances[:, -1]  # Last column = k-th neighbor
        k_distances = np.sort(k_distances)

        # Use percentile to find eps
        # Using 90th percentile means 90% of points will have at least min_samples neighbors
        eps = np.percentile(k_distances, percentile)

        # Stats
        median_dist = np.median(k_distances)
        mean_dist = np.mean(k_distances)

        print(f"    Distance stats: min={k_distances[0]:.2f}, median={median_dist:.2f}, "
              f"mean={mean_dist:.2f}, max={k_distances[-1]:.2f}")
        print(f"    Selected eps={eps:.2f} (P{percentile})")

        return eps

    def run_clustering(self, n_clusters: int = 30, method: str = 'kmeans'):
        """
        Complete clustering workflow.

        Args:
            n_clusters: Number of clusters (for K-means)
            method: 'kmeans' or 'dbscan'

        Returns:
            Dict with cluster results and paths to outputs
        """
        print("=" * 60)
        print("🦅 BIRD CLUSTERING PIPELINE")
        print("=" * 60)

        # Step 1: Load embeddings
        print("\n[1/5] Loading embeddings...")
        embeddings, metadata, config = self._load_data()
        print(f"✓ Loaded {len(embeddings)} bird embeddings ({config['embedding_dim']}-dim)")

        # Step 2: Standardize
        print("\n[2/5] Standardizing features...")
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(embeddings)

        # Step 2.5: PCA dimensionality reduction (for DBSCAN only)
        # DBSCAN struggles in high-D space due to curse of dimensionality
        X_clustering = X_scaled  # Default: use full embeddings
        if method == 'dbscan':
            print("\n[2.5/5] Reducing dimensions for DBSCAN...")
            # Reduce to 100 dimensions (targets 85-95% variance)
            # Note: EfficientNet needs more dims than DINOv2 to preserve variance
            n_components = min(100, embeddings.shape[0] - 1)  # Can't exceed n_samples - 1
            pca_clustering = PCA(n_components=n_components)
            X_clustering = pca_clustering.fit_transform(X_scaled)

            variance_explained = 100 * np.sum(pca_clustering.explained_variance_ratio_)
            print(f"  ✓ Reduced {config['embedding_dim']}D → {n_components}D "
                  f"(keeps {variance_explained:.1f}% variance)")

        # Step 3: Clustering
        print(f"\n[3/5] Clustering with {method}...")
        if method == 'kmeans':
            clusterer = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
            labels = clusterer.fit_predict(X_clustering)
        elif method == 'dbscan':
            # Auto-tune eps based on data distribution in reduced space
            # For fine-grained species classification (~70 species), use aggressive parameters
            min_samples = 3  # Minimum points to form a core point (lower = more fine-grained clusters)
            eps = self._estimate_eps(X_clustering, min_samples=min_samples, percentile=20)

            print(f"  • Running DBSCAN with eps={eps:.2f}, min_samples={min_samples}")
            clusterer = DBSCAN(eps=eps, min_samples=min_samples)
            labels = clusterer.fit_predict(X_clustering)

            # Count clusters (excluding noise labeled as -1)
            n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
            n_noise = np.sum(labels == -1)
            noise_pct = 100 * n_noise / len(labels)

            print(f"  ✓ DBSCAN found {n_clusters} clusters")
            print(f"    Noise points: {n_noise} ({noise_pct:.1f}%)")
        else:
            raise ValueError(f"Unknown method: {method}")

        print(f"✓ Created {n_clusters} clusters")

        # Step 4: Dimensionality reduction to 2D (for interactive visualization)
        print("\n[4/5] Generating 2D visualizations...")

        # PCA (fast, for comparison)
        print("  • Running 2D PCA...")
        pca = PCA(n_components=2)
        X_pca = pca.fit_transform(X_scaled)

        # Try UMAP first (faster and often better for 2D), fallback to t-SNE
        print("  • Running 2D dimensionality reduction...")
        try:
            from umap import UMAP
            print("    Using UMAP (better cluster separation)...")
            # Increased min_dist for more separation between clusters
            # n_neighbors=30 for more global structure preservation
            reducer = UMAP(n_components=2, random_state=42, n_neighbors=30, min_dist=0.5)
            X_tsne = reducer.fit_transform(X_scaled)
            reduction_method = 'umap'
            print("  ✓ UMAP complete")
        except ImportError:
            print("    UMAP not available, using t-SNE...")
            # Increased perplexity for better cluster separation
            tsne = TSNE(n_components=2, random_state=42, perplexity=50, max_iter=1000, verbose=0)
            X_tsne = tsne.fit_transform(X_scaled)
            reduction_method = 'tsne'
            print("  ✓ t-SNE complete")
            reducer = tsne

        # Step 5: Save results
        print("\n[5/5] Saving results...")

        # Save clustering results
        results = {
            'method': method,
            'n_clusters': int(n_clusters),
            'labels': labels.tolist(),
            'metadata': metadata['crops'],
            'scaler': scaler,
            'pca': pca,
            'X_pca': X_pca.tolist(),
            'reducer': reducer,
            'reduction_method': reduction_method,
            'X_tsne': X_tsne.tolist(),  # Actually UMAP or t-SNE, keeping name for compatibility
            'embedding_config': config
        }

        with open(self.clusters_dir / 'clustering_results.pkl', 'wb') as f:
            pickle.dump(results, f)

        # Export for web visualization
        self._export_for_viz(labels, X_tsne, metadata)

        # Generate plots
        self._generate_plots(X_pca, X_tsne, labels, n_clusters)

        # Generate cluster previews
        self._generate_cluster_previews(labels, metadata)

        print("\n✅ CLUSTERING COMPLETE!")
        print(f"📁 Results: {self.clusters_dir}")
        print(f"📊 2D PCA plot: {self.clusters_dir / 'cluster_visualization_pca_2d.png'}")
        print(f"📊 2D main plot: {self.clusters_dir / 'cluster_visualization_2d.png'}")
        print(f"🌐 2D web viz data: {self.clusters_dir / 'clusters_for_labeling.json'}")
        print("\n🎯 Next: Open http://localhost:5000/clusters to explore in 2D!")

        return {
            'n_clusters': int(n_clusters),
            'total_birds': len(labels),
            'clusters_dir': str(self.clusters_dir),
            'viz_file': str(self.clusters_dir / 'clusters_for_labeling.json')
        }

    def _load_data(self) -> Tuple[np.ndarray, Dict, Dict]:
        """Load embeddings and metadata"""
        embeddings_file = self.crops_dir / "embeddings.npy"
        metadata_file = self.crops_dir / "metadata.json"
        config_file = self.crops_dir / "config.json"

        if not embeddings_file.exists():
            raise FileNotFoundError(
                f"Embeddings not found at {embeddings_file}\n"
                "Run embedding extraction first!"
            )

        embeddings = np.load(embeddings_file)

        with open(metadata_file, 'r') as f:
            metadata = json.load(f)

        with open(config_file, 'r') as f:
            config = json.load(f)

        return embeddings, metadata, config

    def _export_for_viz(self, labels: np.ndarray, X_tsne: np.ndarray,
                       metadata: Dict):
        """Export cluster data for 2D web visualization"""

        # Group birds by cluster
        cluster_data = defaultdict(list)

        for idx, (label, pos, meta) in enumerate(zip(labels, X_tsne, metadata['crops'])):
            if label == -1:  # Skip noise points
                continue

            cluster_data[int(label)].append({
                'crop_id': idx,
                'bird_id': idx,
                'image_name': meta['source_image'],
                'crop_filename': meta['crop_filename'],
                'x': float(pos[0]),
                'y': float(pos[1])
            })

        # Build export data
        export_data = {
            'total_birds': len(labels),
            'n_clusters': len(cluster_data),
            'clusters': {},
            'positions': []
        }

        for cluster_id, birds in cluster_data.items():
            export_data['clusters'][str(cluster_id)] = {
                'size': len(birds),
                'total_birds': len(birds),
                'birds': birds[:100],  # First 100 for preview
                'species_label': None,  # To be filled by expert
                'confidence': None
            }

            # Add 2D positions for interactive plot
            for bird in birds:
                export_data['positions'].append({
                    'x': bird['x'],
                    'y': bird['y'],
                    'cluster': cluster_id,
                    'bird_id': bird['bird_id'],
                    'image_name': bird['image_name'],
                    'crop_path': f'/api/bird_crop/{bird["bird_id"]}'
                })

        # Save
        output_file = self.clusters_dir / 'clusters_for_labeling.json'
        with open(output_file, 'w') as f:
            json.dump(export_data, f, indent=2)

        print(f"  ✓ Exported viz data: {output_file}")

    def _generate_plots(self, X_pca: np.ndarray, X_tsne: np.ndarray,
                       labels: np.ndarray, n_clusters: int):
        """Generate 2D visualization plots with clear cluster separation"""

        # 2D PCA plot
        fig, ax = plt.subplots(figsize=(14, 10))
        scatter = ax.scatter(X_pca[:, 0], X_pca[:, 1], c=labels,
                            cmap='tab20', alpha=0.7, s=30, edgecolors='black', linewidth=0.5)
        ax.set_xlabel('PC1', fontsize=12)
        ax.set_ylabel('PC2', fontsize=12)
        ax.set_title(f'Bird Clusters using 2D PCA (n={n_clusters})', fontsize=14, fontweight='bold')
        ax.grid(alpha=0.3, linestyle='--')
        plt.colorbar(scatter, label='Cluster ID', shrink=0.8)
        plt.savefig(self.clusters_dir / 'cluster_visualization_pca_2d.png',
                   dpi=200, bbox_inches='tight')
        plt.close()

        # 2D t-SNE/UMAP plot (main visualization)
        fig, ax = plt.subplots(figsize=(14, 10))
        scatter = ax.scatter(X_tsne[:, 0], X_tsne[:, 1], c=labels,
                            cmap='tab20', alpha=0.7, s=30, edgecolors='black', linewidth=0.5)
        ax.set_xlabel('Dimension 1', fontsize=12)
        ax.set_ylabel('Dimension 2', fontsize=12)

        # Determine method name for title
        method_name = 'UMAP' if hasattr(self, '_used_umap') else 't-SNE'
        ax.set_title(f'Bird Clusters using 2D {method_name} (n={n_clusters})',
                    fontsize=14, fontweight='bold')
        ax.grid(alpha=0.3, linestyle='--')

        # Add colorbar with better positioning
        cbar = plt.colorbar(scatter, label='Cluster ID', shrink=0.8)
        cbar.set_label('Cluster ID', fontsize=11)

        plt.savefig(self.clusters_dir / 'cluster_visualization_2d.png',
                   dpi=200, bbox_inches='tight')
        plt.close()

        print(f"  ✓ Generated 2D visualization plots")

    def _generate_cluster_previews(self, labels: np.ndarray, metadata: Dict):
        """Generate preview images for each cluster"""
        import cv2

        # Group by cluster
        cluster_crops = defaultdict(list)
        for idx, (label, meta) in enumerate(zip(labels, metadata['crops'])):
            if label == -1:
                continue
            cluster_crops[label].append(meta)

        print(f"  • Creating preview images for {len(cluster_crops)} clusters...")

        for cluster_id, crops in cluster_crops.items():
            # Sample up to 20 birds
            sample_size = min(len(crops), 20)
            sampled = np.random.choice(len(crops), size=sample_size, replace=False)

            # Create grid
            grid_size = int(np.ceil(np.sqrt(sample_size)))
            cell_size = 128
            grid_image = np.ones((grid_size * cell_size, grid_size * cell_size, 3),
                                dtype=np.uint8) * 255

            for i, idx in enumerate(sampled):
                crop_info = crops[idx]
                crop_path = self.crops_dir / "images" / crop_info['crop_filename']

                if not crop_path.exists():
                    continue

                crop = cv2.imread(str(crop_path))
                if crop is None:
                    continue

                crop_resized = cv2.resize(crop, (cell_size, cell_size))

                row = i // grid_size
                col = i % grid_size

                y1 = row * cell_size
                y2 = (row + 1) * cell_size
                x1 = col * cell_size
                x2 = (col + 1) * cell_size

                grid_image[y1:y2, x1:x2] = crop_resized

            # Save
            cluster_dir = self.clusters_dir / f"cluster_{cluster_id:03d}"
            cluster_dir.mkdir(exist_ok=True)

            cv2.imwrite(str(cluster_dir / "preview.jpg"), grid_image,
                       [cv2.IMWRITE_JPEG_QUALITY, 95])

            # Save info
            with open(cluster_dir / "info.json", 'w') as f:
                json.dump({
                    'cluster_id': int(cluster_id),
                    'size': len(crops),
                    'species_label': None
                }, f, indent=2)

        print(f"  ✓ Created {len(cluster_crops)} preview images")


def run_full_pipeline(dataset_dir: str, output_dir: str,
                     model_name: str = 'efficientnet',
                     n_clusters: int = 30,
                     method: str = 'kmeans',
                     force_crops: bool = False,
                     force_embeddings: bool = False):
    """
    Run complete pipeline: extract crops → embeddings → 2D clustering with separation.

    Args:
        dataset_dir: YOLO dataset path
        output_dir: Output directory for crops and results
        model_name: Embedding model ('efficientnet' for speed, 'dinov2' for quality)
        n_clusters: Number of clusters (only used for K-means)
        method: Clustering method ('kmeans' or 'dbscan')
        force_crops: Force re-extraction of crops even if they exist
        force_embeddings: Force re-generation of embeddings even if they exist

    Returns:
        Dict with results
    """
    from labeller.services.embedding_service import BirdCropManager

    output_path = Path(output_dir)

    print("\n" + "=" * 60)
    print("🚀 COMPLETE CLUSTERING PIPELINE")
    print("=" * 60)
    print(f"Dataset: {dataset_dir}")
    print(f"Output: {output_dir}")
    print(f"Model: {model_name}")
    print(f"Method: {method}")
    if method == 'kmeans':
        print(f"Clusters: {n_clusters}")
    else:
        print(f"Clusters: auto-detected by {method.upper()}")
    print("=" * 60 + "\n")

    # Step 1: Extract crops and embeddings
    print("STAGE 1: EXTRACT CROPS & EMBEDDINGS")
    print("-" * 60)

    manager = BirdCropManager(output_dir)

    # Check 1: Do we need to extract crops?
    crops_exist = (output_path / "images").exists() and \
                  len(list((output_path / "images").glob("bird_*.jpg"))) > 0
    metadata_exists = (output_path / "metadata.json").exists()

    if force_crops or not (crops_exist and metadata_exists):
        if crops_exist and not force_crops:
            print(f"⚠️  Found {len(list((output_path / 'images').glob('bird_*.jpg')))} crops but no metadata")
        print("Extracting crops from dataset...")
        manager.extract_and_save_crops(dataset_dir, resize=224)
    else:
        n_crops = len(list((output_path / "images").glob("bird_*.jpg")))
        print(f"✓ Found {n_crops} existing crops, skipping extraction...")

    # Check 2: Do we need to generate embeddings?
    embeddings_exist = (output_path / "embeddings.npy").exists()
    config_exists = (output_path / "config.json").exists()

    # Check if model changed (need to regenerate embeddings)
    model_changed = False
    if config_exists:
        with open(output_path / "config.json", 'r') as f:
            config = json.load(f)
            if config.get('model_name') != model_name:
                model_changed = True
                print(f"⚠️  Model changed: {config.get('model_name')} → {model_name}")

    if force_embeddings or not embeddings_exist or model_changed:
        if embeddings_exist and not force_embeddings and not model_changed:
            print("⚠️  Embeddings exist but seem incomplete")
        print(f"Generating embeddings with {model_name}...")
        manager.generate_embeddings(model_name=model_name)
    else:
        embeddings = np.load(output_path / "embeddings.npy")
        print(f"✓ Found existing embeddings ({embeddings.shape[0]} x {embeddings.shape[1]}), skipping generation...")

    # Step 2: Run clustering
    print("\n" + "-" * 60)
    print("STAGE 2: CLUSTERING & VISUALIZATION")
    print("-" * 60)

    service = ClusteringService(output_dir)
    results = service.run_clustering(n_clusters=n_clusters, method=method)

    print("\n" + "=" * 60)
    print("✅ PIPELINE COMPLETE!")
    print("=" * 60)
    print(f"📊 {results['total_birds']} birds clustered into {results['n_clusters']} groups")
    print(f"📁 Results: {results['clusters_dir']}")
    print(f"\n🎯 Open http://localhost:5000/clusters to explore in 2D!")
    print("=" * 60)

    return results
