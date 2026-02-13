"""
Computer Vision Inference Module for Bird Detection
Uses ONNX Runtime for fast bird detection inference
"""

import onnxruntime as ort
import cv2
import os
from pathlib import Path
import numpy as np
from typing import List, Tuple
import time

# Model path - relative to project root directory (using ONNX model)
MODEL_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "seconditer.onnx")

class BirdDetector:
    """YOLO-based bird detection and counting"""

    def __init__(self, model_path=MODEL_PATH, imgsz=1024):
        """
        Initialize the bird detector

        Args:
            model_path: Path to the YOLO model weights
            imgsz: Image size for inference (default: 1024)
        """
        self.model_path = model_path
        self.imgsz = imgsz
        self.model = None
        self._load_model()

    def _load_model(self):
        """Load the ONNX model"""
        if not os.path.exists(self.model_path):
            raise FileNotFoundError(f"Model not found at {self.model_path}")

        try:
            # Configure ONNX Runtime session options for better performance
            sess_options = ort.SessionOptions()
            sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL

            # Use available providers (CUDA if available, otherwise CPU)
            providers = ['CUDAExecutionProvider', 'CPUExecutionProvider']

            self.model = ort.InferenceSession(
                self.model_path,
                sess_options=sess_options,
                providers=providers
            )

            # Get model input details
            self.input_name = self.model.get_inputs()[0].name
            self.output_names = [output.name for output in self.model.get_outputs()]

            print(f"ONNX model loaded successfully from {self.model_path}")
            print(f"Using provider: {self.model.get_providers()[0]}")
        except Exception as e:
            raise RuntimeError(f"Failed to load ONNX model: {str(e)}")

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

    def _postprocess_onnx_output(self, output: np.ndarray, scale: float, pad: Tuple[int, int],
                                  conf_threshold: float = 0.25) -> List[dict]:
        """
        Postprocess ONNX model output to extract detections

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
        detections = self._postprocess_onnx_output(output[0], preprocess_scale, pad, conf_threshold)

        # Scale coordinates back to original image size
        for det in detections:
            det['bbox'][0] /= scale  # x1
            det['bbox'][1] /= scale  # y1
            det['bbox'][2] /= scale  # x2
            det['bbox'][3] /= scale  # y2

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

        # Claude orange color #D97757 in BGR format for OpenCV
        box_color = (87, 119, 217)  # BGR: (87, 119, 217) = RGB: (217, 119, 87) = #D97757
        thickness = 3  # Box thickness

        for det in detections:
            # Get bounding box coordinates
            x1, y1, x2, y2 = det['bbox']
            x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)

            # Draw rectangle with no text
            cv2.rectangle(annotated_img, (x1, y1), (x2, y2), box_color, thickness)

        return annotated_img

    def predict(self, image_path, conf_threshold=0.25, use_sliding_window=True, fast_mode=True):
        """
        Run inference on an image using sliding window approach for large images

        Args:
            image_path: Path to the input image
            conf_threshold: Confidence threshold for detections (default: 0.25)
            use_sliding_window: Whether to use sliding window for large images (default: True)
            fast_mode: Processing mode (default: True)
                - True (Fast Mode): For very large images (>2048px), uses downsampling for 5-10x speed boost.
                                     For medium images, uses 64px overlap for 2x speed improvement.
                - False (Standard Mode): Splits image into ~10 overlapping 1024x1024 tiles with sliding window approach
                                          for improved accuracy. Uses adaptive overlap based on image size.

        Returns:
            dict: Results containing:
                - bird_count: Number of birds detected
                - detections: List of detection info (bbox, confidence)
                - annotated_image: Image with bounding boxes drawn
                - inference_time: Time taken for inference in seconds
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image not found at {image_path}")

        # Start timing
        start_time = time.perf_counter()

        # Read original image
        original_img = cv2.imread(image_path)
        height, width = original_img.shape[:2]

        # Check if we need sliding window (image larger than model input size)
        if use_sliding_window and (height > self.imgsz or width > self.imgsz):
            # For very large images, use downsampling to avoid excessive windows
            # Fast mode: >2048px uses downsampling (2x model size)
            # Standard mode: always uses sliding window with overlap for better accuracy
            downsample_threshold = self.imgsz * 2 if fast_mode else float('inf')

            if height > downsample_threshold or width > downsample_threshold:
                detections = self._downsample_and_predict(original_img, conf_threshold)
            else:
                # Fast mode: minimal overlap (64px) for speed
                # Standard mode: adaptive overlap to achieve ~10 tiles for improved accuracy
                if fast_mode:
                    overlap = 64
                else:
                    # Calculate overlap to achieve approximately 10 windows
                    # For a square-ish image, we want ~3x3 or ~3x4 grid = ~10 windows
                    max_dim = max(height, width)
                    # Calculate stride needed for ~10 windows
                    target_windows_per_side = 3.2  # sqrt(10) ≈ 3.16
                    stride = int(max_dim / target_windows_per_side)
                    overlap = max(128, self.imgsz - stride)  # At least 128px overlap
                    overlap = min(overlap, 512)  # Cap at 512px to avoid too many windows

                detections = self._predict_with_sliding_window(original_img, conf_threshold, overlap=overlap)
        else:
            # Use standard ONNX inference for small images
            preprocessed, scale, pad = self._preprocess_image(original_img)

            # Run ONNX inference
            output = self.model.run(self.output_names, {self.input_name: preprocessed})

            # Postprocess output
            detections = self._postprocess_onnx_output(output[0], scale, pad, conf_threshold)

        # Calculate inference time (before drawing annotations)
        inference_time = time.perf_counter() - start_time

        # Draw custom annotations
        annotated_img = self._draw_custom_annotations_from_detections(original_img, detections)

        return {
            'bird_count': len(detections),
            'detections': detections,
            'annotated_image': annotated_img,
            'image_path': image_path,
            'inference_time': inference_time
        }

    def _predict_with_sliding_window(self, image: np.ndarray, conf_threshold: float = 0.45, overlap: int = 64) -> List[dict]:
        """
        Run inference using sliding window approach

        Args:
            image: Input image as numpy array
            conf_threshold: Confidence threshold for detections
            overlap: Overlap between windows in pixels
                - 64: Fast mode (minimal overlap)
                - 128-512: Standard mode (adaptive overlap for ~10 windows, improved accuracy)

        Returns:
            List of detection dictionaries
        """
        height, width = image.shape[:2]
        windows = self._generate_sliding_windows((height, width), self.imgsz, overlap=overlap)

        all_detections = []

        mode_name = f"Standard ({overlap}px overlap)" if overlap >= 128 else f"Fast ({overlap}px overlap)"
        print(f"[Sliding Window Mode] Processing {len(windows)} windows for {width}x{height} image using {mode_name}...")

        for idx, (x1, y1, x2, y2) in enumerate(windows, 1):
            # Show progress every 10 windows
            if idx % 10 == 0 or idx == len(windows):
                print(f"  Processing window {idx}/{len(windows)}...")

            # Extract window
            window = image[y1:y2, x1:x2]

            # Preprocess window for ONNX
            preprocessed, scale, pad = self._preprocess_image(window)

            # Run ONNX inference on window
            output = self.model.run(self.output_names, {self.input_name: preprocessed})

            # Postprocess output
            window_detections = self._postprocess_onnx_output(output[0], scale, pad, conf_threshold)

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
        Run inference on image bytes (from uploaded file) using sliding window for large images

        Args:
            image_bytes: Image data as bytes
            conf_threshold: Confidence threshold for detections
            use_sliding_window: Whether to use sliding window for large images (default: True)
            fast_mode: Processing mode (default: True)
                - True (Fast Mode): For very large images (>2048px), uses downsampling for 5-10x speed boost.
                                     For medium images, uses 64px overlap for 2x speed improvement.
                - False (Standard Mode): Splits image into ~10 overlapping 1024x1024 tiles with sliding window approach
                                          for improved accuracy. Uses adaptive overlap based on image size.

        Returns:
            dict: Same as predict()
        """
        # Start timing
        start_time = time.perf_counter()

        # Convert bytes to numpy array
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        height, width = img.shape[:2]

        # Check if we need sliding window (image larger than model input size)
        if use_sliding_window and (height > self.imgsz or width > self.imgsz):
            # For very large images, use downsampling to avoid excessive windows
            # Fast mode: >2048px uses downsampling (2x model size)
            # Standard mode: always uses sliding window with overlap for better accuracy
            downsample_threshold = self.imgsz * 2 if fast_mode else float('inf')

            if height > downsample_threshold or width > downsample_threshold:
                detections = self._downsample_and_predict(img, conf_threshold)
            else:
                # Fast mode: minimal overlap (64px) for speed
                # Standard mode: adaptive overlap to achieve ~10 tiles for improved accuracy
                if fast_mode:
                    overlap = 64
                else:
                    # Calculate overlap to achieve approximately 10 windows
                    # For a square-ish image, we want ~3x3 or ~3x4 grid = ~10 windows
                    max_dim = max(height, width)
                    # Calculate stride needed for ~10 windows
                    target_windows_per_side = 3.2  # sqrt(10) ≈ 3.16
                    stride = int(max_dim / target_windows_per_side)
                    overlap = max(128, self.imgsz - stride)  # At least 128px overlap
                    overlap = min(overlap, 512)  # Cap at 512px to avoid too many windows

                detections = self._predict_with_sliding_window(img, conf_threshold, overlap=overlap)
        else:
            # Use standard ONNX inference for small images
            preprocessed, scale, pad = self._preprocess_image(img)

            # Run ONNX inference
            output = self.model.run(self.output_names, {self.input_name: preprocessed})

            # Postprocess output
            detections = self._postprocess_onnx_output(output[0], scale, pad, conf_threshold)

        # Calculate inference time (before drawing annotations)
        inference_time = time.perf_counter() - start_time

        # Draw custom annotations
        annotated_img = self._draw_custom_annotations_from_detections(img, detections)

        return {
            'bird_count': len(detections),
            'detections': detections,
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
