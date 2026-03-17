"""
ONNX-based bird classifier for Nestperts.

This module provides species classification using the ONNX Runtime.
It replaces the missing server.cv_tools.inference module.
"""

import os
import sys
import numpy as np
import cv2
from typing import List, Dict, Tuple

# Add project root to path for relative imports
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

try:
    import onnxruntime as ort
    HAS_ONNX = True
except ImportError:
    HAS_ONNX = False
    print("⚠️ onnxruntime not installed. Classification will be unavailable.")


class ONNXClassifier:
    """
    ONNX-based bird species classifier.

    Dynamically detects the number of output classes from the model.
    """

    def __init__(self, model_path: str = None, classes_file: str = None):
        """
        Initialize the classifier.

        Args:
            model_path: Path to classifier ONNX model. If None, uses default path.
            classes_file: Path to classes JSON file. If None, uses default.
        """
        if not HAS_ONNX:
            raise ImportError("onnxruntime is required for classification. Install with: pip install onnxruntime")

        # Default model path
        if model_path is None:
            model_path = os.path.join(PROJECT_ROOT, 'models', 'classifier_swift.onnx')

        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Classifier model not found at: {model_path}")

        print(f"Loading classifier from: {model_path}")

        # Initialize ONNX Runtime session
        providers = ['CPUExecutionProvider']

        # Try to use GPU if available
        if 'CUDAExecutionProvider' in ort.get_available_providers():
            providers.insert(0, 'CUDAExecutionProvider')
            print("  Using GPU (CUDA)")
        else:
            print("  Using CPU")

        self.session = ort.InferenceSession(model_path, providers=providers)

        # Get input/output details
        self.input_name = self.session.get_inputs()[0].name
        self.input_shape = self.session.get_inputs()[0].shape
        self.output_name = self.session.get_outputs()[0].name
        self.output_shape = self.session.get_outputs()[0].shape

        # Determine number of classes from model output shape
        self.num_classes = self.output_shape[1] if len(self.output_shape) > 1 else self.output_shape[0]

        # Load class names (codes)
        self.class_names = self._load_class_names(classes_file)
        
        # Load mapping from code to full name from database
        self.species_map = self._load_species_mapping()

        print(f"  Input shape: {self.input_shape}")
        print(f"  Output shape: {self.output_shape}")
        print(f"  Number of classes: {self.num_classes}")
        print(f"  Class names: {len(self.class_names)} loaded")
        print(f"  Species mapping: {len(self.species_map)} names loaded from database")
        print("✓ Classifier loaded successfully")

    def _load_species_mapping(self) -> Dict[str, str]:
        """Load mapping from species code to full name from SQLite database."""
        mapping = {}
        try:
            from labeller.services.species_service import get_species_service
            svc = get_species_service()
            species_list = svc.get_all_species()
            for s in species_list:
                mapping[s['code']] = s['name']
        except Exception as e:
            print(f"  ⚠ Could not load species mapping from database: {e}")
        return mapping

    def _load_class_names(self, classes_file: str = None) -> List[str]:
        """
        Load class names with the following priority:
        1. Model Metadata (names property)
        2. User-specified file (classes_file)
        3. Project root class_names.txt (if matching)
        4. Default species_list.json
        5. Generic fallbacks
        """
        # Priority 1: Metadata from ONNX model (Ultralytics standard)
        try:
            meta = self.session.get_modelmeta().custom_metadata_map
            if 'names' in meta:
                import ast
                # Parse string representation of dict: {0: 'bird', 1: 'nest', ...}
                names_dict = ast.literal_eval(meta['names'])
                if isinstance(names_dict, dict):
                    # Sort by index to ensure order
                    sorted_indices = sorted(names_dict.keys())
                    names = [names_dict[i] for i in sorted_indices]
                    
                    if len(names) == self.num_classes:
                        print(f"  ✓ Found {len(names)} names in model metadata")
                        return names
                    else:
                        print(f"  ⚠ Metadata names ({len(names)}) don't match output shape ({self.num_classes})")
        except Exception as e:
            print(f"  ⚠ Could not parse model metadata: {e}")

        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # Priority 2: User-specified file
        if classes_file and os.path.exists(classes_file):
            return self._read_classes_from_file(classes_file)

        # Priority 3: Check for class_names.txt in project root if it matches num_classes
        root_classes_txt = os.path.join(project_root, 'class_names.txt')
        if os.path.exists(root_classes_txt):
            try:
                with open(root_classes_txt, 'r') as f:
                    lines = [line.strip() for line in f if line.strip()]
                    if len(lines) == self.num_classes:
                        print(f"  ✓ Using {root_classes_txt} (matches {self.num_classes} outputs)")
                        return lines
            except Exception:
                pass

        # Priority 3: Default species_list.json
        if classes_file is None:
            classes_file = os.path.join(project_root, 'labeller', 'data', 'species_list.json')

        if os.path.exists(classes_file):
            return self._read_classes_from_file(classes_file)

        # Fallback to generic class names
        print(f"  ⚠ Warning: No valid class list found for {self.num_classes} classes. Using generic names.")
        return [f"CLASS_{i}" for i in range(self.num_classes)]

    def _read_classes_from_file(self, file_path: str) -> List[str]:
        """Read classes from JSON or TXT file."""
        try:
            if file_path.endswith('.json'):
                import json
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    species = data.get('real_species', [])
                    class_names = [s['code'] for s in species[:self.num_classes]]
                    
                    # Pad with generic names if needed
                    while len(class_names) < self.num_classes:
                        class_names.append(f"CLASS_{len(class_names)}")
                    return class_names[:self.num_classes]
            else:
                # Assume TXT format (one per line)
                with open(file_path, 'r') as f:
                    class_names = [line.strip() for line in f if line.strip()]
                    
                    # Pad or truncate to match model
                    if len(class_names) > self.num_classes:
                        print(f"  ⚠ Warning: {file_path} has {len(class_names)} classes, but model only has {self.num_classes}. Truncating.")
                        return class_names[:self.num_classes]
                    while len(class_names) < self.num_classes:
                        class_names.append(f"CLASS_{len(class_names)}")
                    return class_names
        except Exception as e:
            print(f"  ⚠ Error reading {file_path}: {e}")
            return [f"CLASS_{i}" for i in range(self.num_classes)]

    def preprocess(self, image: np.ndarray) -> np.ndarray:
        """
        Preprocess image for classification.

        Args:
            image: BGR image from cv2.imread (H, W, 3)

        Returns:
            Preprocessed tensor (1, 3, H, W) in float32
        """
        # Determine target size from model input shape
        input_shape = self.session.get_inputs()[0].shape
        if isinstance(input_shape[2], int) and isinstance(input_shape[3], int):
            target_size = (input_shape[3], input_shape[2]) # (width, height)
        else:
            target_size = (224, 224) # Default fallback

        # Resize
        img = cv2.resize(image, target_size, interpolation=cv2.INTER_LINEAR)

        # Convert BGR to RGB
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

        # Normalize to [0, 1]
        img = img.astype(np.float32) / 255.0

        # ImageNet normalization
        mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
        std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
        img = (img - mean) / std

        # Convert to CHW format (channels first)
        img = np.transpose(img, (2, 0, 1))

        # Add batch dimension
        img = np.expand_dims(img, axis=0)

        return img

    def classify_crop(self, crop: np.ndarray, top_k: int = 5) -> Dict:
        """
        Classify a bird bird image.

        Args:
            crop: BGR image crop from cv2 (H, W, 3)
            top_k: Number of top predictions to return

        Returns:
            Dictionary with:
                - top_predictions: List of dicts with code, full_name, confidence
                - all_scores: Dictionary of all class scores (codes)
        """
        # Preprocess
        input_tensor = self.preprocess(crop)

        # Run inference
        outputs = self.session.run([self.output_name], {self.input_name: input_tensor})
        logits = outputs[0][0]  # Shape: (num_classes,)

        # Apply softmax
        exp_logits = np.exp(logits - np.max(logits))
        probabilities = exp_logits / np.sum(exp_logits)

        # Get top-k predictions
        top_k = min(top_k, len(self.class_names))  # Ensure top_k doesn't exceed available classes
        top_indices = np.argsort(probabilities)[::-1][:top_k]
        
        top_predictions = []
        for idx in top_indices:
            code = self.class_names[idx]
            top_predictions.append({
                'code': code,
                'full_name': self.species_map.get(code, code),  # Fallback to code if name not in DB
                'confidence': float(probabilities[idx])
            })

        # All scores
        all_scores = {
            self.class_names[i]: float(probabilities[i])
            for i in range(len(self.class_names))
        }

        return {
            'top_predictions': top_predictions,
            'all_scores': all_scores
        }


class BirdDetector:
    """
    Compatibility wrapper for classification.

    This class provides the same interface as the old server.cv_tools.inference.BirdDetector
    but only supports classification (no detection).
    """

    def __init__(self, model_path: str = None, classes_file: str = None):
        """Initialize the classifier."""
        self.classifier = ONNXClassifier(model_path=model_path, classes_file=classes_file)

    def classify_crop(self, crop: np.ndarray, top_k: int = 5) -> Dict:
        """
        Classify a bird crop.

        Args:
            crop: BGR image crop from cv2
            top_k: Number of top predictions

        Returns:
            Classification results
        """
        return self.classifier.classify_crop(crop, top_k=top_k)


# Singleton instance
_classifier_instance = None


def get_classifier(model_path: str = None) -> ONNXClassifier:
    """Get or create the global classifier instance."""
    global _classifier_instance
    if _classifier_instance is None:
        try:
            _classifier_instance = ONNXClassifier(model_path=model_path)
        except Exception as e:
            print(f"Failed to load classifier: {e}")
            return None
    return _classifier_instance


def get_bird_detector(model_path: str = None, classes_file: str = None) -> BirdDetector:
    """Get or create the global BirdDetector instance (compatibility)."""
    try:
        return BirdDetector(model_path=model_path, classes_file=classes_file)
    except Exception as e:
        print(f"Failed to load BirdDetector: {e}")
        return None
