"""
Bird Image Embedding Service

Uses deep learning models to extract semantic embeddings from bird images.
These embeddings capture fine-grained visual features better than hand-crafted
features (color histograms, etc.).

Supported models:
- EfficientNet-B0: Fast, accurate, 1280-dim embeddings
- ResNet-50: Standard baseline, 2048-dim embeddings
- CLIP: Semantic understanding, 512-dim embeddings
- DINOv2: Self-supervised, excellent for fine-grained visual bird clustering, 768-dim embeddings (Base)
- SigLIP (RECOMMENDED): Vision-language model, faster than DINOv2, semantic understanding, 768-dim embeddings
"""

import torch
import torch.nn as nn
from torchvision import transforms, models
import numpy as np
import cv2
from pathlib import Path
from typing import List, Dict, Tuple
import json
from tqdm import tqdm


class EmbeddingExtractor:
    """
    Extract deep learning embeddings from bird images.

    This captures fine-grained visual features that are better for
    clustering similar-looking birds than basic color/size features.
    """

    def __init__(self, model_name: str = 'efficientnet', device: str = None):
        """
        Args:
            model_name: 'efficientnet', 'resnet50', 'clip', 'dinov2', or 'siglip'
            device: 'cuda', 'cpu', or None (auto-detect)
        """
        self.model_name = model_name
        self.device = device or ('cuda' if torch.cuda.is_available() else 'cpu')

        print(f"Loading {model_name} model on {self.device}...")
        self.model, self.preprocess, self.embedding_dim = self._load_model(model_name)
        self.model.eval()
        self.model.to(self.device)
        print(f"✓ Model loaded ({self.embedding_dim}-dimensional embeddings)")

        # Auto-tune batch size based on available memory
        self.recommended_batch_size = self._get_recommended_batch_size()
        if self.device == 'cuda':
            print(f"💡 Recommended batch size: {self.recommended_batch_size}")

    def _load_model(self, model_name: str) -> Tuple[nn.Module, transforms.Compose, int]:
        """Load pre-trained model and preprocessing"""

        if model_name == 'efficientnet':
            # EfficientNet-B0: Fast, accurate, compact
            try:
                import timm
                model = timm.create_model('efficientnet_b0', pretrained=True, num_classes=0)
                embedding_dim = 1280
            except ImportError:
                # Fallback to torchvision
                model = models.efficientnet_b0(pretrained=True)
                model.classifier = nn.Identity()  # Remove classification head
                embedding_dim = 1280

            preprocess = transforms.Compose([
                transforms.Resize(256),
                transforms.CenterCrop(224),
                transforms.ToTensor(),
                transforms.Normalize(mean=[0.485, 0.456, 0.406],
                                   std=[0.229, 0.224, 0.225])
            ])

        elif model_name == 'resnet50':
            # ResNet-50: Standard baseline
            model = models.resnet50(pretrained=True)
            model.fc = nn.Identity()  # Remove classification head
            embedding_dim = 2048

            preprocess = transforms.Compose([
                transforms.Resize(256),
                transforms.CenterCrop(224),
                transforms.ToTensor(),
                transforms.Normalize(mean=[0.485, 0.456, 0.406],
                                   std=[0.229, 0.224, 0.225])
            ])

        elif model_name == 'clip':
            # CLIP: Semantic understanding (requires open_clip)
            try:
                import open_clip
                model, _, preprocess = open_clip.create_model_and_transforms(
                    'ViT-B-32', pretrained='openai'
                )
                embedding_dim = 512
            except ImportError:
                raise ImportError(
                    "CLIP requires open_clip: pip install open_clip_torch"
                )

        elif model_name == 'dinov2':
            # DINOv2: Self-supervised, excellent for fine-grained
            # Default to BASE model for better speed/accuracy balance
            # Options: 'dinov2_vits14' (fast), 'dinov2_vitb14' (balanced), 'dinov2_vitl14' (slow but best)
            try:
                # Use base model - 3-4x faster than large, ~98% accuracy
                variant = 'dinov2_vitb14'  # Change to 'dinov2_vitl14' for maximum accuracy
                model = torch.hub.load('facebookresearch/dinov2', variant)

                # Embedding dimensions by variant
                embedding_dims = {'dinov2_vits14': 384, 'dinov2_vitb14': 768, 'dinov2_vitl14': 1024}
                embedding_dim = embedding_dims[variant]

                # Use 384x384 for speed (native DINOv2 supports multiple resolutions)
                # Change to 518 for maximum detail (but 2x slower)
                resolution = 384  # Good balance of speed and quality
                preprocess = transforms.Compose([
                    transforms.Resize(resolution),
                    transforms.CenterCrop(resolution),
                    transforms.ToTensor(),
                    transforms.Normalize(mean=[0.485, 0.456, 0.406],
                                       std=[0.229, 0.224, 0.225])
                ])
            except Exception as e:
                raise RuntimeError(f"Failed to load DINOv2: {e}")

        elif model_name == 'siglip':
            # SigLIP: Google's improved CLIP with sigmoid loss
            # FASTER and MORE MEMORY EFFICIENT than DINOv2
            # Better semantic understanding (vision + language)
            try:
                import timm

                # Use SigLIP base model - great balance of speed/accuracy
                # Available variants:
                # - vit_base_patch16_siglip_256: Fast, 256 resolution, 768-dim
                # - vit_base_patch16_siglip_384: Balanced, 384 resolution, 768-dim (RECOMMENDED)
                # - vit_so400m_patch14_siglip_384: Large, 384 resolution, 1152-dim

                variant = 'vit_base_patch16_siglip_384'
                model = timm.create_model(variant, pretrained=True, num_classes=0)
                embedding_dim = 768  # Base model output dimension

                # SigLIP uses 384x384 resolution for base model
                # Get the preprocessing config from the model
                data_config = timm.data.resolve_model_data_config(model)
                preprocess = timm.data.create_transform(**data_config, is_training=False)

                print(f"✓ Loaded SigLIP variant: {variant}")

            except ImportError:
                raise ImportError(
                    "SigLIP requires timm>=0.9.0: pip install --upgrade timm"
                )
            except Exception as e:
                raise RuntimeError(f"Failed to load SigLIP: {e}")

        else:
            raise ValueError(f"Unknown model: {model_name}")

        return model, preprocess, embedding_dim

    def _get_recommended_batch_size(self) -> int:
        """
        Automatically determine safe batch size based on:
        - Device (CPU vs GPU)
        - Available GPU memory (if GPU)
        - Model size
        """
        if self.device == 'cpu':
            # CPU: use smaller batches (no memory constraint, but slower)
            return 8

        try:
            # GPU: check available memory
            if torch.cuda.is_available():
                gpu_mem_gb = torch.cuda.get_device_properties(0).total_memory / (1024**3)

                # Conservative batch size based on GPU memory
                if gpu_mem_gb < 4:
                    batch_size = 4  # Low memory GPU
                elif gpu_mem_gb < 8:
                    batch_size = 8  # Mid-range GPU
                elif gpu_mem_gb < 12:
                    batch_size = 16  # High-end consumer GPU
                else:
                    batch_size = 32  # Professional GPU

                # Reduce for larger models
                if self.model_name == 'dinov2':
                    batch_size = max(4, batch_size // 2)  # DINOv2 needs more memory
                elif self.model_name == 'siglip':
                    # SigLIP is more efficient, can use larger batches
                    batch_size = min(32, int(batch_size * 1.5))

                return batch_size
        except:
            pass

        # Fallback
        return 8

    @torch.no_grad()
    def extract_embedding(self, image: np.ndarray) -> np.ndarray:
        """
        Extract embedding from a single image.

        Args:
            image: BGR image (OpenCV format, numpy array)

        Returns:
            Embedding vector (1D numpy array)
        """
        from PIL import Image

        # Convert BGR to RGB
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        # Convert numpy array to PIL Image (torchvision transforms expect PIL Images)
        pil_img = Image.fromarray(image_rgb)

        # Preprocess
        input_tensor = self.preprocess(pil_img).unsqueeze(0).to(self.device)

        # Extract features
        embedding = self.model(input_tensor)

        # Convert to numpy
        if isinstance(embedding, tuple):
            embedding = embedding[0]  # Some models return tuples

        return embedding.detach().cpu().numpy().flatten()

    def extract_embeddings_batch(self, images: List[np.ndarray],
                                 batch_size: int = 32) -> np.ndarray:
        """
        Extract embeddings from multiple images in batches.

        Args:
            images: List of BGR images (numpy arrays from OpenCV)
            batch_size: Number of images to process at once

        Returns:
            Embeddings array (N x embedding_dim)
        """
        from PIL import Image

        embeddings = []

        for i in tqdm(range(0, len(images), batch_size), desc="Extracting embeddings"):
            batch_images = images[i:i + batch_size]

            # Preprocess batch
            batch_tensors = []
            for img in batch_images:
                # Convert BGR (OpenCV) to RGB
                img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

                # Convert numpy array to PIL Image (torchvision transforms expect PIL Images)
                pil_img = Image.fromarray(img_rgb)

                # Apply preprocessing transforms
                tensor = self.preprocess(pil_img)
                batch_tensors.append(tensor)

            batch_tensor = torch.stack(batch_tensors).to(self.device)

            # Extract features
            batch_embeddings = self.model(batch_tensor)

            if isinstance(batch_embeddings, tuple):
                batch_embeddings = batch_embeddings[0]

            embeddings.append(batch_embeddings.detach().cpu().numpy())

        return np.vstack(embeddings)


class BirdCropManager:
    """
    Manages bird crops and their embeddings.

    Directory structure:
        bird_crops/
            ├── images/
            │   ├── bird_000000.jpg
            │   ├── bird_000001.jpg
            │   └── ...
            ├── embeddings.npy       # All embeddings (N x embedding_dim)
            ├── metadata.json        # Crop metadata
            └── config.json          # Embedding model config
    """

    def __init__(self, crops_dir: str):
        """
        Args:
            crops_dir: Path to bird_crops directory
        """
        self.crops_dir = Path(crops_dir)
        self.images_dir = self.crops_dir / "images"
        self.embeddings_file = self.crops_dir / "embeddings.npy"
        self.metadata_file = self.crops_dir / "metadata.json"
        self.config_file = self.crops_dir / "config.json"

        # Create directories
        self.crops_dir.mkdir(parents=True, exist_ok=True)
        self.images_dir.mkdir(exist_ok=True)

    def extract_and_save_crops(self, dataset_dir: str, resize: int = None,
                               min_size: int = 20, max_size: int = 10000,
                               padding_percent: float = 0.15):
        """
        Extract bird crops from YOLO dataset and save to crops directory.

        Args:
            dataset_dir: Path to YOLO dataset (contains images/ and labels/)
            resize: Resize crops to this size (None to keep original - RECOMMENDED for DINOv2)
            min_size: Minimum crop size in pixels
            max_size: Maximum crop size in pixels
            padding_percent: Add padding around crops (0.15 = 15% padding on each side)
        """
        dataset_path = Path(dataset_dir)
        images_dir = dataset_path / "images"
        labels_dir = dataset_path / "labels"

        print(f"Extracting crops from {dataset_dir}...")

        metadata = []
        crop_count = 0

        label_files = list(labels_dir.glob("*.txt"))

        for label_file in tqdm(label_files, desc="Extracting crops"):
            # Find corresponding image
            image_name = label_file.stem
            image_file = self._find_image_file(images_dir, image_name)

            if not image_file:
                continue

            # Load image
            image = cv2.imread(str(image_file))
            if image is None:
                continue

            height, width = image.shape[:2]

            # Read YOLO labels
            with open(label_file, 'r') as f:
                lines = f.readlines()

            # Extract each bird
            for bbox_idx, line in enumerate(lines):
                parts = line.strip().split()
                if len(parts) < 5:
                    continue

                try:
                    class_id = int(parts[0])
                    x_center, y_center, box_w, box_h = map(float, parts[1:5])
                    species = parts[5] if len(parts) > 5 else None
                except (ValueError, IndexError):
                    continue

                # Convert to pixel coords
                x_center_px = int(x_center * width)
                y_center_px = int(y_center * height)
                box_w_px = int(box_w * width)
                box_h_px = int(box_h * height)

                # Add padding to capture full bird context
                padding_w = int(box_w_px * padding_percent)
                padding_h = int(box_h_px * padding_percent)

                x1 = max(0, x_center_px - box_w_px // 2 - padding_w)
                y1 = max(0, y_center_px - box_h_px // 2 - padding_h)
                x2 = min(width, x_center_px + box_w_px // 2 + padding_w)
                y2 = min(height, y_center_px + box_h_px // 2 + padding_h)

                # Filter by size
                crop_width = x2 - x1
                crop_height = y2 - y1

                if crop_width < min_size or crop_height < min_size:
                    continue
                if crop_width > max_size or crop_height > max_size:
                    continue

                # Crop bird
                crop = image[y1:y2, x1:x2]

                # Resize if requested (not recommended for DINOv2 - preserves more detail at native res)
                if resize:
                    crop = cv2.resize(crop, (resize, resize),
                                    interpolation=cv2.INTER_LANCZOS4)  # Higher quality interpolation

                # Save crop
                crop_filename = f"bird_{crop_count:06d}.jpg"
                crop_path = self.images_dir / crop_filename
                cv2.imwrite(str(crop_path), crop, [cv2.IMWRITE_JPEG_QUALITY, 95])

                # Store metadata
                metadata.append({
                    'crop_id': crop_count,
                    'crop_filename': crop_filename,
                    'source_image': image_name,
                    'bbox_index': bbox_idx,
                    'class_id': class_id,
                    'bbox_pixel': [x1, y1, x2, y2],
                    'bbox_yolo': [x_center, y_center, box_w, box_h],
                    'crop_size': [crop_width, crop_height],
                    'species': species
                })

                crop_count += 1

        # Save metadata
        with open(self.metadata_file, 'w') as f:
            json.dump({
                'total_crops': crop_count,
                'source_dataset': str(dataset_dir),
                'resize': resize,
                'crops': metadata
            }, f, indent=2)

        print(f"✓ Extracted {crop_count} crops to {self.crops_dir}")

    def generate_embeddings(self, model_name: str = 'efficientnet',
                          batch_size: int = None,
                          low_memory: bool = False):
        """
        Generate embeddings for all bird crops.

        Args:
            model_name: Model to use ('efficientnet', 'resnet50', 'clip', 'dinov2', 'siglip')
            batch_size: Batch size for inference (None = auto-tune based on available memory)
            low_memory: If True, loads crops in chunks (slower but uses less RAM)
        """
        print(f"\n=== Generating Embeddings with {model_name} ===")

        # Load extractor
        extractor = EmbeddingExtractor(model_name)

        # Auto-tune batch size if not specified
        if batch_size is None:
            batch_size = extractor.recommended_batch_size
            print(f"Using auto-tuned batch size: {batch_size}")

        # Get crop files
        crop_files = sorted(self.images_dir.glob("bird_*.jpg"))
        print(f"Found {len(crop_files)} crops")

        if low_memory:
            # Memory-efficient mode: load in chunks of 1000 images
            print("Low-memory mode: loading crops in chunks")
            chunk_size = 1000
            all_embeddings = []

            for chunk_start in tqdm(range(0, len(crop_files), chunk_size), desc="Processing chunks"):
                chunk_end = min(chunk_start + chunk_size, len(crop_files))
                chunk_files = crop_files[chunk_start:chunk_end]

                # Load chunk
                chunk_crops = []
                for crop_file in chunk_files:
                    crop = cv2.imread(str(crop_file))
                    if crop is not None:
                        chunk_crops.append(crop)

                # Extract embeddings for this chunk
                if chunk_crops:
                    chunk_embeddings = extractor.extract_embeddings_batch(
                        chunk_crops,
                        batch_size=batch_size
                    )
                    all_embeddings.append(chunk_embeddings)

            embeddings = np.vstack(all_embeddings)
        else:
            # Standard mode: load all crops (faster, uses more RAM)
            print("Loading all crops into memory...")
            crops = []
            for crop_file in tqdm(crop_files, desc="Loading crops"):
                crop = cv2.imread(str(crop_file))
                if crop is not None:
                    crops.append(crop)

            # Extract embeddings
            print(f"Extracting embeddings with batch size {batch_size}...")
            embeddings = extractor.extract_embeddings_batch(crops, batch_size=batch_size)

        # Save embeddings
        np.save(self.embeddings_file, embeddings)

        # Save config
        with open(self.config_file, 'w') as f:
            json.dump({
                'model_name': model_name,
                'embedding_dim': extractor.embedding_dim,
                'device': extractor.device,
                'num_crops': len(embeddings)
            }, f, indent=2)

        print(f"✓ Saved embeddings: {embeddings.shape}")
        print(f"   File: {self.embeddings_file}")

    def load_embeddings(self) -> Tuple[np.ndarray, Dict]:
        """Load embeddings and metadata"""
        if not self.embeddings_file.exists():
            raise FileNotFoundError(
                f"Embeddings not found. Run generate_embeddings() first."
            )

        embeddings = np.load(self.embeddings_file)

        with open(self.metadata_file, 'r') as f:
            metadata = json.load(f)

        with open(self.config_file, 'r') as f:
            config = json.load(f)

        return embeddings, metadata, config

    def _find_image_file(self, images_dir: Path, image_name: str):
        """Find image file with various extensions"""
        for ext in ['.jpg', '.jpeg', '.png', '.JPG', '.JPEG', '.PNG']:
            image_file = images_dir / f"{image_name}{ext}"
            if image_file.exists():
                return image_file
        return None


# Convenience functions for easy use

def extract_crops_and_embeddings(dataset_dir: str, output_dir: str,
                                model_name: str = 'siglip',
                                resize: int = None):
    """
    One-stop function: extract crops and generate embeddings.

    Args:
        dataset_dir: YOLO dataset path
        output_dir: Where to save crops and embeddings
        model_name: Embedding model to use (default: siglip for speed/accuracy balance)
        resize: Resize crops to this size (None to preserve original - recommended)
    """
    manager = BirdCropManager(output_dir)

    # Extract crops
    manager.extract_and_save_crops(dataset_dir, resize=resize)

    # Generate embeddings
    manager.generate_embeddings(model_name=model_name)

    print("\n✅ Complete!")
    print(f"Crops: {manager.images_dir}")
    print(f"Embeddings: {manager.embeddings_file}")
