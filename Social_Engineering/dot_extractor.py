#!/usr/bin/env python3
"""
Dot Extractor - Extract bird dot annotations from expert-dotted screenshots
"""

import cv2
import numpy as np
from typing import List, Tuple, Dict, Optional
from pathlib import Path
import json


class DotExtractor:
    """Extract dot coordinates from expert-annotated screenshots"""

    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize dot extractor with color ranges

        Args:
            config: Optional config dict with color ranges
        """
        self.config = config or self._default_config()

    def _default_config(self) -> Dict:
        """Default configuration for dot detection"""
        return {
            'color_ranges': {
                # HSV color ranges for common annotation colors
                'red1': {'lower': [0, 100, 100], 'upper': [10, 255, 255]},
                'red2': {'lower': [170, 100, 100], 'upper': [180, 255, 255]},  # Red wraps around
                'yellow': {'lower': [20, 100, 100], 'upper': [35, 255, 255]},
                'green': {'lower': [40, 100, 100], 'upper': [80, 255, 255]},
                'cyan': {'lower': [80, 100, 100], 'upper': [100, 255, 255]},
                'blue': {'lower': [100, 100, 100], 'upper': [130, 255, 255]},
                'magenta': {'lower': [140, 100, 100], 'upper': [170, 255, 255]},
                'orange': {'lower': [10, 100, 100], 'upper': [20, 255, 255]},
            },
            'min_dot_radius': 2,
            'max_dot_radius': 20,
            'min_circularity': 0.5,
            'min_area': 10,
            'max_area': 400,
        }

    def extract_dots(self, image_path: str, visualize: bool = False) -> Tuple[List[Dict], Optional[np.ndarray]]:
        """
        Extract dot coordinates from annotated image

        Args:
            image_path: Path to dotted screenshot
            visualize: If True, return visualization image

        Returns:
            (dots, vis_image) where dots is list of {x, y, color, radius}
        """
        # Read image
        image = cv2.imread(str(image_path))
        if image is None:
            raise ValueError(f"Could not read image: {image_path}")

        # Convert to HSV for color-based detection
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

        all_dots = []
        all_masks = []

        # Try each color range
        for color_name, color_range in self.config['color_ranges'].items():
            lower = np.array(color_range['lower'])
            upper = np.array(color_range['upper'])

            # Create mask for this color
            mask = cv2.inRange(hsv, lower, upper)

            # Morphological operations to clean up
            kernel = np.ones((3, 3), np.uint8)
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=1)

            all_masks.append(mask)

            # Find contours
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            for contour in contours:
                # Filter by area
                area = cv2.contourArea(contour)
                if area < self.config['min_area'] or area > self.config['max_area']:
                    continue

                # Calculate circularity
                perimeter = cv2.arcLength(contour, True)
                if perimeter == 0:
                    continue
                circularity = 4 * np.pi * area / (perimeter ** 2)

                if circularity < self.config['min_circularity']:
                    continue

                # Get center and radius
                (x, y), radius = cv2.minEnclosingCircle(contour)

                if radius < self.config['min_dot_radius'] or radius > self.config['max_dot_radius']:
                    continue

                all_dots.append({
                    'x': float(x),
                    'y': float(y),
                    'radius': float(radius),
                    'color': color_name,
                    'area': float(area),
                    'circularity': float(circularity)
                })

        # Remove duplicate dots (same location detected in multiple colors)
        dots = self._remove_duplicates(all_dots, threshold=5)

        vis_image = None
        if visualize:
            vis_image = self._create_visualization(image, dots, all_masks)

        return dots, vis_image

    def _remove_duplicates(self, dots: List[Dict], threshold: float = 5) -> List[Dict]:
        """Remove duplicate dots within threshold distance"""
        if not dots:
            return []

        # Sort by area (larger = more confident)
        dots = sorted(dots, key=lambda d: d['area'], reverse=True)

        filtered = []
        for dot in dots:
            # Check if too close to existing dot
            too_close = False
            for existing in filtered:
                dist = np.sqrt((dot['x'] - existing['x'])**2 + (dot['y'] - existing['y'])**2)
                if dist < threshold:
                    too_close = True
                    break

            if not too_close:
                filtered.append(dot)

        return filtered

    def _create_visualization(self, image: np.ndarray, dots: List[Dict], masks: List[np.ndarray]) -> np.ndarray:
        """Create visualization showing detected dots"""
        vis = image.copy()

        # Color mapping for visualization
        color_map = {
            'red1': (0, 0, 255),
            'red2': (0, 0, 255),
            'yellow': (0, 255, 255),
            'green': (0, 255, 0),
            'cyan': (255, 255, 0),
            'blue': (255, 0, 0),
            'magenta': (255, 0, 255),
            'orange': (0, 165, 255),
        }

        # Draw detected dots
        for i, dot in enumerate(dots):
            x, y = int(dot['x']), int(dot['y'])
            radius = int(dot['radius']) + 3  # Slightly larger for visibility
            color = color_map.get(dot['color'], (255, 255, 255))

            # Draw circle
            cv2.circle(vis, (x, y), radius, color, 2)

            # Draw center point
            cv2.circle(vis, (x, y), 2, color, -1)

            # Draw number
            cv2.putText(vis, str(i+1), (x+5, y-5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)

        # Add stats overlay
        h, w = image.shape[:2]
        overlay = vis.copy()
        cv2.rectangle(overlay, (10, 10), (300, 80), (0, 0, 0), -1)
        vis = cv2.addWeighted(vis, 0.7, overlay, 0.3, 0)

        cv2.putText(vis, f"Detected Dots: {len(dots)}", (20, 35),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        # Color breakdown
        color_counts = {}
        for dot in dots:
            color = dot['color']
            color_counts[color] = color_counts.get(color, 0) + 1

        y_pos = 60
        for color, count in sorted(color_counts.items(), key=lambda x: x[1], reverse=True)[:3]:
            cv2.putText(vis, f"  {color}: {count}", (20, y_pos),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
            y_pos += 20

        return vis

    def extract_batch(self, image_paths: List[str], output_dir: Optional[Path] = None) -> Dict:
        """
        Extract dots from batch of images

        Args:
            image_paths: List of image paths
            output_dir: Optional directory to save visualizations

        Returns:
            Dict with results for each image
        """
        results = {}

        if output_dir:
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)

        for i, image_path in enumerate(image_paths):
            print(f"Processing [{i+1}/{len(image_paths)}]: {Path(image_path).name}")

            try:
                dots, vis_image = self.extract_dots(image_path, visualize=True)

                results[Path(image_path).name] = {
                    'dots': dots,
                    'count': len(dots),
                    'success': True
                }

                # Save visualization
                if output_dir and vis_image is not None:
                    vis_path = output_dir / f"{Path(image_path).stem}_extracted.jpg"
                    cv2.imwrite(str(vis_path), vis_image)

                print(f"   Found {len(dots)} dots")

            except Exception as e:
                print(f"   Error: {e}")
                results[Path(image_path).name] = {
                    'error': str(e),
                    'success': False
                }

        return results


def test_on_sample_image():
    """Test dot extraction on a sample image"""
    # For testing, we'll need to download a sample first
    # This is a placeholder for demonstration

    extractor = DotExtractor()

    print("Testing dot extraction")
    print("="*60)

    # This would work with actual downloaded images
    # For now, just demonstrate the API

    print("\n DotExtractor initialized with config:")
    print(json.dumps(extractor.config, indent=2))


if __name__ == "__main__":
    test_on_sample_image()
