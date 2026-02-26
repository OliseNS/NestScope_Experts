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


def main():
    parser = argparse.ArgumentParser(
        description='Cluster birds using deep learning embeddings and visualize in 3D',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Use DINOv2 (recommended for best clustering results)
  python scripts/cluster_birds.py --data labeller/nestvision --model dinov2 --clusters 30

  # Use SigLIP (fastest with great accuracy - RECOMMENDED)
  python scripts/cluster_birds.py --data labeller/nestvision --model siglip --clusters 30

  # Use EfficientNet (faster, but less accurate)
  python scripts/cluster_birds.py --data labeller/nestvision --model efficientnet --clusters 25

  # Use DBSCAN instead of K-means
  python scripts/cluster_birds.py --data labeller/nestvision --model siglip --method dbscan

Models available:
  - siglip: Vision-language model (RECOMMENDED - fastest with semantic understanding)
  - dinov2: Self-supervised ViT (best for fine-grained visual similarity)
  - efficientnet: Fast CNN (good balance of speed and accuracy)
  - resnet50: Classic CNN baseline
  - clip: Semantic understanding (experimental)

Clustering methods:
  - kmeans: Requires specifying number of clusters (faster)
  - dbscan: Automatically finds clusters (slower, may have noise)
        """
    )

    parser.add_argument(
        '--data',
        type=str,
        required=True,
        help='Path to YOLO dataset directory (contains images/ and labels/)'
    )

    parser.add_argument(
        '--output',
        type=str,
        default=None,
        help='Output directory for crops and results (default: <data>/bird_crops)'
    )

    parser.add_argument(
        '--model',
        type=str,
        default='siglip',
        choices=['siglip', 'dinov2', 'efficientnet', 'resnet50', 'clip'],
        help='Embedding model to use (default: siglip for best speed/accuracy)'
    )

    parser.add_argument(
        '--clusters',
        type=int,
        default=30,
        help='Number of clusters for K-means (default: 30)'
    )

    parser.add_argument(
        '--method',
        type=str,
        default='kmeans',
        choices=['kmeans', 'dbscan'],
        help='Clustering method (default: kmeans)'
    )

    parser.add_argument(
        '--force',
        action='store_true',
        help='Force re-extraction of crops and embeddings'
    )

    parser.add_argument(
        '--force-crops',
        action='store_true',
        help='Force re-extraction of crops only'
    )

    parser.add_argument(
        '--force-embeddings',
        action='store_true',
        help='Force re-generation of embeddings only'
    )

    args = parser.parse_args()

    # Validate dataset path
    data_path = Path(args.data)
    if not data_path.exists():
        print(f"❌ Error: Dataset not found at {args.data}")
        sys.exit(1)

    if not (data_path / "images").exists():
        print(f"❌ Error: No 'images' directory found in {args.data}")
        sys.exit(1)

    if not (data_path / "labels").exists():
        print(f"❌ Error: No 'labels' directory found in {args.data}")
        sys.exit(1)

    # Set output directory
    output_dir = args.output if args.output else str(data_path / "bird_crops")

    # Determine force flags
    force_crops = args.force or args.force_crops
    force_embeddings = args.force or args.force_embeddings

    # Clear existing data if full force flag is set
    if args.force:
        output_path = Path(output_dir)
        if output_path.exists():
            print(f"🗑️  Clearing existing data at {output_dir}...")
            import shutil
            shutil.rmtree(output_path)
            force_crops = False  # No need to force if we just deleted everything
            force_embeddings = False

    # Run pipeline
    print("\n" + "=" * 70)
    print("🦅 BIRD CLUSTERING PIPELINE")
    print("=" * 70)
    print(f"Dataset:    {args.data}")
    print(f"Model:      {args.model}")
    print(f"Method:     {args.method}")
    if args.method == 'kmeans':
        print(f"Clusters:   {args.clusters}")
    else:
        print(f"Clusters:   auto-detected")
    print(f"Output:     {output_dir}")
    print("=" * 70 + "\n")

    try:
        results = run_full_pipeline(
            dataset_dir=args.data,
            output_dir=output_dir,
            model_name=args.model,
            n_clusters=args.clusters,
            method=args.method,
            force_crops=force_crops,
            force_embeddings=force_embeddings
        )

        print("\n" + "=" * 70)
        print("✅ SUCCESS!")
        print("=" * 70)
        print(f"📊 Clustered {results['total_birds']:,} birds into {results['n_clusters']} groups")
        print(f"📁 Results saved to: {results['clusters_dir']}")
        print(f"🌐 Web visualization: {results['viz_file']}")
        print("\n🎯 Next steps:")
        print("   1. Start Nestperts: python labeller/app.py --data labeller/nestvision")
        print("   2. Open browser: http://localhost:5000/clusters")
        print("   3. Explore clusters in 3D!")
        print("=" * 70 + "\n")

    except KeyboardInterrupt:
        print("\n\n⚠️  Pipeline interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Pipeline failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
