"""
Image processing utilities for computer vision features
"""

import streamlit as st
import csv
import random as pyrandom
import numpy as np
import cv2
from typing import List, Tuple, Dict, Any


@st.cache_data(ttl=3600)
def load_species_list() -> List[Tuple[str, str]]:
    """
    Load species codes and names from CSV file.

    Returns:
        List of tuples (species_code, species_name)
    """
    try:
        species_map = {}
        csv_path = "CSV_Files/tblSpeciesData2015_2018_2021.csv"

        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                code = row.get('SpeciesCode', '').strip().strip('"')
                if code and code not in species_map:
                    # Use code as name for now (could be enhanced with full names)
                    species_map[code] = code

        # Convert to sorted list
        species_list = sorted([(code, code) for code in species_map.keys()])
        return species_list

    except Exception:
        # Return common bird species codes as fallback
        return [
            ("BLSK", "Black Skimmer"),
            ("BRPE", "Brown Pelican"),
            ("GBTE", "Gull-billed Tern"),
            ("LAGU", "Laughing Gull"),
            ("ROYT", "Royal Tern"),
            ("FOTE", "Forster's Tern"),
            ("LETE", "Least Tern"),
            ("TRHE", "Tricolored Heron"),
            ("GBHE", "Great Blue Heron"),
            ("SNEG", "Snowy Egret"),
        ]


def extract_crops_from_detections(
    image_bytes: bytes,
    detections: List[Dict[str, Any]],
    num_crops: int = 5
) -> List[Tuple[bytes, Dict[str, Any]]]:
    """
    Extract random crops from detected birds.

    Args:
        image_bytes: Raw image bytes
        detections: List of detection dictionaries
        num_crops: Number of crops to extract

    Returns:
        List of (crop_image_bytes, detection_info) tuples
    """
    try:
        # Decode image
        img_array = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        img_h, img_w = img.shape[:2]

        crops = []

        # Randomly sample detections
        selected_detections = pyrandom.sample(detections, min(num_crops, len(detections)))

        for det in selected_detections:
            bbox = det.get('bbox', [])
            if len(bbox) == 4:
                x1, y1, x2, y2 = [int(coord) for coord in bbox]

                # Add some padding
                padding = 10
                x1 = max(0, x1 - padding)
                y1 = max(0, y1 - padding)
                x2 = min(img_w, x2 + padding)
                y2 = min(img_h, y2 + padding)

                # Extract crop
                crop = img[y1:y2, x1:x2]

                # Encode crop as JPEG
                _, buffer = cv2.imencode('.jpg', crop)
                crop_bytes = buffer.tobytes()

                crops.append((crop_bytes, det))

        return crops

    except Exception:
        return []
