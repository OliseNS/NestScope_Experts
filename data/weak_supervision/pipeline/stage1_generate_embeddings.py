"""
Stage 1: Generate Embeddings for All Bird Crops

Extracts EfficientNet-B0 embeddings (1280-dim) for all 100K bird crops.
This is done once and reused by all subsequent stages.
"""

import sys
from pathlib import Path
import json
import numpy as np
from datetime import datetime
from tqdm import tqdm
import torch
from PIL import Image
import cv2

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from labeller.services.embedding_service import EmbeddingExtractor


class EmbeddingGenerator:
    """
    Generates and saves embeddings for all bird crops.
    Reuses existing EmbeddingExtractor from labeller/services.
    """

    def __init__(self, crops_dir: str, output_dir: str, model_name: str = 'efficientnet'):
        """
        Args:
            crops_dir: Path to bird_crops directory (contains images/ and metadata.json)
            output_dir: Path to output directory for embeddings
            model_name: Model to use ('efficientnet', 'resnet50', 'clip', 'dinov2', 'siglip')
        """
        self.crops_dir = Path(crops_dir)
        self.images_dir = self.crops_dir / "images"
        self.metadata_path = self.crops_dir / "metadata.json"
        self.output_dir = Path(output_dir) / "embeddings"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.model_name = model_name

        # Load metadata
        print(f"Loading metadata from {self.metadata_path}...")
        with open(self.metadata_path, 'r') as f:
            self.metadata = json.load(f)

        self.crops = self.metadata['crops']
        print(f"✓ Loaded {len(self.crops)} crops")

        # Initialize embedding extractor
        print(f"\nInitializing {model_name} model...")
        self.extractor = EmbeddingExtractor(model_name=model_name)
        print(f"✓ Model ready ({self.extractor.embedding_dim}-dimensional embeddings)")

    def generate_all_embeddings(self, batch_size: int = None, low_memory: bool = False):
        """
        Extract embeddings for all crops.

        Args:
            batch_size: Batch size for processing (None = auto-detect)
            low_memory: If True, process in small chunks to save RAM

        Returns:
            Path to saved embeddings_all.npy
        """
        print("\n" + "=" * 60)
        print("GENERATING EMBEDDINGS")
        print("=" * 60)

        # Determine batch size
        if batch_size is None:
            batch_size = self.extractor.recommended_batch_size

        print(f"Batch size: {batch_size}")
        print(f"Low memory mode: {low_memory}")
        print(f"Total crops: {len(self.crops)}")

        # Pre-allocate array for embeddings
        n_crops = len(self.crops)
        emb_dim = self.extractor.embedding_dim
        all_embeddings = np.zeros((n_crops, emb_dim), dtype=np.float32)

        # Process in batches
        print(f"\nProcessing {n_crops} crops...")

        with torch.no_grad():  # Disable gradient computation for inference
            for i in tqdm(range(0, n_crops, batch_size), desc="Extracting embeddings"):
                batch_end = min(i + batch_size, n_crops)
                batch_crops = self.crops[i:batch_end]

                # Load images (convert PIL to numpy BGR for embedding service)
                batch_images = []
                for crop in batch_crops:
                    img_path = self.images_dir / crop['crop_filename']
                    try:
                        # Load with OpenCV (BGR format) - this is what embedding service expects
                        img = cv2.imread(str(img_path))
                        if img is None:
                            raise ValueError(f"Failed to load {img_path}")
                        batch_images.append(img)
                    except Exception as e:
                        print(f"\n⚠️  Error loading {img_path}: {e}")
                        # Use black image as placeholder
                        batch_images.append(np.zeros((224, 224, 3), dtype=np.uint8))

                # Extract embeddings
                batch_embeddings = self.extractor.extract_embeddings_batch(
                    batch_images,
                    batch_size=len(batch_images)
                )

                # Store in pre-allocated array
                all_embeddings[i:batch_end] = batch_embeddings

                # Free memory in low memory mode
                if low_memory:
                    del batch_images
                    del batch_embeddings
                    if torch.cuda.is_available():
                        torch.cuda.empty_cache()

        # Save embeddings
        embeddings_path = self.output_dir / "embeddings_all.npy"
        print(f"\n💾 Saving embeddings to {embeddings_path}...")
        np.save(embeddings_path, all_embeddings)
        print(f"✓ Saved: {all_embeddings.shape}")

        # Create index mapping crop_id → array index
        print("Creating embedding index...")
        self._create_embedding_index()

        # Save config
        print("Saving configuration...")
        self._save_config()

        print("\n" + "=" * 60)
        print("✅ EMBEDDING GENERATION COMPLETE")
        print("=" * 60)
        print(f"Embeddings: {embeddings_path}")
        print(f"Shape: {all_embeddings.shape}")
        print(f"Size: {all_embeddings.nbytes / 1024**2:.1f} MB")

        return embeddings_path

    def _create_embedding_index(self):
        """
        Create mapping from crop_id to embedding array index.

        This allows fast lookup: given crop_id, find its embedding
        in the embeddings_all.npy array.

        Returns:
            Path to embeddings_index.json
        """
        index = {crop['crop_id']: idx for idx, crop in enumerate(self.crops)}

        index_path = self.output_dir / "embeddings_index.json"
        with open(index_path, 'w') as f:
            json.dump(index, f)

        print(f"✓ Saved embedding index: {index_path}")
        return index_path

    def _save_config(self):
        """
        Save embedding configuration metadata.

        Returns:
            Path to embeddings_config.json
        """
        config = {
            "model": self.model_name,
            "embedding_dim": self.extractor.embedding_dim,
            "device": self.extractor.device,
            "n_crops": len(self.crops),
            "generated_at": datetime.now().isoformat(),
            "crops_dir": str(self.crops_dir),
        }

        config_path = self.output_dir / "embeddings_config.json"
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)

        print(f"✓ Saved config: {config_path}")
        return config_path


def main():
    """
    Main entry point for Stage 1.
    """
    import argparse

    parser = argparse.ArgumentParser(description='Stage 1: Generate embeddings for bird crops')
    parser.add_argument('--crops-dir', type=str,
                        default='data/weak_supervision/bird_crops',
                        help='Path to bird_crops directory')
    parser.add_argument('--output-dir', type=str,
                        default='data/weak_supervision/bird_crops',
                        help='Path to output directory')
    parser.add_argument('--model', type=str, default='efficientnet',
                        choices=['efficientnet', 'resnet50', 'clip', 'dinov2', 'siglip'],
                        help='Embedding model to use')
    parser.add_argument('--batch-size', type=int, default=None,
                        help='Batch size (None = auto-detect)')
    parser.add_argument('--low-memory', action='store_true',
                        help='Enable low memory mode (slower but uses less RAM)')

    args = parser.parse_args()

    # Create generator
    generator = EmbeddingGenerator(
        crops_dir=args.crops_dir,
        output_dir=args.output_dir,
        model_name=args.model
    )

    # Generate embeddings
    generator.generate_all_embeddings(
        batch_size=args.batch_size,
        low_memory=args.low_memory
    )


if __name__ == '__main__':
    main()
