"""
LuckyCharm Inference Engine - Fast bird detection with SAHI

Optimized for speed demonstration with YOLO v26 End-to-End format support.
"""

import cv2
import numpy as np
import onnxruntime as ort
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import time


class FastBirdDetector:
    """Ultra-fast bird detector with SAHI support"""

    def __init__(self, detector_path: str, classifier_path: str,
                 conf_threshold: float = 0.25, iou_threshold: float = 0.45):
        """
        Initialize detector and classifier.

        Args:
            detector_path: Path to swift_UQ.onnx
            classifier_path: Path to classifier_swift.onnx
            conf_threshold: Confidence threshold for detections
            iou_threshold: IoU threshold for NMS
        """
        self.conf_threshold = conf_threshold
        self.iou_threshold = iou_threshold

        # Initialize ONNX Runtime with optimizations
        sess_options = ort.SessionOptions()
        sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        sess_options.intra_op_num_threads = 4
        sess_options.inter_op_num_threads = 4

        providers = ['CPUExecutionProvider']
        if 'CUDAExecutionProvider' in ort.get_available_providers():
            providers.insert(0, 'CUDAExecutionProvider')

        # Load detector
        print(f"Loading detector: {detector_path}")
        self.detector_session = ort.InferenceSession(
            detector_path,
            providers=providers,
            sess_options=sess_options
        )
        self.detector_input_name = self.detector_session.get_inputs()[0].name
        detector_shape = self.detector_session.get_inputs()[0].shape
        self.detector_size = detector_shape[2] if isinstance(detector_shape[2], int) else 1024

        # Load classifier
        print(f"Loading classifier: {classifier_path}")
        self.classifier_session = ort.InferenceSession(
            classifier_path,
            providers=providers,
            sess_options=sess_options
        )
        self.classifier_input_name = self.classifier_session.get_inputs()[0].name

        # Species group mapping (7 groups from classifier)
        self.species_groups = [
            "COLOR_WADER", "DARK", "GULL", "PELICAN",
            "SHOREBIRD", "TERN", "WHITE_WADER"
        ]

        print(f"✓ Detector loaded (input: {self.detector_size}x{self.detector_size})")
        print(f"✓ Classifier loaded (7 species groups)")
        print(f"✓ Using: {providers[0]}")

    def preprocess_detection(self, image: np.ndarray) -> Tuple[np.ndarray, float]:
        """Preprocess image for YOLO detection"""
        h, w = image.shape[:2]

        # Resize maintaining aspect ratio
        scale = self.detector_size / max(h, w)
        new_w, new_h = int(w * scale), int(h * scale)
        resized = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_LINEAR)

        # Pad to square
        padded = np.ones((self.detector_size, self.detector_size, 3), dtype=np.uint8) * 114
        padded[:new_h, :new_w] = resized

        # Convert BGR to RGB and normalize
        rgb = cv2.cvtColor(padded, cv2.COLOR_BGR2RGB)
        img = rgb.astype(np.float32) / 255.0
        img = np.transpose(img, (2, 0, 1))[np.newaxis, ...]

        return img, scale

    def preprocess_classification(self, crop: np.ndarray) -> np.ndarray:
        """Preprocess crop for species classification"""
        # Resize to 224x224
        img = cv2.resize(crop, (224, 224), interpolation=cv2.INTER_LINEAR)
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

        # Normalize with ImageNet stats
        img = img.astype(np.float32) / 255.0
        mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
        std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
        img = (img - mean) / std

        # CHW format with batch dimension
        img = np.transpose(img, (2, 0, 1))[np.newaxis, ...]
        return img

    def postprocess_detection(self, outputs: np.ndarray, orig_shape: Tuple[int, int],
                             scale: float) -> List[Dict]:
        """Post-process YOLO detections (supports v26 End-to-End format)"""
        output = outputs[0]

        # YOLO26n End-to-End format: (1, 300, 6) -> [x1, y1, x2, y2, conf, class]
        if len(output.shape) == 3 and output.shape[1] <= 300 and output.shape[2] == 6:
            detections = output[0]  # Remove batch dimension
            confidences = detections[:, 4]
            mask = confidences > self.conf_threshold
            filtered = detections[mask]

            if len(filtered) == 0:
                return []

            boxes = filtered[:, :4] / scale  # Scale back to original
            scores = filtered[:, 4]
            class_ids = filtered[:, 5].astype(int)

        # Traditional YOLO format: (1, nc+4, 8400)
        else:
            detections = output[0].T  # (8400, nc+4)
            confidences = detections[:, 4]
            mask = confidences > self.conf_threshold
            filtered = detections[mask]

            if len(filtered) == 0:
                return []

            # Convert center format to corner format
            boxes = filtered[:, :4].copy()
            boxes[:, 0] -= boxes[:, 2] / 2  # x1
            boxes[:, 1] -= boxes[:, 3] / 2  # y1
            boxes[:, 2] += boxes[:, 0]      # x2
            boxes[:, 3] += boxes[:, 1]      # y2

            scores = filtered[:, 4]
            class_ids = filtered[:, 5].astype(int)

            # NMS
            indices = self._nms(boxes, scores, self.iou_threshold)
            boxes = boxes[indices] / scale
            scores = scores[indices]
            class_ids = class_ids[indices]

        # Clamp to image bounds and format results
        h, w = orig_shape[:2]
        results = []

        for box, score, class_id in zip(boxes, scores, class_ids):
            x1, y1, x2, y2 = box
            x1 = max(0, min(x1, w))
            y1 = max(0, min(y1, h))
            x2 = max(0, min(x2, w))
            y2 = max(0, min(y2, h))

            results.append({
                'bbox': [int(x1), int(y1), int(x2), int(y2)],
                'confidence': float(score),
                'class_id': int(class_id)
            })

        return results

    def classify_crop(self, crop: np.ndarray) -> Dict:
        """Classify a bird crop into species group"""
        if crop.size == 0:
            return {'species': 'UNKNOWN', 'confidence': 0.0}

        try:
            input_tensor = self.preprocess_classification(crop)
            outputs = self.classifier_session.run(None, {self.classifier_input_name: input_tensor})
            logits = outputs[0][0]

            # Softmax
            exp_logits = np.exp(logits - np.max(logits))
            probs = exp_logits / np.sum(exp_logits)

            top_idx = np.argmax(probs)
            return {
                'species': self.species_groups[top_idx],
                'confidence': float(probs[top_idx])
            }
        except Exception as e:
            print(f"Classification error: {e}")
            return {'species': 'UNKNOWN', 'confidence': 0.0}

    def _nms(self, boxes: np.ndarray, scores: np.ndarray, iou_threshold: float) -> List[int]:
        """Non-Maximum Suppression"""
        x1, y1, x2, y2 = boxes[:, 0], boxes[:, 1], boxes[:, 2], boxes[:, 3]
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

    def detect_and_classify(self, image_path: str, sahi_slices: Optional[int] = None) -> Dict:
        """
        Detect and classify birds in an image.

        Args:
            image_path: Path to image
            sahi_slices: Number of slices per dimension (e.g., 2 = 2x2 grid)

        Returns:
            Dict with detections, stats, and timing
        """
        start_time = time.time()

        # Read image
        image = cv2.imread(str(image_path))
        if image is None:
            return {'error': 'Failed to read image'}

        h, w = image.shape[:2]

        # SAHI sliced inference for large images
        if sahi_slices and sahi_slices > 1:
            detections = self._sahi_inference(image, sahi_slices)
        else:
            # Standard inference
            input_tensor, scale = self.preprocess_detection(image)
            outputs = self.detector_session.run(None, {self.detector_input_name: input_tensor})
            detections = self.postprocess_detection(outputs, image.shape[:2], scale)

        # Classify each detection
        classified_detections = []
        for det in detections:
            x1, y1, x2, y2 = det['bbox']
            crop = image[y1:y2, x1:x2]

            if crop.size > 0:
                classification = self.classify_crop(crop)
                det['species'] = classification['species']
                det['species_confidence'] = classification['confidence']
            else:
                det['species'] = 'UNKNOWN'
                det['species_confidence'] = 0.0

            classified_detections.append(det)

        inference_time = time.time() - start_time

        return {
            'image_path': str(image_path),
            'image_size': {'width': w, 'height': h},
            'detections': classified_detections,
            'bird_count': len(classified_detections),
            'inference_time': inference_time,
            'sahi_used': sahi_slices is not None
        }

    def _sahi_inference(self, image: np.ndarray, slices: int) -> List[Dict]:
        """
        SAHI (Slicing Aided Hyper Inference) for large images.

        Splits image into overlapping tiles for better small object detection.
        """
        h, w = image.shape[:2]
        slice_h = h // slices
        slice_w = w // slices
        overlap = 0.2  # 20% overlap between slices

        all_detections = []

        for i in range(slices):
            for j in range(slices):
                # Calculate slice bounds with overlap
                y1 = max(0, int(i * slice_h - i * slice_h * overlap))
                y2 = min(h, int((i + 1) * slice_h + i * slice_h * overlap))
                x1 = max(0, int(j * slice_w - j * slice_w * overlap))
                x2 = min(w, int((j + 1) * slice_w + j * slice_w * overlap))

                # Extract slice
                slice_img = image[y1:y2, x1:x2]

                # Run detection on slice
                input_tensor, scale = self.preprocess_detection(slice_img)
                outputs = self.detector_session.run(None, {self.detector_input_name: input_tensor})
                slice_detections = self.postprocess_detection(outputs, slice_img.shape[:2], scale)

                # Adjust coordinates to global image space
                for det in slice_detections:
                    det['bbox'][0] += x1
                    det['bbox'][1] += y1
                    det['bbox'][2] += x1
                    det['bbox'][3] += y1

                all_detections.extend(slice_detections)

        # Merge overlapping detections with NMS
        if all_detections:
            boxes = np.array([d['bbox'] for d in all_detections])
            scores = np.array([d['confidence'] for d in all_detections])
            keep_indices = self._nms(boxes, scores, self.iou_threshold)
            all_detections = [all_detections[i] for i in keep_indices]

        return all_detections


def draw_detections(image: np.ndarray, detections: List[Dict]) -> np.ndarray:
    """Draw bounding boxes and labels on image"""
    result = image.copy()

    # Species colors
    colors = {
        'COLOR_WADER': (255, 150, 100),  # Orange
        'DARK': (100, 100, 100),         # Gray
        'GULL': (255, 255, 255),         # White
        'PELICAN': (0, 200, 255),        # Cyan
        'SHOREBIRD': (150, 200, 100),    # Light green
        'TERN': (255, 200, 0),           # Yellow
        'WHITE_WADER': (255, 255, 200),  # Cream
        'UNKNOWN': (128, 128, 128)       # Gray
    }

    for det in detections:
        x1, y1, x2, y2 = det['bbox']
        species = det.get('species', 'UNKNOWN')
        conf = det.get('confidence', 0.0)
        species_conf = det.get('species_confidence', 0.0)

        color = colors.get(species, (0, 255, 0))

        # Draw box
        cv2.rectangle(result, (x1, y1), (x2, y2), color, 2)

        # Draw label background
        label = f"{species} {species_conf:.2f}"
        (label_w, label_h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
        cv2.rectangle(result, (x1, y1 - label_h - 5), (x1 + label_w, y1), color, -1)

        # Draw label text
        cv2.putText(result, label, (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX,
                   0.5, (0, 0, 0), 1, cv2.LINE_AA)

    return result
