#!/usr/bin/env python3
"""
Bird Clustering Script

Runs the complete clustering pipeline:
1. Extract bird crops from YOLO dataset
2. Generate embeddings using DINOv2 (or other models)
3. Cluster birds using K-means or DBSCAN
4. Generate 3D interactive visualization

Usage:
    python scripts/cluster_birds.py --data labeller/nestvision --model dinov2 --clusters 30
"""

import argparse
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from labeller.services.clustering_service import run_full_pipeline


class BirdClusterer:
    """
    Clusters bird crops by visual similarity to reduce annotation burden.

    Features extracted:
    - Color histogram (HSV space) - captures plumage color
    - Size (width, height, aspect ratio) - distinguishes large vs small species
    - Texture features (gradient magnitude) - captures patterns
    - Brightness (mean intensity) - separates light vs dark birds
    """

    def __init__(self, data_dir: str, n_clusters: int = 30):
        """
        Args:
            data_dir: Path to YOLO dataset (contains images/ and labels/)
            n_clusters: Target number of clusters (30-50 recommended)
        """
        self.data_dir = Path(data_dir)
        self.images_dir = self.data_dir / "images"
        self.labels_dir = self.data_dir / "labels"
        self.clusters_dir = self.data_dir / "clusters"
        self.n_clusters = n_clusters

        self.clusters_dir.mkdir(exist_ok=True)

        # Storage for features and metadata
        self.features = []
        self.metadata = []  # Stores {image_path, bbox_index, bbox_coords}

    def extract_bird_crops(self) -> List[Tuple[np.ndarray, Dict]]:
        """
        Extract all bird crops from images using YOLO labels.

        Returns:
            List of (crop_image, metadata) tuples
        """
        crops = []

        label_files = list(self.labels_dir.glob("*.txt"))
        print(f"Found {len(label_files)} labeled images")

        for label_file in label_files:
            # Find corresponding image
            image_name = label_file.stem
            image_file = None
            for ext in ['.jpg', '.jpeg', '.png', '.JPG', '.JPEG', '.PNG']:
                potential_image = self.images_dir / f"{image_name}{ext}"
                if potential_image.exists():
                    image_file = potential_image
                    break

            if not image_file:
                print(f"Warning: No image found for {label_file.name}")
                continue

            # Load image
            image = cv2.imread(str(image_file))
            if image is None:
                print(f"Warning: Could not load {image_file}")
                continue

            height, width = image.shape[:2]

            # Read YOLO labels
            with open(label_file, 'r') as f:
                lines = f.readlines()

            for bbox_idx, line in enumerate(lines):
                parts = line.strip().split()
                if len(parts) < 5:
                    continue

                # YOLO format: class_id x_center y_center width height [species]
                class_id, x_center, y_center, box_w, box_h = map(float, parts[:5])

                # Convert normalized coords to pixel coords
                x_center_px = int(x_center * width)
                y_center_px = int(y_center * height)
                box_w_px = int(box_w * width)
                box_h_px = int(box_h * height)

                # Get bbox corners
                x1 = max(0, x_center_px - box_w_px // 2)
                y1 = max(0, y_center_px - box_h_px // 2)
                x2 = min(width, x_center_px + box_w_px // 2)
                y2 = min(height, y_center_px + box_h_px // 2)

                # Skip tiny boxes
                if (x2 - x1) < 10 or (y2 - y1) < 10:
                    continue

                # Crop bird
                crop = image[y1:y2, x1:x2]

                metadata = {
                    'image_path': str(image_file),
                    'image_name': image_name,
                    'bbox_index': bbox_idx,
                    'bbox_coords': (x1, y1, x2, y2),
                    'bbox_yolo': (x_center, y_center, box_w, box_h),
                    'existing_species': parts[5] if len(parts) > 5 else None
                }

                crops.append((crop, metadata))

        print(f"Extracted {len(crops)} bird crops")
        return crops

    def extract_features(self, crop: np.ndarray) -> np.ndarray:
        """
        Extract visual features from a bird crop.

        Features:
        1. Color histogram (HSV) - 48 bins (16 per channel)
        2. Size features - width, height, aspect ratio, area
        3. Brightness - mean intensity in each channel
        4. Texture - gradient magnitude statistics

        Args:
            crop: BGR image of bird

        Returns:
            Feature vector (1D numpy array)
        """
        features = []

        # Resize to standard size for consistent feature extraction
        crop_resized = cv2.resize(crop, (128, 128))

        # 1. Color Histogram (HSV space works better for birds)
        hsv = cv2.cvtColor(crop_resized, cv2.COLOR_BGR2HSV)
        hist_h = cv2.calcHist([hsv], [0], None, [16], [0, 180])
        hist_s = cv2.calcHist([hsv], [1], None, [16], [0, 256])
        hist_v = cv2.calcHist([hsv], [2], None, [16], [0, 256])

        # Normalize histograms
        hist_h = hist_h.flatten() / hist_h.sum()
        hist_s = hist_s.flatten() / hist_s.sum()
        hist_v = hist_v.flatten() / hist_v.sum()

        features.extend(hist_h)
        features.extend(hist_s)
        features.extend(hist_v)

        # 2. Size features (important for distinguishing large vs small species)
        height, width = crop.shape[:2]
        aspect_ratio = width / height if height > 0 else 1.0
        area = width * height

        features.extend([
            width / 1000.0,  # Normalize
            height / 1000.0,
            aspect_ratio,
            area / 1000000.0
        ])

        # 3. Brightness features
        mean_bgr = crop_resized.mean(axis=(0, 1))
        features.extend(mean_bgr / 255.0)  # Normalize to [0, 1]

        # 4. Texture features (gradient magnitude)
        gray = cv2.cvtColor(crop_resized, cv2.COLOR_BGR2GRAY)
        grad_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
        grad_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
        grad_mag = np.sqrt(grad_x**2 + grad_y**2)

        features.extend([
            grad_mag.mean() / 255.0,
            grad_mag.std() / 255.0,
        ])

        return np.array(features)

    def cluster(self, method: str = 'kmeans'):
        """
        Perform clustering on extracted features.

        Args:
            method: 'kmeans' or 'dbscan'
                - kmeans: Fixed number of clusters (n_clusters parameter)
                - dbscan: Automatic number of clusters (density-based)
        """
        print("\n=== Extracting Features ===")
        crops = self.extract_bird_crops()

        if len(crops) == 0:
            print("Error: No bird crops found!")
            return

        for crop, meta in crops:
            feat = self.extract_features(crop)
            self.features.append(feat)
            self.metadata.append(meta)

        X = np.array(self.features)
        print(f"Feature matrix shape: {X.shape}")

        # Standardize features (important for clustering)
        print("\n=== Standardizing Features ===")
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        # Dimensionality reduction for visualization
        print("\n=== Dimensionality Reduction ===")

        # PCA (fast, linear)
        print("Running PCA...")
        pca = PCA(n_components=2)
        X_pca = pca.fit_transform(X_scaled)
        print(f"PCA explained variance: {pca.explained_variance_ratio_.sum():.2%}")

        # t-SNE (slower, better for visualization)
        print("Running t-SNE (this may take a few minutes)...")
        tsne = TSNE(n_components=2, random_state=42, perplexity=30, max_iter=1000)
        X_tsne = tsne.fit_transform(X_scaled)
        print("t-SNE complete!")

        # Clustering
        print(f"\n=== Clustering with {method} ===")
        if method == 'kmeans':
            clusterer = KMeans(n_clusters=self.n_clusters, random_state=42, n_init=10)
            labels = clusterer.fit_predict(X_scaled)
        elif method == 'dbscan':
            # DBSCAN automatically determines number of clusters
            clusterer = DBSCAN(eps=0.5, min_samples=10)
            labels = clusterer.fit_predict(X_scaled)
            self.n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
            print(f"DBSCAN found {self.n_clusters} clusters")
        else:
            raise ValueError(f"Unknown method: {method}")

        # Save clustering results
        print("\n=== Saving Results ===")
        clustering_results = {
            'method': method,
            'n_clusters': self.n_clusters,
            'labels': labels.tolist(),
            'metadata': self.metadata,
            'scaler': scaler,
            'pca': pca,
            'X_pca': X_pca.tolist(),
            'tsne': tsne,
            'X_tsne': X_tsne.tolist()
        }

        with open(self.clusters_dir / 'clustering_results.pkl', 'wb') as f:
            pickle.dump(clustering_results, f)

        # Export cluster assignments to JSON (for Nestperts)
        self.export_for_labeling(labels)

        # Visualize clusters (PCA)
        self.visualize_clusters(X_pca, labels, 'PCA')

        # Visualize clusters (t-SNE)
        self.visualize_clusters(X_tsne, labels, 't-SNE')

        # Create cluster preview images
        self.create_cluster_previews(crops, labels)

        print(f"\n✅ Clustering complete!")
        print(f"📁 Results saved to: {self.clusters_dir}")

    def export_for_labeling(self, labels: np.ndarray):
        """
        Export cluster assignments for expert labeling in Nestperts.

        Creates a JSON file with cluster information that Nestperts can load.
        """
        cluster_data = defaultdict(list)

        for idx, (label, meta) in enumerate(zip(labels, self.metadata)):
            cluster_data[int(label)].append({
                'image_path': meta['image_path'],
                'image_name': meta['image_name'],
                'bbox_index': meta['bbox_index'],
                'bbox_coords': meta['bbox_coords'],
                'bbox_yolo': meta['bbox_yolo']
            })

        # Add cluster statistics
        export_data = {
            'total_birds': len(labels),
            'n_clusters': self.n_clusters,
            'clusters': {}
        }

        for cluster_id, birds in cluster_data.items():
            if cluster_id == -1:  # DBSCAN noise points
                continue

            export_data['clusters'][str(cluster_id)] = {
                'size': len(birds),
                'birds': birds[:100],  # Limit to first 100 for preview
                'total_birds': len(birds),
                'species_label': None,  # To be filled by expert
                'confidence': None  # Expert confidence rating
            }

        output_file = self.clusters_dir / 'clusters_for_labeling.json'
        with open(output_file, 'w') as f:
            json.dump(export_data, f, indent=2)

        print(f"📋 Cluster assignments exported to: {output_file}")
        print(f"   Total clusters: {len(export_data['clusters'])}")
        print(f"   Birds per cluster: {[c['total_birds'] for c in export_data['clusters'].values()]}")

    def visualize_clusters(self, X_2d: np.ndarray, labels: np.ndarray, method_name: str = 'PCA'):
        """
        Create a 2D visualization of clusters.

        Args:
            X_2d: 2D projection of features
            labels: Cluster labels
            method_name: Name of dimensionality reduction method (PCA or t-SNE)
        """
        plt.figure(figsize=(12, 8))
        scatter = plt.scatter(X_2d[:, 0], X_2d[:, 1], c=labels,
                            cmap='tab20', alpha=0.6, s=10)
        plt.colorbar(scatter, label='Cluster ID')

        if method_name == 'PCA':
            plt.xlabel('First Principal Component')
            plt.ylabel('Second Principal Component')
        elif method_name == 't-SNE':
            plt.xlabel('t-SNE Dimension 1')
            plt.ylabel('t-SNE Dimension 2')
        else:
            plt.xlabel('Dimension 1')
            plt.ylabel('Dimension 2')

        plt.title(f'Bird Clusters using {method_name} (n={self.n_clusters})')
        plt.grid(alpha=0.3)

        output_file = self.clusters_dir / f'cluster_visualization_{method_name.lower().replace("-", "")}.png'
        plt.savefig(output_file, dpi=150, bbox_inches='tight')
        print(f"📊 {method_name} visualization saved to: {output_file}")
        plt.close()

    def create_cluster_previews(self, crops: List[Tuple[np.ndarray, Dict]],
                                labels: np.ndarray, max_per_cluster: int = 20):
        """
        Create grid images showing representative birds from each cluster.

        This helps experts quickly see what each cluster looks like.
        """
        cluster_data = defaultdict(list)

        for idx, (crop_meta, label) in enumerate(zip(crops, labels)):
            if label == -1:  # Skip noise
                continue
            crop, meta = crop_meta
            cluster_data[label].append((crop, meta))

        print(f"\n📸 Creating cluster preview images...")

        for cluster_id, items in cluster_data.items():
            # Sample up to max_per_cluster representative birds
            sample_size = min(len(items), max_per_cluster)
            sampled_items = np.random.choice(len(items), size=sample_size, replace=False)

            # Create grid
            grid_size = int(np.ceil(np.sqrt(sample_size)))
            cell_size = 128
            grid_image = np.ones((grid_size * cell_size, grid_size * cell_size, 3),
                                dtype=np.uint8) * 255

            for i, idx in enumerate(sampled_items):
                crop, meta = items[idx]
                row = i // grid_size
                col = i % grid_size

                # Resize crop to fit cell
                crop_resized = cv2.resize(crop, (cell_size, cell_size))

                y1 = row * cell_size
                y2 = (row + 1) * cell_size
                x1 = col * cell_size
                x2 = (col + 1) * cell_size

                grid_image[y1:y2, x1:x2] = crop_resized

            # Save preview
            cluster_dir = self.clusters_dir / f"cluster_{cluster_id:03d}"
            cluster_dir.mkdir(exist_ok=True)

            preview_file = cluster_dir / "preview.jpg"
            cv2.imwrite(str(preview_file), grid_image)

            # Save cluster info
            info = {
                'cluster_id': int(cluster_id),
                'size': len(items),
                'sample_size': sample_size,
                'species_label': None  # To be filled by expert
            }

            with open(cluster_dir / "info.json", 'w') as f:
                json.dump(info, f, indent=2)

        print(f"✅ Created previews for {len(cluster_data)} clusters")


def main():
    parser = argparse.ArgumentParser(
        description="Cluster birds by visual similarity to reduce annotation effort"
    )
    parser.add_argument('--data', type=str, required=True,
                       help='Path to YOLO dataset directory')
    parser.add_argument('--clusters', type=int, default=30,
                       help='Number of clusters (default: 30)')
    parser.add_argument('--method', choices=['kmeans', 'dbscan'], default='kmeans',
                       help='Clustering method (default: kmeans)')

    args = parser.parse_args()

    print("=" * 60)
    print("🦅 BIRD CLUSTERING PIPELINE")
    print("=" * 60)
    print(f"\nDataset: {args.data}")
    print(f"Method: {args.method}")
    print(f"Target clusters: {args.clusters}")
    print("\nThis will:")
    print("1. Extract all bird crops from labeled images")
    print("2. Extract visual features (color, size, texture)")
    print("3. Cluster birds by similarity")
    print("4. Create preview images for each cluster")
    print("5. Export cluster data for expert labeling")
    print("\n" + "=" * 60 + "\n")

    clusterer = BirdClusterer(args.data, n_clusters=args.clusters)
    clusterer.cluster(method=args.method)

    print("\n" + "=" * 60)
    print("🎯 NEXT STEPS:")
    print("=" * 60)
    print(f"1. Open cluster previews: {clusterer.clusters_dir}")
    print(f"2. Review each cluster preview image")
    print(f"3. Assign species labels to clusters in Nestperts")
    print(f"4. Run training with cluster labels")
    print("=" * 60)


if __name__ == '__main__':
    main()
