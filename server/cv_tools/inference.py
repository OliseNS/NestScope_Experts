"""
Computer Vision Inference Module for Bird Detection
Uses YOLOv6m model to detect and count birds in images
"""

from ultralytics import YOLO
import cv2
import os
from pathlib import Path
import numpy as np

# Model path - relative to server directory
MODEL_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "best.pt")

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
        """Load the YOLO model"""
        if not os.path.exists(self.model_path):
            raise FileNotFoundError(f"Model not found at {self.model_path}")

        try:
            self.model = YOLO(self.model_path)
            print(f"Model loaded successfully from {self.model_path}")
        except Exception as e:
            raise RuntimeError(f"Failed to load model: {str(e)}")

    def _draw_custom_annotations(self, image, boxes):
        """
        Draw custom annotations on image with specified color and no text

        Args:
            image: Original image array
            boxes: YOLO boxes object

        Returns:
            Annotated image with custom styling
        """
        annotated_img = image.copy()

        # Claude orange color #D97757 in BGR format for OpenCV
        box_color = (87, 119, 217)  # BGR: (87, 119, 217) = RGB: (217, 119, 87) = #D97757
        thickness = 3  # Box thickness

        for box in boxes:
            # Get bounding box coordinates
            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
            x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)

            # Draw rectangle with no text
            cv2.rectangle(annotated_img, (x1, y1), (x2, y2), box_color, thickness)

        return annotated_img

    def predict(self, image_path, conf_threshold=0.25):
        """
        Run inference on an image

        Args:
            image_path: Path to the input image
            conf_threshold: Confidence threshold for detections (default: 0.25)

        Returns:
            dict: Results containing:
                - bird_count: Number of birds detected
                - detections: List of detection info (bbox, confidence)
                - annotated_image: Image with bounding boxes drawn
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image not found at {image_path}")

        # Run inference
        results = self.model.predict(
            source=image_path,
            imgsz=self.imgsz,
            conf=conf_threshold,
            verbose=False
        )

        # Extract results
        result = results[0]
        boxes = result.boxes

        # Read original image
        original_img = cv2.imread(image_path)

        # Draw custom annotations
        annotated_img = self._draw_custom_annotations(original_img, boxes)

        # Extract detection information
        detections = []
        for box in boxes:
            detection_info = {
                'bbox': box.xyxy[0].cpu().numpy().tolist(),  # [x1, y1, x2, y2]
                'confidence': float(box.conf[0]),
                'class_id': int(box.cls[0]) if box.cls is not None else 0
            }
            detections.append(detection_info)

        return {
            'bird_count': len(detections),
            'detections': detections,
            'annotated_image': annotated_img,
            'image_path': image_path
        }

    def predict_from_bytes(self, image_bytes, conf_threshold=0.25):
        """
        Run inference on image bytes (from uploaded file)

        Args:
            image_bytes: Image data as bytes
            conf_threshold: Confidence threshold for detections

        Returns:
            dict: Same as predict()
        """
        # Convert bytes to numpy array
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        # Run inference
        results = self.model.predict(
            source=img,
            imgsz=self.imgsz,
            conf=conf_threshold,
            verbose=False
        )

        # Extract results
        result = results[0]
        boxes = result.boxes

        # Draw custom annotations
        annotated_img = self._draw_custom_annotations(img, boxes)

        # Extract detection information
        detections = []
        for box in boxes:
            detection_info = {
                'bbox': box.xyxy[0].cpu().numpy().tolist(),
                'confidence': float(box.conf[0]),
                'class_id': int(box.cls[0]) if box.cls is not None else 0
            }
            detections.append(detection_info)

        return {
            'bird_count': len(detections),
            'detections': detections,
            'annotated_image': annotated_img
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
