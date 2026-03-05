"""
Nestperts - Image-Pro Replacement for Avian Data Annotation

A Flask application for expert ornithologists to annotate bird images with:
1. Bounding box drawing (with MobileSAM assistance)
2. Gamified species identification (Akinator-style)
3. Task queue management
4. Progress tracking and achievements

This completely replaces the Image-Pro workflow with an AI-assisted,
gamified experience that's faster and more engaging.
"""

import os
import sys
import json
import glob
import argparse
import numpy as np
import cv2
import torch
import threading
from urllib.parse import quote
from flask import Flask, render_template, request, jsonify, send_from_directory, url_for
from datetime import datetime

# Add project root to path for imports
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Import species service for database access
from services.species_service import get_species_service
from services.wikipedia_images_v2 import get_wikipedia_images

app = Flask(__name__)

# ============================================================================
# CONFIGURATION
# ============================================================================

class Config:
    """Centralized configuration"""
    DATASET_PATH = "nestvision"
    STATE_FILE = "project_state.json"
    CLASSES_FILE = "classes.txt"
    SAM_MODEL_PATH = os.path.join("..", "models", "mobile_sam.pt")

    # SAM settings
    SAM_CONF_THRESHOLD = 0.5
    SAM_IMGSZ = 720
    MAX_MASK_AREA_RATIO = 0.3
    MIN_MASK_AREA = 50
    BBOX_PADDING = 0.05

# MobileSAM model (lazy loaded)
MOBILESAM_MODEL = None
INFERENCE_LOCK = threading.Lock()

# Species classifier (lazy loaded)
BIRD_DETECTOR = None

# Image cache to reduce redundant loading
IMAGE_CACHE = {
    "filename": None,
    "data": None,
    "timestamp": None
}
CACHE_TIMEOUT = 300  # 5 minutes

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def get_image_dir():
    """Returns the images directory path"""
    img_dir = os.path.join(Config.DATASET_PATH, "images")
    if os.path.exists(img_dir) and os.path.isdir(img_dir):
        return img_dir
    return Config.DATASET_PATH

def get_label_dir():
    """Returns the labels directory path"""
    lbl_dir = os.path.join(Config.DATASET_PATH, "labels")
    if os.path.exists(lbl_dir) and os.path.isdir(lbl_dir):
        return lbl_dir
    return Config.DATASET_PATH

def load_state():
    """Load project state from JSON file"""
    if os.path.exists(Config.STATE_FILE):
        with open(Config.STATE_FILE, 'r') as f:
            return json.load(f)
    return None

def save_state(state):
    """Save project state to JSON file"""
    with open(Config.STATE_FILE, 'w') as f:
        json.dump(state, f, indent=4)

def get_classes():
    """Load class names from classes.txt or data.yaml"""
    class_path = os.path.join(Config.DATASET_PATH, Config.CLASSES_FILE)
    if os.path.exists(class_path):
        with open(class_path, 'r') as f:
            return [line.strip() for line in f.readlines() if line.strip()]
    return ["bird"]  # Default class

def get_all_images():
    """Get list of all image files in dataset"""
    img_dir = get_image_dir()
    extensions = ['*.jpg', '*.jpeg', '*.png', '*.JPG', '*.JPEG', '*.PNG']
    images = []
    for ext in extensions:
        images.extend(glob.glob(os.path.join(img_dir, ext)))
    return sorted([os.path.basename(img) for img in images])

def load_labels(image_name):
    """Load existing labels for an image"""
    label_file = os.path.splitext(image_name)[0] + ".txt"
    label_path = os.path.join(get_label_dir(), label_file)

    if not os.path.exists(label_path):
        return []

    boxes = []
    with open(label_path, 'r') as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) >= 5:
                boxes.append({
                    'class_id': int(parts[0]),
                    'x_center': float(parts[1]),
                    'y_center': float(parts[2]),
                    'width': float(parts[3]),
                    'height': float(parts[4]),
                    'species': parts[5] if len(parts) > 5 else None,
                    'confidence': float(parts[6]) if len(parts) > 6 else None
                })
    return boxes

def save_labels(image_name, boxes):
    """Save labels for an image in YOLO format"""
    label_file = os.path.splitext(image_name)[0] + ".txt"
    label_path = os.path.join(get_label_dir(), label_file)

    with open(label_path, 'w') as f:
        for box in boxes:
            line = f"{box['class_id']} {box['x_center']} {box['y_center']} {box['width']} {box['height']}"
            if box.get('species'):
                line += f" {box['species']}"
            if box.get('confidence'):
                line += f" {box['confidence']}"
            f.write(line + '\n')

def calculate_user_stats(username):
    """Calculate statistics for a user"""
    state = load_state()
    if not state:
        return {}

    # Handle both 'users' and 'assignments' keys
    users_data = state.get('users', state.get('assignments', {}))
    if username not in users_data:
        return {}

    user = users_data[username]
    completed = user.get('completed', [])

    # Count total birds identified
    total_birds = 0
    for img in completed:
        boxes = load_labels(img)
        total_birds += len([b for b in boxes if b.get('species')])

    # Get assigned images count
    assigned = user.get('assigned', user.get('images', []))

    return {
        'images_completed': len(completed),
        'images_total': len(assigned),
        'species_identified': total_birds,
        'accuracy': 94.2,  # Placeholder - would calculate from validation data
        'hours_saved': len(completed) * 0.15,  # Estimate 9 min/image saved
        'streak': user.get('streak_days', 0),
        'today_count': user.get('today_count', 0)
    }

# ============================================================================
# SPECIES & GAMIFICATION
# ============================================================================

def get_species_list():
    """Get list of all species from database with proper structure"""
    try:
        species_service = get_species_service()
        species = species_service.get_all_species()
        # Convert to proper format expected by frontend
        return [
            {
                'code': s['code'],
                'common_name': s['name'],
                'scientific_name': s.get('scientific_name', ''),  # Will be empty, can enhance later
            }
            for s in species
        ]
    except Exception as e:
        print(f"Error loading species: {e}")
        return []

def get_question_tree():
    """Get the decision tree questions for species identification (optimized for aerial view)"""
    return [
        {
            "id": 1,
            "question": "What is the bird's overall body size?",
            "options": ["Large (pelican/heron size)", "Medium (gull/tern size)", "Small (plover size)", "Not Sure"],
            "filter_key": "body_size"
        },
        {
            "id": 2,
            "question": "What is the dominant plumage color from above?",
            "options": ["White/Light", "Dark/Black", "Brown/Gray", "Mixed/Patterned", "Not Sure"],
            "filter_key": "plumage_color"
        },
        {
            "id": 3,
            "question": "What is the bill shape visible from above?",
            "options": ["Long and straight (spear-like)", "Long and curved (sickle-like)", "Short and thick", "Medium/pointed", "Not Sure"],
            "filter_key": "bill_shape"
        },
        {
            "id": 4,
            "question": "Can you see the legs extending beyond the tail when perched?",
            "options": ["Yes (long legs visible)", "No (legs not visible/short)", "Not Sure"],
            "filter_key": "leg_length"
        },
        {
            "id": 5,
            "question": "What is the neck appearance from above?",
            "options": ["Very long (S-curved)", "Long (straight)", "Medium", "Short/thick", "Not Sure"],
            "filter_key": "neck_length"
        },
        {
            "id": 6,
            "question": "Are there any distinctive markings visible from above?",
            "options": ["Orange/red bill or legs", "Black cap or crest", "Wing patterns/bars", "Solid color (no distinctive marks)", "Not Sure"],
            "filter_key": "distinctive_marks"
        }
    ]

# ============================================================================
# MOBILESAM SEGMENTATION & SPECIES CLASSIFICATION
# ============================================================================

def load_sam_model():
    """Lazy load MobileSAM model"""
    global MOBILESAM_MODEL
    if MOBILESAM_MODEL is None:
        try:
            from ultralytics import SAM
            model_path = Config.SAM_MODEL_PATH
            if os.path.exists(model_path):
                MOBILESAM_MODEL = SAM(model_path)
                print(f"✓ MobileSAM loaded from {model_path}")
            else:
                print(f"✗ MobileSAM model not found at {model_path}")
                return None
        except Exception as e:
            print(f"✗ Error loading MobileSAM: {e}")
            return None
    return MOBILESAM_MODEL

def load_classifier():
    """Lazy load species classifier"""
    global BIRD_DETECTOR
    if BIRD_DETECTOR is None:
        try:
            # Import BirdDetector from the server CV tools
            sys.path.insert(0, os.path.join(PROJECT_ROOT, 'server'))
            from cv_tools.inference import BirdDetector

            BIRD_DETECTOR = BirdDetector()
            print(f"✓ Species classifier loaded")
        except Exception as e:
            print(f"✗ Error loading species classifier: {e}")
            import traceback
            traceback.print_exc()
            return None
    return BIRD_DETECTOR

def sam_segment_point(image_path, points):
    """
    Segment image using MobileSAM with point prompts

    Args:
        image_path: Path to image file
        points: List of [x, y] click coordinates

    Returns:
        List of bounding boxes [x, y, w, h] in normalized coordinates
    """
    with INFERENCE_LOCK:
        model = load_sam_model()
        if model is None:
            return {"error": "SAM model not loaded"}

        try:
            # Load image
            image = cv2.imread(image_path)
            if image is None:
                return {"error": "Failed to load image"}

            height, width = image.shape[:2]

            # Convert points to SAM format
            sam_points = np.array(points)

            # Run segmentation
            results = model(
                image,
                points=sam_points,
                labels=np.ones(len(points)),  # All positive points
                imgsz=Config.SAM_IMGSZ,
                retina_masks=False,
                conf=Config.SAM_CONF_THRESHOLD
            )

            # Extract bounding boxes
            boxes = []
            if results and len(results) > 0:
                for result in results:
                    if hasattr(result, 'masks') and result.masks is not None:
                        for mask_data in result.masks.data:
                            # Convert mask to bbox
                            mask = mask_data.cpu().numpy()
                            coords = np.column_stack(np.where(mask > 0.5))

                            if len(coords) > 0:
                                y_min, x_min = coords.min(axis=0)
                                y_max, x_max = coords.max(axis=0)

                                # Calculate area and filter
                                mask_area = len(coords)
                                image_area = height * width

                                if mask_area < Config.MIN_MASK_AREA:
                                    continue
                                if mask_area / image_area > Config.MAX_MASK_AREA_RATIO:
                                    continue

                                # Add padding
                                padding_x = int((x_max - x_min) * Config.BBOX_PADDING)
                                padding_y = int((y_max - y_min) * Config.BBOX_PADDING)

                                x_min = max(0, x_min - padding_x)
                                y_min = max(0, y_min - padding_y)
                                x_max = min(width, x_max + padding_x)
                                y_max = min(height, y_max + padding_y)

                                # Normalize to 0-1
                                x_center = (x_min + x_max) / 2 / width
                                y_center = (y_min + y_max) / 2 / height
                                w = (x_max - x_min) / width
                                h = (y_max - y_min) / height

                                boxes.append({
                                    'x_center': float(x_center),
                                    'y_center': float(y_center),
                                    'width': float(w),
                                    'height': float(h)
                                })

            return {"boxes": boxes}

        except Exception as e:
            return {"error": str(e)}

# ============================================================================
# ROUTES - Dashboard & Editor
# ============================================================================

@app.route('/')
def index():
    """Expert dashboard - shows task queue"""
    state = load_state()

    if not state:
        # First time setup - create default state
        state = {
            'users': {},
            'setup_complete': False
        }
        save_state(state)

    # Handle both 'assignments' (old format) and 'users' (new format)
    users_data = state.get('users', {})
    if not users_data and 'assignments' in state:
        # Migrate old format to new format
        users_data = state['assignments']

    # Get all users
    users = []
    for username, user_data in users_data.items():
        # Normalize user_data structure
        if 'assigned' not in user_data and 'images' in user_data:
            user_data['assigned'] = user_data['images']

        stats = calculate_user_stats(username)
        users.append({
            'name': username,
            'stats': stats
        })

    return render_template('expert_dashboard_v2.html', users=users, has_images=len(get_all_images()) > 0)

@app.route('/editor/<username>')
@app.route('/editor/<username>/<int:image_index>')
def editor(username, image_index=None):
    """Annotation editor with integrated species identification"""
    from flask import redirect
    state = load_state()

    if not state:
        return redirect('/')

    # Handle both 'users' and 'assignments' keys
    users_data = state.get('users', state.get('assignments', {}))
    if username not in users_data:
        return redirect('/')

    # Get user's assigned images
    user_data = users_data[username]
    assigned = user_data.get('assigned', user_data.get('images', []))
    completed = user_data.get('completed', [])

    if not assigned:
        return redirect('/')  # No images assigned at all

    # Determine current image based on index or next incomplete
    if image_index is not None:
        # Use specified index (1-based)
        if 1 <= image_index <= len(assigned):
            current_index = image_index
            current_image = assigned[current_index - 1]
        else:
            return redirect(f'/editor/{username}')  # Invalid index, go to default
    else:
        # Find next incomplete image
        remaining = [img for img in assigned if img not in completed]
        # If all images are completed, loop back to the first image for review
        if not remaining:
            remaining = assigned
        current_image = remaining[0]
        current_index = assigned.index(current_image) + 1

    # Load existing boxes
    boxes = load_labels(current_image)

    # Get species list for classification
    species_list = get_species_list()

    # Get question tree
    questions = get_question_tree()

    # Calculate navigation URLs
    prev_index = current_index - 1 if current_index > 1 else len(assigned)
    next_index = current_index + 1 if current_index < len(assigned) else 1

    # Debug logging
    print(f"[EDITOR] User: {username}")
    print(f"[EDITOR] Image: {current_image}")
    print(f"[EDITOR] Index: {current_index}/{len(assigned)}")
    print(f"[EDITOR] Image URL: /images/{quote(current_image)}")
    print(f"[EDITOR] Image path: {os.path.join(get_image_dir(), current_image)}")
    print(f"[EDITOR] Image exists: {os.path.exists(os.path.join(get_image_dir(), current_image))}")

    return render_template('expert_editor.html',
        username=username,
        image_name=current_image,
        image_url=f'/images/{quote(current_image)}',
        current_index=current_index,
        total_images=len(assigned),
        prev_index=prev_index,
        next_index=next_index,
        assigned_images=assigned,
        boxes=boxes,
        species_list=species_list,
        questions=questions,
        back_url='/',
        next_url=f'/editor/{quote(username)}/{next_index}',
        prev_url=f'/editor/{quote(username)}/{prev_index}'
    )

# ============================================================================
# ROUTES - API Endpoints
# ============================================================================

@app.route('/images/<path:filename>')
def serve_image(filename):
    """Serve image files"""
    img_dir = get_image_dir()
    file_path = os.path.join(img_dir, filename)

    # Debug logging
    print(f"[IMAGE SERVE] Requested: {filename}")
    print(f"[IMAGE SERVE] Directory: {img_dir}")
    print(f"[IMAGE SERVE] Full path: {file_path}")
    print(f"[IMAGE SERVE] Exists: {os.path.exists(file_path)}")

    if not os.path.exists(file_path):
        print(f"[IMAGE SERVE] ERROR: File not found!")
        return jsonify({'error': 'Image not found'}), 404

    return send_from_directory(img_dir, filename)

@app.route('/api/setup_expert', methods=['POST'])
def setup_expert():
    """Setup a new expert user with task assignment"""
    data = request.json
    username = data.get('username')
    num_images = data.get('num_images', 10)

    if not username:
        return jsonify({'error': 'Username required'}), 400

    state = load_state()
    if not state:
        state = {'users': {}, 'classes': ['bird']}

    # Handle both 'users' and 'assignments' keys
    if 'users' not in state and 'assignments' in state:
        # Migrate old format
        state['users'] = state.pop('assignments')

    if 'users' not in state:
        state['users'] = {}

    # Assign images
    all_images = get_all_images()
    if len(all_images) == 0:
        return jsonify({'error': 'No images found in dataset. Please add images to the dataset folder first.'}), 400

    assigned = all_images[:num_images] if num_images <= len(all_images) else all_images

    state['users'][username] = {
        'assigned': assigned,
        'completed': [],
        'created_at': datetime.now().isoformat(),
        'streak_days': 0,
        'today_count': 0
    }

    save_state(state)

    return jsonify({'success': True, 'assigned': len(assigned)})

@app.route('/api/save_annotation', methods=['POST'])
def save_annotation():
    """Save bounding boxes and species annotations"""
    data = request.json
    image_name = data.get('image_name')
    boxes = data.get('boxes', [])
    username = data.get('username')

    if not image_name:
        return jsonify({'error': 'Image name required'}), 400

    # Save boxes
    save_labels(image_name, boxes)

    # Update user progress
    if username:
        state = load_state()
        if state:
            # Handle both 'users' and 'assignments' keys
            users_data = state.get('users', state.get('assignments', {}))
            if username in users_data:
                completed = users_data[username].get('completed', [])
                if image_name not in completed:
                    completed.append(image_name)
                    users_data[username]['completed'] = completed
                    users_data[username]['today_count'] = users_data[username].get('today_count', 0) + 1

                    # Update state with correct key
                    if 'users' in state:
                        state['users'] = users_data
                    else:
                        state['assignments'] = users_data
                    save_state(state)

    return jsonify({'success': True})

@app.route('/api/species')
def api_species():
    """Get all species data sorted alphabetically"""
    species = get_species_list()
    # Sort by common name
    return jsonify(sorted(species, key=lambda x: x['common_name']))

@app.route('/api/species/filter', methods=['POST'])
def filter_species():
    """Filter species based on question answers (Akinator-style)"""
    data = request.json
    answers = data.get('answers', {})

    # Get all species
    all_species = get_species_list()

    # Filter based on answers
    filtered = []
    for species in all_species:
        # In production, this would use actual species characteristics
        # For now, simulate filtering
        score = 100
        for key, value in answers.items():
            if value == "unsure":
                score -= 5
            # Add actual filtering logic based on species characteristics

        if score > 60:
            species['match_score'] = score
            filtered.append(species)

    # Sort by match score
    filtered.sort(key=lambda x: x.get('match_score', 0), reverse=True)

    return jsonify(filtered[:10])  # Return top 10 matches

@app.route('/api/sam_segment', methods=['POST'])
def api_sam_segment():
    """SAM segmentation endpoint"""
    data = request.json
    image_name = data.get('image_name')
    points = data.get('points', [])

    if not image_name or not points:
        return jsonify({'error': 'Image name and points required'}), 400

    image_path = os.path.join(get_image_dir(), image_name)
    if not os.path.exists(image_path):
        return jsonify({'error': 'Image not found'}), 404

    result = sam_segment_point(image_path, points)
    return jsonify(result)

@app.route('/api/sam_status')
def sam_status():
    """Check SAM model status"""
    model = load_sam_model()
    return jsonify({
        'loaded': model is not None,
        'device': 'cuda' if torch.cuda.is_available() else 'cpu'
    })

@app.route('/api/classify_crop', methods=['POST'])
def classify_crop():
    """
    Classify a bird crop and return top-5 species predictions

    Request JSON:
        {
            "image_name": "image.jpg",
            "bbox": {
                "x_center": 0.5,
                "y_center": 0.5,
                "width": 0.1,
                "height": 0.1
            },
            "fast_mode": true  # optional, default true
        }

    Returns:
        {
            "predictions": [
                {
                    "species_code": "BRPE",
                    "species_name": "Brown Pelican",
                    "confidence": 0.85,
                    "group": "PELICAN"
                },
                ...  # top 5 predictions
            ],
            "crop_size": [width, height]
        }
    """
    try:
        data = request.json
        image_name = data.get('image_name')
        bbox = data.get('bbox')
        fast_mode = data.get('fast_mode', True)

        if not image_name or not bbox:
            return jsonify({'error': 'Missing image_name or bbox'}), 400

        # Load image
        img_dir = get_image_dir()
        image_path = os.path.join(img_dir, image_name)

        if not os.path.exists(image_path):
            return jsonify({'error': f'Image not found: {image_name}'}), 404

        # Load classifier
        detector = load_classifier()
        if detector is None:
            return jsonify({'error': 'Classifier not loaded'}), 500

        # Load image
        image = cv2.imread(image_path)
        if image is None:
            return jsonify({'error': 'Failed to read image'}), 500

        h, w = image.shape[:2]

        # Convert YOLO format (normalized) to pixel coordinates
        x_center = bbox['x_center'] * w
        y_center = bbox['y_center'] * h
        box_w = bbox['width'] * w
        box_h = bbox['height'] * h

        x1 = int(max(0, x_center - box_w / 2))
        y1 = int(max(0, y_center - box_h / 2))
        x2 = int(min(w, x_center + box_w / 2))
        y2 = int(min(h, y_center + box_h / 2))

        # Crop bird
        crop = image[y1:y2, x1:x2]

        if crop.size == 0:
            return jsonify({'error': 'Invalid crop dimensions'}), 400

        # Classify with top-5 predictions
        result = detector.classify_crop(crop, fast_mode=fast_mode, top_k=5)

        return jsonify({
            'predictions': result.get('top_predictions', []),
            'crop_size': [crop.shape[1], crop.shape[0]]
        })

    except Exception as e:
        print(f"Classification error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/user_stats/<username>')
def user_stats(username):
    """Get user statistics"""
    stats = calculate_user_stats(username)
    return jsonify(stats)

@app.route('/api/species/search', methods=['GET'])
def search_species():
    """Search species by name or code with smart fuzzy matching"""
    query = request.args.get('q', '').strip()

    # If empty query, return ALL species sorted alphabetically
    if not query:
        all_species = get_species_list()
        return jsonify(sorted(all_species, key=lambda x: x['common_name']))

    # Allow single character search for common codes
    if len(query) < 1:
        return jsonify([])

    all_species = get_species_list()
    query_lower = query.lower()

    # Enhanced search with multiple strategies:
    # 1. Exact code match (case-insensitive)
    # 2. Code starts with query
    # 3. Code contains query (for abbreviations like "LAGU" matching "LAGU")
    # 4. Common name starts with query
    # 5. Common name contains any word starting with query
    # 6. Common name contains query anywhere

    exact_code_matches = []
    code_starts_matches = []
    code_contains_matches = []
    name_starts_matches = []
    name_word_starts_matches = []
    name_contains_matches = []

    for species in all_species:
        code_lower = species['code'].lower()
        name_lower = species['common_name'].lower()

        # Code matching
        if code_lower == query_lower:
            exact_code_matches.append(species)
        elif code_lower.startswith(query_lower):
            code_starts_matches.append(species)
        elif query_lower in code_lower:
            code_contains_matches.append(species)
        # Name matching
        elif name_lower.startswith(query_lower):
            name_starts_matches.append(species)
        # Check if any word in the name starts with the query
        elif any(word.startswith(query_lower) for word in name_lower.split()):
            name_word_starts_matches.append(species)
        elif query_lower in name_lower:
            name_contains_matches.append(species)

    # Combine results with priority ordering
    results = (exact_code_matches + code_starts_matches + code_contains_matches +
               name_starts_matches + name_word_starts_matches + name_contains_matches)

    return jsonify(results[:20])  # Return top 20 matches

@app.route('/api/species/images/<species_name>')
def get_species_images(species_name):
    """Get reference images for a species from Wikimedia"""
    max_images = int(request.args.get('max', 5))
    offset = int(request.args.get('offset', 0))

    print(f"\n🖼️  API Request: /api/species/images/{species_name}")
    print(f"   Parameters: max={max_images}, offset={offset}")

    try:
        images = get_wikipedia_images(species_name, max_images=max_images, offset=offset)

        response = {
            'species': species_name,
            'images': images,
            'count': len(images),
            'offset': offset,
            'has_more': len(images) == max_images  # Assume more if we got exactly max_images
        }

        print(f"✓ API Response: {len(images)} images returned")
        return jsonify(response)

    except Exception as e:
        print(f"❌ Error fetching images for {species_name}: {e}")
        import traceback
        traceback.print_exc()

        return jsonify({
            'species': species_name,
            'images': [],
            'count': 0,
            'offset': 0,
            'has_more': False,
            'error': str(e)
        }), 500

# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Nestperts - Expert Annotation Platform')
    parser.add_argument('--data', type=str, default='nestvision',
                       help='Path to dataset directory')
    parser.add_argument('--host', type=str, default='0.0.0.0',
                       help='Host to run server on')
    parser.add_argument('--port', type=int, default=5000,
                       help='Port to run server on')
    parser.add_argument('--debug', action='store_true',
                       help='Run in debug mode')

    args = parser.parse_args()

    # Update config - convert to absolute path
    Config.DATASET_PATH = os.path.abspath(args.data)
    Config.STATE_FILE = os.path.join(Config.DATASET_PATH, 'project_state.json')
    Config.CLASSES_FILE = 'classes.txt'

    # Create necessary directories
    os.makedirs(get_label_dir(), exist_ok=True)

    img_dir = get_image_dir()
    num_images = len(get_all_images())

    print("=" * 60)
    print("🦅 Nestperts - Image-Pro Replacement")
    print("=" * 60)
    print(f"📁 Dataset: {Config.DATASET_PATH}")
    print(f"🖼️  Images Directory: {img_dir}")
    print(f"🖼️  Images Found: {num_images}")
    print(f"📋 State File: {Config.STATE_FILE}")
    print(f"🌐 Server: http://{args.host}:{args.port}")
    print("=" * 60)

    if num_images == 0:
        print("⚠️  WARNING: No images found! Check your dataset directory.")
        print(f"   Expected images in: {img_dir}")
        print("=" * 60)

    app.run(host=args.host, port=args.port, debug=args.debug)
