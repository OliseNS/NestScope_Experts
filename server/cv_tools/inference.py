"""
Computer Vision Inference Module for Bird Detection
Uses ONNX Runtime with SAHI for smart sliced inference
"""

import onnxruntime as ort
import cv2
import os
from pathlib import Path
import numpy as np
from typing import List, Tuple
import time
import yaml
from sahi import AutoDetectionModel
from sahi.predict import get_sliced_prediction
from sahi.utils.cv import read_image_as_pil

# Import species classifier mapping (25 species, grouped for visualization)
from server.cv_tools.classifier_species import (
    CLASSIFIER_SPECIES,
    SPECIES_COMMON_NAMES,
    SPECIES_TO_GROUP,
    GROUP_COLORS,
    get_species_code,
    get_species_name,
    get_species_group,
    get_group_color,
)


# Load model paths from config.yaml
def _load_model_paths():
    """Load model paths and classifier threshold from server configuration"""
    config_path = Path(__file__).parent.parent / "config.yaml"
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)

        model_fast = config['cv']['model_fast']
        model_pro = config['cv']['model_pro']

        # Classifier paths — fix .pt → .onnx if needed
        classifier_swift = config['cv'].get('classifier_swift', 'models/classifier_swift.onnx')
        classifier_apex  = config['cv'].get('classifier_apex',  'models/classifier_apex.onnx')
        classifier_swift = str(classifier_swift).replace('.pt', '.onnx')
        classifier_apex  = str(classifier_apex).replace('.pt', '.onnx')

        # Classifier confidence threshold
        classifier_threshold = config['cv'].get('classifier_confidence_threshold', 0.30)

        # Convert relative paths to absolute (relative to project root)
        project_root = Path(__file__).parent.parent.parent

        if not os.path.isabs(model_fast):
            model_fast = str(project_root / model_fast)
        if not os.path.isabs(model_pro):
            model_pro = str(project_root / model_pro)
        if not os.path.isabs(classifier_swift):
            classifier_swift = str(project_root / classifier_swift)
        if not os.path.isabs(classifier_apex):
            classifier_apex = str(project_root / classifier_apex)

        return model_fast, model_pro, classifier_swift, classifier_apex, classifier_threshold
    except Exception as e:
        print(f"Warning: Could not load model paths from config: {e}")
        # Fallback to default models
        models_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "models")
        return (
            os.path.join(models_dir, "swift.onnx"),
            os.path.join(models_dir, "apex.onnx"),
            os.path.join(models_dir, "classifier_swift.onnx"),
            os.path.join(models_dir, "classifier_apex.onnx"),
            0.30,  # Default threshold
        )

MODEL_FAST, MODEL_PRO, CLASSIFIER_SWIFT, CLASSIFIER_APEX, CLASSIFIER_THRESHOLD = _load_model_paths()
print(f"✓ CV Models configured:")
print(f"  Fast mode: {MODEL_FAST}")
print(f"  Pro mode: {MODEL_PRO}")
print(f"  Classifier (Swift): {CLASSIFIER_SWIFT}")
print(f"  Classifier (Apex): {CLASSIFIER_APEX}")
print(f"  Classification threshold: {CLASSIFIER_THRESHOLD:.0%}")

class BirdDetector:
    """YOLO-based bird detection and counting with dynamic model loading"""

    def __init__(self, model_fast=MODEL_FAST, model_pro=MODEL_PRO, imgsz=1024,
                 classifier_swift=CLASSIFIER_SWIFT, classifier_apex=CLASSIFIER_APEX,
                 classifier_threshold=CLASSIFIER_THRESHOLD):
        """
        Initialize the bird detector with support for multiple models

        Args:
            model_fast: Path to the fast YOLO model (nano)
            model_pro: Path to the pro YOLO model (small)
            imgsz: Image size for inference (default: 1024)
            classifier_swift: Path to the fast species classifier ONNX
            classifier_apex: Path to the accurate species classifier ONNX
            classifier_threshold: Minimum confidence for species classification (default: 0.30)
        """
        self.model_fast_path = model_fast
        self.model_pro_path = model_pro
        self.imgsz = imgsz
        self.current_model_path = None
        self.model = None
        # Classifier state (lazy-loaded on first use)
        self.classifier_swift_path = classifier_swift
        self.classifier_threshold = classifier_threshold
        self.classifier_apex_path = classifier_apex
        self.classifier_session = None
        self.classifier_path_loaded = None
        # Start with fast model loaded by default
        self._load_model(self.model_fast_path)

    def _load_model(self, model_path):
        """
        Load the ONNX model and detect its output format

        Args:
            model_path: Path to the ONNX model file
        """
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model not found at {model_path}")

        # Skip reloading if this model is already loaded
        if self.current_model_path == model_path and self.model is not None:
            return

        self.current_model_path = model_path

        try:
            # Configure ONNX Runtime session options for better performance
            sess_options = ort.SessionOptions()
            sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL

            # Use available providers (CUDA if available, otherwise CPU)
            providers = ['CUDAExecutionProvider', 'CPUExecutionProvider']

            self.model = ort.InferenceSession(
                model_path,
                sess_options=sess_options,
                providers=providers
            )

            # Get model input details
            self.input_name = self.model.get_inputs()[0].name
            self.output_names = [output.name for output in self.model.get_outputs()]

            # Detect output format by checking shape
            output_shape = self.model.get_outputs()[0].shape
            if len(output_shape) == 3 and output_shape[2] == 6:
                self.output_format = 'max_det'  # Format: [batch, num_detections, 6]

                # Detect coordinate format (xyxy vs xywh) using test inference
                self.coord_format = self._detect_coordinate_format()
                print(f"✓ Detected YOLOv8/v11 max_det format: {output_shape}")
                print(f"✓ Coordinate format: {self.coord_format}")
            else:
                self.output_format = 'standard'  # Format: [batch, classes, anchors]
                self.coord_format = 'xywh'  # Standard format always uses xywh
                print(f"✓ Detected standard YOLO format: {output_shape}")

            print(f"✓ ONNX model loaded successfully from {model_path}")
            print(f"  Using provider: {self.model.get_providers()[0]}")
        except Exception as e:
            raise RuntimeError(f"Failed to load ONNX model: {str(e)}")

    def _detect_coordinate_format(self) -> str:
        """
        Detect if model outputs xyxy or xywh coordinates using test inference

        YOLO11n exports to ONNX with xyxy format: [x1, y1, x2, y2, conf, class]
        YOLOv8 exports to ONNX with xywh format: [x_center, y_center, width, height, conf, class]

        Returns:
            'xyxy' or 'xywh'
        """
        try:
            # Run test inference with dummy input
            dummy_input = np.random.rand(1, 3, self.imgsz, self.imgsz).astype(np.float32)
            output = self.model.run(self.output_names, {self.input_name: dummy_input})

            # Get first few detections to analyze
            detections = output[0][0][:10]  # First 10 detections

            # For each detection, check if coordinates make sense as xyxy
            xyxy_score = 0
            xywh_score = 0

            for det in detections:
                c1, c2, c3, c4 = det[:4]

                # Test 1: In xyxy format, x2 > x1 and y2 > y1
                if c3 > c1 and c4 > c2:
                    xyxy_score += 1

                    # Additional check: box size should be reasonable (not entire image)
                    width = c3 - c1
                    height = c4 - c2
                    if 0 < width < self.imgsz * 0.8 and 0 < height < self.imgsz * 0.8:
                        xyxy_score += 1

                # Test 2: In xywh format, center coords should be < image size, w/h reasonable
                if 0 <= c1 <= self.imgsz and 0 <= c2 <= self.imgsz:
                    if 0 < c3 < self.imgsz and 0 < c4 < self.imgsz:
                        xywh_score += 1

            # Decide based on scores
            if xyxy_score > xywh_score:
                return 'xyxy'
            else:
                return 'xywh'

        except Exception as e:
            print(f"Warning: Could not detect coordinate format: {e}")
            print("Defaulting to xywh format")
            return 'xywh'

    def _preprocess_image(self, image: np.ndarray) -> Tuple[np.ndarray, float, Tuple[int, int]]:
        """
        Preprocess image for ONNX inference

        Args:
            image: Input image (BGR format)

        Returns:
            Tuple of (preprocessed_image, scale, (pad_w, pad_h))
        """
        # Get original dimensions
        original_height, original_width = image.shape[:2]

        # Calculate scaling factor to fit within imgsz while maintaining aspect ratio
        scale = min(self.imgsz / original_width, self.imgsz / original_height)
        new_width = int(original_width * scale)
        new_height = int(original_height * scale)

        # Resize image
        resized = cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_LINEAR)

        # Create padded image
        pad_w = (self.imgsz - new_width) // 2
        pad_h = (self.imgsz - new_height) // 2

        padded = np.full((self.imgsz, self.imgsz, 3), 114, dtype=np.uint8)
        padded[pad_h:pad_h + new_height, pad_w:pad_w + new_width] = resized

        # Convert to RGB and normalize
        image_rgb = cv2.cvtColor(padded, cv2.COLOR_BGR2RGB)
        image_norm = image_rgb.astype(np.float32) / 255.0

        # Transpose to CHW format and add batch dimension
        image_chw = np.transpose(image_norm, (2, 0, 1))
        image_batch = np.expand_dims(image_chw, axis=0).astype(np.float32)

        return image_batch, scale, (pad_w, pad_h)

    def _postprocess_max_det_format(self, output: np.ndarray, scale: float, pad: Tuple[int, int],
                                      conf_threshold: float = 0.25) -> List[dict]:
        """
        Postprocess YOLOv8/v11 max_det format output: [1, num_detections, 6]

        This format is already filtered to max detections (e.g., 300) by the model.
        Coordinate format depends on model version:
        - YOLOv8: [x_center, y_center, width, height, confidence, class_id]
        - YOLO11n: [x1, y1, x2, y2, confidence, class_id]

        Args:
            output: Raw ONNX model output [1, num_detections, 6]
            scale: Scale factor used during preprocessing
            pad: Padding (pad_w, pad_h) used during preprocessing
            conf_threshold: Confidence threshold for detections

        Returns:
            List of detection dictionaries
        """
        # Route to appropriate handler based on coordinate format
        if self.coord_format == 'xyxy':
            return self._postprocess_max_det_xyxy(output, scale, pad, conf_threshold)
        else:
            return self._postprocess_max_det_xywh(output, scale, pad, conf_threshold)

    def _postprocess_max_det_xyxy(self, output: np.ndarray, scale: float, pad: Tuple[int, int],
                                    conf_threshold: float = 0.25) -> List[dict]:
        """
        Postprocess max_det format with xyxy coordinates (YOLO11n format)
        Format: [x1, y1, x2, y2, confidence, class_id]

        Coordinates are already in corner format - no conversion needed!
        """
        pad_w, pad_h = pad

        detections_raw = output[0]  # Remove batch dimension -> [num_detections, 6]

        # Extract components - coordinates already in xyxy format!
        boxes_xyxy = detections_raw[:, :4]  # x1, y1, x2, y2
        confidences = detections_raw[:, 4]   # confidence scores
        class_ids = detections_raw[:, 5].astype(int)  # class IDs

        # Filter by confidence threshold
        mask = confidences >= conf_threshold
        boxes_xyxy = boxes_xyxy[mask]
        confidences = confidences[mask]
        class_ids = class_ids[mask]

        if len(boxes_xyxy) == 0:
            return []

        # Adjust coordinates back to original image space (removing padding and scaling)
        boxes_xyxy[:, [0, 2]] = (boxes_xyxy[:, [0, 2]] - pad_w) / scale
        boxes_xyxy[:, [1, 3]] = (boxes_xyxy[:, [1, 3]] - pad_h) / scale

        # Apply NMS to remove duplicate detections
        indices = self._nms_boxes(boxes_xyxy, confidences, iou_threshold=0.45)

        # Create detection dictionaries
        detections = []
        for idx in indices:
            detections.append({
                'bbox': boxes_xyxy[idx].tolist(),
                'confidence': float(confidences[idx]),
                'class_id': int(class_ids[idx])
            })

        return detections

    def _postprocess_max_det_xywh(self, output: np.ndarray, scale: float, pad: Tuple[int, int],
                                    conf_threshold: float = 0.25) -> List[dict]:
        """
        Postprocess max_det format with xywh coordinates (YOLOv8 format)
        Format: [x_center, y_center, width, height, confidence, class_id]

        Need to convert from center format to corner format.
        """
        pad_w, pad_h = pad

        detections_raw = output[0]  # Remove batch dimension -> [num_detections, 6]

        # Extract components
        boxes_xywh = detections_raw[:, :4]  # x_center, y_center, width, height
        confidences = detections_raw[:, 4]   # confidence scores
        class_ids = detections_raw[:, 5].astype(int)  # class IDs

        # Filter by confidence threshold
        mask = confidences >= conf_threshold
        boxes_xywh = boxes_xywh[mask]
        confidences = confidences[mask]
        class_ids = class_ids[mask]

        if len(boxes_xywh) == 0:
            return []

        # Convert from xywh (center format) to xyxy (corner format)
        boxes_xyxy = np.zeros_like(boxes_xywh)
        boxes_xyxy[:, 0] = boxes_xywh[:, 0] - boxes_xywh[:, 2] / 2  # x1 = x_center - width/2
        boxes_xyxy[:, 1] = boxes_xywh[:, 1] - boxes_xywh[:, 3] / 2  # y1 = y_center - height/2
        boxes_xyxy[:, 2] = boxes_xywh[:, 0] + boxes_xywh[:, 2] / 2  # x2 = x_center + width/2
        boxes_xyxy[:, 3] = boxes_xywh[:, 1] + boxes_xywh[:, 3] / 2  # y2 = y_center + height/2

        # Adjust coordinates back to original image space
        boxes_xyxy[:, [0, 2]] = (boxes_xyxy[:, [0, 2]] - pad_w) / scale
        boxes_xyxy[:, [1, 3]] = (boxes_xyxy[:, [1, 3]] - pad_h) / scale

        # Apply NMS to remove duplicate detections
        indices = self._nms_boxes(boxes_xyxy, confidences, iou_threshold=0.45)

        # Create detection dictionaries
        detections = []
        for idx in indices:
            detections.append({
                'bbox': boxes_xyxy[idx].tolist(),
                'confidence': float(confidences[idx]),
                'class_id': int(class_ids[idx])
            })

        return detections

    def _postprocess(self, output: np.ndarray, scale: float, pad: Tuple[int, int],
                     conf_threshold: float = 0.25) -> List[dict]:
        """
        Route to the correct postprocessing function based on model output format

        Args:
            output: Raw ONNX model output
            scale: Scale factor used during preprocessing
            pad: Padding (pad_w, pad_h) used during preprocessing
            conf_threshold: Confidence threshold for detections

        Returns:
            List of detection dictionaries
        """
        if self.output_format == 'max_det':
            return self._postprocess_max_det_format(output, scale, pad, conf_threshold)
        else:
            return self._postprocess_standard_format(output, scale, pad, conf_threshold)

    def _postprocess_standard_format(self, output: np.ndarray, scale: float, pad: Tuple[int, int],
                                      conf_threshold: float = 0.25) -> List[dict]:
        """
        Postprocess ONNX model output (standard format) to extract detections
        Standard format: [1, num_classes, num_boxes]

        Args:
            output: Raw ONNX model output [1, num_classes, num_boxes]
            scale: Scale factor used during preprocessing
            pad: Padding (pad_w, pad_h) used during preprocessing
            conf_threshold: Confidence threshold for detections

        Returns:
            List of detection dictionaries
        """
        pad_w, pad_h = pad

        # Output format: [1, num_classes, num_detections]
        # Transpose to [num_detections, num_classes]
        predictions = output[0].T

        # Extract boxes and scores
        # Format: [x_center, y_center, width, height, ...class_scores]
        boxes_xywh = predictions[:, :4]
        scores = predictions[:, 4:].max(axis=1)
        class_ids = predictions[:, 4:].argmax(axis=1)

        # Filter by confidence threshold
        mask = scores >= conf_threshold
        boxes_xywh = boxes_xywh[mask]
        scores = scores[mask]
        class_ids = class_ids[mask]

        if len(boxes_xywh) == 0:
            return []

        # Convert from xywh to xyxy format
        boxes_xyxy = np.zeros_like(boxes_xywh)
        boxes_xyxy[:, 0] = boxes_xywh[:, 0] - boxes_xywh[:, 2] / 2  # x1
        boxes_xyxy[:, 1] = boxes_xywh[:, 1] - boxes_xywh[:, 3] / 2  # y1
        boxes_xyxy[:, 2] = boxes_xywh[:, 0] + boxes_xywh[:, 2] / 2  # x2
        boxes_xyxy[:, 3] = boxes_xywh[:, 1] + boxes_xywh[:, 3] / 2  # y2

        # Adjust coordinates back to original image space
        boxes_xyxy[:, [0, 2]] = (boxes_xyxy[:, [0, 2]] - pad_w) / scale
        boxes_xyxy[:, [1, 3]] = (boxes_xyxy[:, [1, 3]] - pad_h) / scale

        # Apply NMS
        indices = self._nms_boxes(boxes_xyxy, scores, iou_threshold=0.45)

        # Create detection dictionaries
        detections = []
        for idx in indices:
            detections.append({
                'bbox': boxes_xyxy[idx].tolist(),
                'confidence': float(scores[idx]),
                'class_id': int(class_ids[idx])
            })

        return detections

    def _nms_boxes(self, boxes: np.ndarray, scores: np.ndarray, iou_threshold: float = 0.45) -> List[int]:
        """
        Apply Non-Maximum Suppression to bounding boxes

        Args:
            boxes: Array of boxes in xyxy format [N, 4]
            scores: Array of confidence scores [N]
            iou_threshold: IoU threshold for NMS

        Returns:
            List of indices to keep
        """
        x1 = boxes[:, 0]
        y1 = boxes[:, 1]
        x2 = boxes[:, 2]
        y2 = boxes[:, 3]

        areas = (x2 - x1) * (y2 - y1)
        order = scores.argsort()[::-1]

        keep = []
        while order.size > 0:
            i = order[0]
            keep.append(i)

            xx1 = np.maximum(x1[i], x1[order[1:]])
            yy1 = np.maximum(y1[i], y1[order[1:]])
            xx2 = np.minimum(x2[i], x2[order[1:]])
            yy2 = np.minimum(y2[i], y2[order[1:]])

            w = np.maximum(0.0, xx2 - xx1)
            h = np.maximum(0.0, yy2 - yy1)
            inter = w * h

            iou = inter / (areas[i] + areas[order[1:]] - inter)

            inds = np.where(iou <= iou_threshold)[0]
            order = order[inds + 1]

        return keep

    def _generate_sliding_windows(self, image_shape: Tuple[int, int], window_size: int = 1024, overlap: int = 128) -> List[Tuple[int, int, int, int]]:
        """
        Generate sliding window coordinates for an image

        Args:
            image_shape: (height, width) of the image
            window_size: Size of the sliding window (default: 1024)
            overlap: Overlap between windows in pixels (default: 128)

        Returns:
            List of (x1, y1, x2, y2) coordinates for each window
        """
        height, width = image_shape
        stride = window_size - overlap
        windows = []

        y = 0
        while y < height:
            x = 0
            while x < width:
                x2 = min(x + window_size, width)
                y2 = min(y + window_size, height)
                x1 = x2 - window_size if x2 == width and width - x < window_size else x
                y1 = y2 - window_size if y2 == height and height - y < window_size else y

                windows.append((max(0, x1), max(0, y1), x2, y2))

                if x2 >= width:
                    break
                x += stride

            if y2 >= height:
                break
            y += stride

        return windows

    def _non_max_suppression_custom(self, detections: List[dict], iou_threshold: float = 0.5) -> List[dict]:
        """
        Apply Non-Maximum Suppression to remove duplicate detections from overlapping windows

        Args:
            detections: List of detection dictionaries
            iou_threshold: IoU threshold for suppression (default: 0.5)

        Returns:
            Filtered list of detections
        """
        if len(detections) == 0:
            return []

        # Sort by confidence
        detections = sorted(detections, key=lambda x: x['confidence'], reverse=True)

        keep = []
        while len(detections) > 0:
            current = detections.pop(0)
            keep.append(current)

            # Remove detections with high IoU
            remaining = []
            for det in detections:
                if self._calculate_iou(current['bbox'], det['bbox']) < iou_threshold:
                    remaining.append(det)
            detections = remaining

        return keep

    def _calculate_iou(self, box1: List[float], box2: List[float]) -> float:
        """
        Calculate Intersection over Union (IoU) between two bounding boxes

        Args:
            box1: [x1, y1, x2, y2]
            box2: [x1, y1, x2, y2]

        Returns:
            IoU value
        """
        x1_inter = max(box1[0], box2[0])
        y1_inter = max(box1[1], box2[1])
        x2_inter = min(box1[2], box2[2])
        y2_inter = min(box1[3], box2[3])

        if x2_inter < x1_inter or y2_inter < y1_inter:
            return 0.0

        intersection = (x2_inter - x1_inter) * (y2_inter - y1_inter)
        area1 = (box1[2] - box1[0]) * (box1[3] - box1[1])
        area2 = (box2[2] - box2[0]) * (box2[3] - box2[1])
        union = area1 + area2 - intersection

        return intersection / union if union > 0 else 0.0

    def _downsample_and_predict(self, image: np.ndarray, conf_threshold: float = 0.25) -> List[dict]:
        """
        Downsample a large image to fit model input size and run inference (much faster than sliding window)

        Args:
            image: Input image as numpy array
            conf_threshold: Confidence threshold for detections

        Returns:
            List of detection dictionaries with coordinates scaled back to original image size
        """
        height, width = image.shape[:2]

        # Calculate scale to fit within model input size
        scale = min(self.imgsz / width, self.imgsz / height)
        new_width = int(width * scale)
        new_height = int(height * scale)

        print(f"[Downsample Mode] Resizing {width}x{height} → {new_width}x{new_height} for fast single-pass inference...")

        # Resize image
        resized_img = cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_LINEAR)

        # Preprocess
        preprocessed, preprocess_scale, pad = self._preprocess_image(resized_img)

        # Run ONNX inference
        output = self.model.run(self.output_names, {self.input_name: preprocessed})

        # Postprocess output
        detections = self._postprocess(output[0], preprocess_scale, pad, conf_threshold)

        # Scale coordinates back to original image size
        for det in detections:
            det['bbox'][0] /= scale  # x1
            det['bbox'][1] /= scale  # y1
            det['bbox'][2] /= scale  # x2
            det['bbox'][3] /= scale  # y2

        return detections

    def _predict_with_sahi(self, image_path: str, conf_threshold: float = 0.25, verbose: bool = True) -> List[dict]:
        """
        Use SAHI (Slicing Aided Hyper Inference) for smart sliced prediction

        Args:
            image_path: Path to the input image
            conf_threshold: Confidence threshold for detections
            verbose: Whether to print progress messages (default: True)

        Returns:
            List of detection dictionaries
        """
        try:
            # SAHI uses YOLOv5/v8 format, but we need to use ONNX
            # We'll use SAHI's slicing logic but run our own ONNX inference
            from sahi.slicing import slice_image
            import tempfile

            if verbose:
                print(f"[SAHI Mode] Using intelligent slicing for accurate detection...")

            # Read image
            image = cv2.imread(image_path)
            height, width = image.shape[:2]

            # SAHI parameters
            slice_height = self.imgsz
            slice_width = self.imgsz
            overlap_height_ratio = 0.2  # 20% overlap for good coverage
            overlap_width_ratio = 0.2

            # Calculate overlap in pixels
            overlap_height = int(slice_height * overlap_height_ratio)
            overlap_width = int(slice_width * overlap_width_ratio)

            if verbose:
                print(f"  Slice size: {slice_width}x{slice_height}")
                print(f"  Overlap: {overlap_width}x{overlap_height} pixels ({overlap_width_ratio*100:.0f}%)")

            # Generate slices
            slice_image_result = slice_image(
                image=image_path,
                output_file_name=None,
                output_dir=None,
                slice_height=slice_height,
                slice_width=slice_width,
                overlap_height_ratio=overlap_height_ratio,
                overlap_width_ratio=overlap_width_ratio,
                min_area_ratio=0.1,
                verbose=False
            )

            all_detections = []
            num_slices = len(slice_image_result.images)
            if verbose:
                print(f"  Processing {num_slices} slices...")

            # Process each slice
            for idx, (slice_img, slice_coords) in enumerate(zip(slice_image_result.images, slice_image_result.starting_pixels), 1):
                # Show progress
                if verbose and (idx % 10 == 0 or idx == num_slices):
                    print(f"  Processing slice {idx}/{num_slices}...")

                # Convert PIL to numpy array for ONNX
                slice_np = np.array(slice_img)
                slice_np = cv2.cvtColor(slice_np, cv2.COLOR_RGB2BGR)

                # Preprocess
                preprocessed, scale, pad = self._preprocess_image(slice_np)

                # Run ONNX inference
                output = self.model.run(self.output_names, {self.input_name: preprocessed})

                # Postprocess
                slice_detections = self._postprocess(output[0], scale, pad, conf_threshold)

                # Adjust coordinates to original image space
                x_offset, y_offset = slice_coords
                for det in slice_detections:
                    det['bbox'][0] += x_offset  # x1
                    det['bbox'][1] += y_offset  # y1
                    det['bbox'][2] += x_offset  # x2
                    det['bbox'][3] += y_offset  # y2
                    all_detections.append(det)

            if verbose:
                print(f"  Found {len(all_detections)} raw detections, applying NMS...")

            # Apply NMS to merge overlapping detections
            filtered_detections = self._non_max_suppression_custom(all_detections, iou_threshold=0.5)

            if verbose:
                print(f"  Final count after NMS: {len(filtered_detections)} birds")

            return filtered_detections

        except Exception as e:
            if verbose:
                print(f"SAHI prediction failed: {str(e)}, falling back to standard inference")
            # Fallback to standard inference
            preprocessed, scale, pad = self._preprocess_image(cv2.imread(image_path))
            output = self.model.run(self.output_names, {self.input_name: preprocessed})
            return self._postprocess(output[0], scale, pad, conf_threshold)

    def _load_classifier(self, fast_mode: bool):
        """Lazy-load the species classifier ONNX session."""
        path = self.classifier_swift_path if fast_mode else self.classifier_apex_path
        if self.classifier_path_loaded == path and self.classifier_session is not None:
            return
        if not os.path.exists(path):
            self.classifier_session = None
            return
        try:
            self.classifier_session = ort.InferenceSession(
                path, providers=['CUDAExecutionProvider', 'CPUExecutionProvider']
            )
            self.classifier_path_loaded = path
            print(f"✓ Species classifier loaded: {Path(path).name}")
        except Exception as e:
            print(f"Warning: Could not load classifier {path}: {e}")
            self.classifier_session = None

    def classify_crop(self, crop_bgr: np.ndarray, fast_mode: bool = True, top_k: int = 1) -> dict:
        """
        Classify a bird crop into one of 25 species.

        Args:
            crop_bgr: Bird crop in BGR format (any size)
            fast_mode: Use Swift classifier (True) or Apex (False)
            top_k: Number of top predictions to return (default: 1, max: 5)

        Returns:
            Dict with:
                - species_code: 4-letter code (e.g., 'BRPE')
                - species_name: Common name (e.g., 'Brown Pelican')
                - confidence: Float probability (0-1)
                - group: Functional group (e.g., 'PELICAN') for color-coding
                - top_predictions: List of top-k predictions if top_k > 1
        """
        self._load_classifier(fast_mode)
        if self.classifier_session is None:
            return {
                'species_code': 'UNKNOWN',
                'species_name': 'Unknown',
                'confidence': 0.0,
                'group': 'UNKNOWN',
                'top_predictions': []
            }

        try:
            # Resize to 224x224, BGR→RGB, normalize [0,1], NCHW float32
            img = cv2.resize(crop_bgr, (224, 224), interpolation=cv2.INTER_LINEAR)
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            img = img.astype(np.float32) / 255.0
            img = np.transpose(img, (2, 0, 1))[np.newaxis]  # (1, 3, 224, 224)

            input_name = self.classifier_session.get_inputs()[0].name
            output = self.classifier_session.run(None, {input_name: img})[0][0]

            # Softmax to get probabilities
            exp_out = np.exp(output - output.max())
            probs = exp_out / exp_out.sum()

            # DEBUG: Print classifier stats (first few predictions only to avoid spam)
            if not hasattr(self, '_debug_count'):
                self._debug_count = 0
            if self._debug_count < 3:
                print(f"\n[CLASSIFIER DEBUG #{self._debug_count + 1}]")
                print(f"  Crop size: {crop_bgr.shape}")
                print(f"  Raw logits (top 5): {output[np.argsort(output)[::-1][:5]]}")
                print(f"  Probabilities (top 5): {probs[np.argsort(probs)[::-1][:5]]}")
                print(f"  Top prediction: {get_species_code(int(np.argmax(probs)))} ({probs.max():.2%})")
                self._debug_count += 1

            # Get top-k predictions
            top_k = min(max(1, top_k), 5)  # Clamp to [1, 5]
            top_indices = np.argsort(probs)[::-1][:top_k]

            top_predictions = []
            for idx in top_indices:
                species_code = get_species_code(int(idx))
                species_name = get_species_name(species_code)
                group = get_species_group(species_code)
                confidence = float(probs[idx])

                top_predictions.append({
                    'species_code': species_code,
                    'species_name': species_name,
                    'confidence': round(confidence, 3),
                    'group': group
                })

            # Apply confidence threshold - if top prediction is below threshold, return UNKNOWN
            top_pred = top_predictions[0]
            if top_pred['confidence'] < self.classifier_threshold:
                return {
                    'species_code': 'UNKNOWN',
                    'species_name': 'Unknown',
                    'confidence': top_pred['confidence'],
                    'group': 'UNKNOWN',
                    'top_predictions': top_predictions  # Still include all predictions for reference
                }

            # Return top prediction as main result + top-k list
            top_result = {
                'species_code': top_pred['species_code'],
                'species_name': top_pred['species_name'],
                'confidence': top_pred['confidence'],
                'group': top_pred['group'],
                'top_predictions': top_predictions
            }

            return top_result

        except Exception as e:
            print(f"Classification error: {e}")
            return {
                'species_code': 'UNKNOWN',
                'species_name': 'Unknown',
                'confidence': 0.0,
                'group': 'UNKNOWN',
                'top_predictions': []
            }

    def _classify_detections(self, image_bgr: np.ndarray, detections: List[dict], fast_mode: bool = True) -> List[dict]:
        """
        Run species classifier on each detected bird crop and add species info.

        Args:
            image_bgr: Full original image in BGR format
            detections: List of detection dicts with 'bbox' key
            fast_mode: Use Swift (True) or Apex (False) classifier

        Returns:
            Same detections list with species info added:
                - species_code: 4-letter code (e.g., 'BRPE')
                - species_name: Common name (e.g., 'Brown Pelican')
                - species_group: Functional group (e.g., 'PELICAN')
                - species_confidence: Classification confidence (0-1)
        """
        h, w = image_bgr.shape[:2]
        for det in detections:
            x1, y1, x2, y2 = [int(v) for v in det['bbox']]
            # Clamp to image bounds
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(w, x2), min(h, y2)
            crop = image_bgr[y1:y2, x1:x2]

            if crop.size > 0 and (x2 - x1) >= 5 and (y2 - y1) >= 5:
                result = self.classify_crop(crop, fast_mode, top_k=1)
                det['species_code'] = result['species_code']
                det['species_name'] = result['species_name']
                det['species_group'] = result['group']
                det['species_confidence'] = result['confidence']
            else:
                det['species_code'] = 'UNKNOWN'
                det['species_name'] = 'Unknown'
                det['species_group'] = 'UNKNOWN'
                det['species_confidence'] = 0.0

        return detections

    def _draw_custom_annotations_from_detections(self, image, detections: List[dict]):
        """
        Draw custom annotations on image from detection dictionaries

        Args:
            image: Original image array
            detections: List of detection dictionaries with 'bbox' key

        Returns:
            Annotated image with custom styling
        """
        annotated_img = image.copy()
        thickness = 3

        for det in detections:
            x1, y1, x2, y2 = det['bbox']
            x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)

            # Use species group color (for visual distinction)
            group = det.get('species_group', 'UNKNOWN')
            box_color = get_group_color(group)

            cv2.rectangle(annotated_img, (x1, y1), (x2, y2), box_color, thickness)

            # Draw species code label above box (only if classification ran)
            species_code = det.get('species_code', '')
            if species_code and species_code != 'UNKNOWN':
                label = species_code  # Show 4-letter code (e.g., 'BRPE')
                font_scale = 0.5
                font_thickness = 2
                (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, font_scale, font_thickness)
                label_y = max(y1 - 4, th + 4)
                # Draw label background (same color as box)
                cv2.rectangle(annotated_img, (x1, label_y - th - 6), (x1 + tw + 6, label_y), box_color, -1)
                # Draw label text in white
                cv2.putText(annotated_img, label, (x1 + 3, label_y - 3),
                            cv2.FONT_HERSHEY_SIMPLEX, font_scale, (255, 255, 255), font_thickness, cv2.LINE_AA)

        return annotated_img

    def predict(self, image_path, conf_threshold=0.25, use_sliding_window=True, fast_mode=True, verbose=True):
        """
        Run inference on an image with SAHI and model selection

        Args:
            image_path: Path to the input image
            conf_threshold: Confidence threshold for detections (default: 0.25)
            use_sliding_window: Whether to use smart slicing for large images (default: True)
            fast_mode: Model selection mode (default: True)
                - True (Fast): Swift model - optimized for speed, good for quick previews
                - False (Max): Apex model - optimized for accuracy, better for final results
                Both modes use SAHI (Slicing Aided Hyper Inference) for large images
            verbose: Whether to print progress messages (default: True)

        Returns:
            dict: Results containing:
                - bird_count: Number of birds detected
                - detections: List of detection info (bbox, confidence)
                - annotated_image: Image with bounding boxes drawn
                - inference_time: Time taken for inference in seconds
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image not found at {image_path}")

        # Load the appropriate model based on mode
        target_model = self.model_fast_path if fast_mode else self.model_pro_path
        mode_name = "Swift" if fast_mode else "Apex"
        self._load_model(target_model)

        # Start timing
        start_time = time.perf_counter()

        # Read original image
        original_img = cv2.imread(image_path)
        height, width = original_img.shape[:2]

        # ALWAYS use SAHI for large images, standard inference for small images
        if use_sliding_window and (height > self.imgsz or width > self.imgsz):
            if verbose:
                print(f"[{mode_name} Mode] Processing {width}x{height} image with SAHI slicing...")
            detections = self._predict_with_sahi(image_path, conf_threshold, verbose=verbose)
        else:
            # Small image: use standard inference
            if verbose:
                print(f"[{mode_name} Mode] Processing {width}x{height} image with standard inference...")
            preprocessed, scale, pad = self._preprocess_image(original_img)
            output = self.model.run(self.output_names, {self.input_name: preprocessed})
            detections = self._postprocess(output[0], scale, pad, conf_threshold)

        # Calculate inference time (before drawing annotations)
        inference_time = time.perf_counter() - start_time

        # Classify each detected bird crop into a species group
        detections = self._classify_detections(original_img, detections, fast_mode)

        # Build species summary: {species_code: count}
        species_summary: dict = {}
        for det in detections:
            code = det.get('species_code', 'UNKNOWN')
            species_summary[code] = species_summary.get(code, 0) + 1

        # Draw custom annotations (uses species group colors)
        annotated_img = self._draw_custom_annotations_from_detections(original_img, detections)

        return {
            'bird_count': len(detections),
            'detections': detections,
            'species_summary': species_summary,
            'annotated_image': annotated_img,
            'image_path': image_path,
            'inference_time': inference_time
        }

    def _predict_with_sliding_window(self, image: np.ndarray, conf_threshold: float = 0.45, overlap: int = 64, verbose: bool = True) -> List[dict]:
        """
        Run inference using sliding window approach

        Args:
            image: Input image as numpy array
            conf_threshold: Confidence threshold for detections
            overlap: Overlap between windows in pixels
                - 64: Fast mode (minimal overlap)
                - 128-512: Standard mode (adaptive overlap for ~10 windows, improved accuracy)
            verbose: Whether to print progress messages (default: True)

        Returns:
            List of detection dictionaries
        """
        height, width = image.shape[:2]
        windows = self._generate_sliding_windows((height, width), self.imgsz, overlap=overlap)

        all_detections = []

        mode_name = f"Standard ({overlap}px overlap)" if overlap >= 128 else f"Fast ({overlap}px overlap)"
        if verbose:
            print(f"[Sliding Window Mode] Processing {len(windows)} windows for {width}x{height} image using {mode_name}...")

        for idx, (x1, y1, x2, y2) in enumerate(windows, 1):
            # Show progress every 10 windows
            if verbose and (idx % 10 == 0 or idx == len(windows)):
                print(f"  Processing window {idx}/{len(windows)}...")

            # Extract window
            window = image[y1:y2, x1:x2]

            # Preprocess window for ONNX
            preprocessed, scale, pad = self._preprocess_image(window)

            # Run ONNX inference on window
            output = self.model.run(self.output_names, {self.input_name: preprocessed})

            # Postprocess output
            window_detections = self._postprocess(output[0], scale, pad, conf_threshold)

            # Adjust coordinates back to original image space
            for det in window_detections:
                det['bbox'][0] += x1  # x1
                det['bbox'][1] += y1  # y1
                det['bbox'][2] += x1  # x2
                det['bbox'][3] += y1  # y2
                all_detections.append(det)

        print(f"Found {len(all_detections)} raw detections, applying NMS...")

        # Apply NMS to remove duplicate detections from overlapping windows
        filtered_detections = self._non_max_suppression_custom(all_detections, iou_threshold=0.5)

        print(f"Final count after NMS: {len(filtered_detections)} birds")

        return filtered_detections

    def predict_from_bytes(self, image_bytes, conf_threshold=0.25, use_sliding_window=True, fast_mode=True):
        """
        Run inference on image bytes (from uploaded file) with SAHI and model selection

        Args:
            image_bytes: Image data as bytes
            conf_threshold: Confidence threshold for detections
            use_sliding_window: Whether to use smart slicing for large images (default: True)
            fast_mode: Model selection mode (default: True)
                - True (Fast): Swift model - optimized for speed, good for quick previews
                - False (Max): Apex model - optimized for accuracy, better for final results
                Both modes use SAHI (Slicing Aided Hyper Inference) for large images

        Returns:
            dict: Same as predict()
        """
        # Load the appropriate model based on mode
        target_model = self.model_fast_path if fast_mode else self.model_pro_path
        mode_name = "Swift" if fast_mode else "Apex"
        self._load_model(target_model)

        # Start timing
        start_time = time.perf_counter()

        # Convert bytes to numpy array
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        height, width = img.shape[:2]

        # ALWAYS use SAHI for large images, standard inference for small images
        if use_sliding_window and (height > self.imgsz or width > self.imgsz):
            print(f"[{mode_name} Mode] Processing {width}x{height} image with SAHI slicing...")
            # Save image temporarily for SAHI
            import tempfile
            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp_file:
                tmp_path = tmp_file.name
                cv2.imwrite(tmp_path, img)

            try:
                detections = self._predict_with_sahi(tmp_path, conf_threshold)
            finally:
                # Clean up temp file
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
        else:
            # Small image: use standard inference
            print(f"[{mode_name} Mode] Processing {width}x{height} image with standard inference...")
            preprocessed, scale, pad = self._preprocess_image(img)
            output = self.model.run(self.output_names, {self.input_name: preprocessed})
            detections = self._postprocess(output[0], scale, pad, conf_threshold)

        # Calculate inference time (before drawing annotations)
        inference_time = time.perf_counter() - start_time

        # Classify each detected bird crop into a species group
        detections = self._classify_detections(img, detections, fast_mode)

        # Build species summary: {species_code: count}
        species_summary: dict = {}
        for det in detections:
            code = det.get('species_code', 'UNKNOWN')
            species_summary[code] = species_summary.get(code, 0) + 1

        # Draw custom annotations (uses species group colors)
        annotated_img = self._draw_custom_annotations_from_detections(img, detections)

        return {
            'bird_count': len(detections),
            'detections': detections,
            'species_summary': species_summary,
            'annotated_image': annotated_img,
            'inference_time': inference_time
        }

    def save_annotated_image(self, annotated_img, output_path):
        """
        Save the annotated image to disk

        Args:
            annotated_img: Annotated image array
            output_path: Path to save the image
        """
        cv2.imwrite(output_path, annotated_img)
        return output_path


def get_example_images():
    """
    Get list of example images from cv_tools/images directory

    Returns:
        list: List of image filenames
    """
    images_dir = Path(__file__).parent / "images"
    if not images_dir.exists():
        return []

    image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp'}
    example_images = [
        f.name for f in images_dir.iterdir()
        if f.is_file() and f.suffix.lower() in image_extensions
    ]

    return sorted(example_images)


if __name__ == "__main__":
    # Test the detector
    detector = BirdDetector()
    print("Bird detector initialized successfully!")

    # List example images
    examples = get_example_images()
    print(f"Found {len(examples)} example images: {examples}")
