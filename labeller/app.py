import os
import sys
import json
import glob
import math
import argparse
import yaml # Requires pip install pyyaml, but we can do a simple parse if needed
import numpy as np
import cv2
import torch
import threading
import time
from flask import Flask, render_template, request, jsonify, send_from_directory, redirect, url_for, Response

# Add project root to path so we can import labeller.services modules
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Import species service for database access
from services.species_service import get_species_service

app = Flask(__name__)

# MobileSAM Model (lazy loaded) - from ultralytics
MOBILESAM_MODEL = None
MOBILESAM_MODEL_NAME = os.path.join("..", "models", "mobile_sam.pt")  # Load from root models/ directory

# Segmentation configuration
SEGMENT_CONF_THRESHOLD = 0.5  # Confidence threshold for segmentation
SEGMENT_IMGSZ = 720  # Balance between speed and accuracy for small objects
USE_HALF_PRECISION = True  # Use FP16 for faster GPU inference
MAX_SEGMENT_AREA_RATIO = 0.3  # Reject masks larger than 30% of image (likely wrong)
MIN_SEGMENT_AREA = 50  # Minimum mask area in pixels (reduced from 100)
BBOX_PADDING_RATIO = 0.05  # Add 5% padding around bounding boxes

# Cache for image processing - stores last processed image
IMAGE_CACHE = {
    "filename": None,
    "preprocessed_image": None,
    "timestamp": None
}
CACHE_TIMEOUT = 300  # Clear cache after 5 minutes

# Threading lock to prevent concurrent model inference (prevents GPU stalls)
INFERENCE_LOCK = threading.Lock()

# --- CONFIGURATION ---
# These will be updated from command-line args in main block
DATASET_PATH = "nestvision"
STATE_FILE = "project_state.json"
CLASSES_FILE = "classes.txt"
YAML_FILE = "data.yaml"

# Config holder that will be updated
class Config:
    DATASET_PATH = "nestvision"
    STATE_FILE = "project_state.json"
    CLASSES_FILE = "classes.txt"
    YAML_FILE = "data.yaml"

def get_image_dir():
    """Returns the path to the images folder (either root or ./images)"""
    sub_img = os.path.join(Config.DATASET_PATH, "images")
    if os.path.exists(sub_img) and os.path.isdir(sub_img):
        return sub_img
    return Config.DATASET_PATH

def get_label_dir():
    """Returns the path to the labels folder (either root or ./labels)"""
    sub_lbl = os.path.join(Config.DATASET_PATH, "labels")
    if os.path.exists(sub_lbl) and os.path.isdir(sub_lbl):
        return sub_lbl
    return Config.DATASET_PATH

def load_state():
    if os.path.exists(Config.STATE_FILE):
        with open(Config.STATE_FILE, 'r') as f:
            return json.load(f)
    return None

def save_state(state):
    with open(Config.STATE_FILE, 'w') as f:
        json.dump(state, f, indent=4)

def get_classes():
    # 1. Try classes.txt (standard priority)
    class_path = os.path.join(Config.DATASET_PATH, Config.CLASSES_FILE)
    if os.path.exists(class_path):
        with open(class_path, 'r') as f:
            return [line.strip() for line in f.readlines() if line.strip()]

    # 2. Try data.yaml (YOLO standard)
    yaml_path = os.path.join(Config.DATASET_PATH, Config.YAML_FILE)
    if os.path.exists(yaml_path):
        try:
            with open(yaml_path, 'r') as f:
                # Simple parsing to avoid strict pyyaml dependency if possible,
                # but assume standard yaml structure.
                # If pyyaml is installed: import yaml; data = yaml.safe_load(f)
                content = f.read()
                # Very basic manual parse for "names: [a, b]" or "names:\n  0: a"
                # For robustness, let's just return empty and let user input if parsing fails without lib
                pass
        except:
            pass

    # 3. Fallback to state
    state = load_state()
    if state and 'classes' in state:
        return state['classes']
    return []

def get_species_list():
    """
    Load species codes and names from database for expert identification.

    This function now uses the SpeciesService to load species from the
    SQLite database instead of a CSV file. Species are cached in memory
    for fast access.

    Returns:
        list: List of dicts with 'code' and 'name' keys
              Example: [{"code": "AMAV", "name": "American Avocet"}, ...]
    """
    service = get_species_service()
    return service.get_all_species()

# Singleton labeling service instance
_labeling_service_instance = None

def get_labeling_service():
    """
    Get singleton labeling service instance.

    This ensures we only create one LabelingService for the entire app,
    which keeps label data and metadata in memory for fast access.

    Returns:
        LabelingService: The singleton instance
    """
    global _labeling_service_instance
    if _labeling_service_instance is None:
        from labeller.services.labeling_service import LabelingService
        _labeling_service_instance = LabelingService(Config.DATASET_PATH)
    return _labeling_service_instance

@app.route('/')
def index():
    """
    New role-based homepage with clear separation of:
    - LABELING JOB (draw bounding boxes)
    - CLASSIFICATION JOB (identify species)

    Addresses judge feedback about clear user workflows.
    """
    state = load_state()
    if not state:
        return render_template('index_new.html', setup_needed=True, users=[])

    users_progress = []
    for user, data in state['assignments'].items():
        total = len(data['images'])
        completed = len(data['completed'])
        percent = int((completed / total) * 100) if total > 0 else 0
        users_progress.append({
            'name': user,
            'total': total,
            'completed': completed,
            'percent': percent
        })

    return render_template('index_new.html', setup_needed=False, users=users_progress)

@app.route('/setup', methods=['POST'])
def setup():
    # 1. Scan Dataset using new logic
    if not os.path.exists(Config.DATASET_PATH):
        os.makedirs(Config.DATASET_PATH, exist_ok=True)
    
    img_dir = get_image_dir()
    
    # Recursive search or simple list? Let's do simple list of known extensions
    exts = ['*.jpg', '*.jpeg', '*.png', '*.bmp']
    images = []
    for ext in exts:
        images.extend(glob.glob(os.path.join(img_dir, ext)))
        # Also check uppercase
        images.extend(glob.glob(os.path.join(img_dir, ext.upper())))

    images = [os.path.basename(img) for img in images]
    images.sort()

    if not images:
        return f"No images found in {img_dir}. Please check your path.", 400

    # 2. Get Form Data
    num_users = int(request.form.get('num_users', 1))
    class_input = request.form.get('classes', '')
    
    # 3. Handle Classes
    classes = [c.strip() for c in class_input.split(',') if c.strip()]
    if not classes:
        classes = get_classes()
    
    # Save classes.txt to root of dataset for future ref
    with open(os.path.join(Config.DATASET_PATH, Config.CLASSES_FILE), 'w') as f:
        f.write('\n'.join(classes))

    # 4. Split Logic
    chunk_size = math.ceil(len(images) / num_users)
    assignments = {}
    label_dir = get_label_dir()
    
    for i in range(num_users):
        user_name = f"User_{i+1}"
        start = i * chunk_size
        end = start + chunk_size
        user_imgs = images[start:end]
        
        # CHANGED: Don't check for existing labels. Start fresh so users can correct data.
        completed = []

        assignments[user_name] = {
            "images": user_imgs,
            "completed": completed
        }

    state = {
        "classes": classes,
        "assignments": assignments
    }
    save_state(state)
    
    return redirect(url_for('index'))

@app.route('/editor/<username>')
def editor(username):
    state = load_state()
    if not state or username not in state['assignments']:
        return redirect(url_for('index'))

    # Load species list for expert identification
    species_list = get_species_list()

    return render_template('editor.html', username=username, classes=state['classes'], species_list=species_list)

# --- API ENDPOINTS ---

@app.route('/api/get_image/<username>')
def get_image(username):
    state = load_state()
    user_data = state['assignments'].get(username)
    if not user_data:
        return jsonify({"error": "User not found"}), 404

    all_imgs = user_data['images']
    completed = set(user_data['completed'])
    
    index = request.args.get('index', type=int)
    
    if index is None:
        # Find first uncompleted
        for i, img in enumerate(all_imgs):
            if img not in completed:
                index = i
                break
        if index is None:
            index = len(all_imgs) - 1 if all_imgs else 0

    if not all_imgs:
        return jsonify({"done": True})
        
    index = max(0, min(index, len(all_imgs) - 1))
    target_img = all_imgs[index]

    return jsonify({
        "image": target_img,
        "index": index,
        "total": len(all_imgs),
        "progress": f"{len(completed)} / {len(all_imgs)}",
        "is_completed": target_img in completed
    })

@app.route('/api/delete_image', methods=['POST'])
def delete_image():
    data = request.json
    username = data.get('username')
    filename = data.get('filename')

    if not username or not filename:
        return jsonify({"status": "error", "message": "Missing username or filename"}), 400

    # 1. Delete image file
    img_path = os.path.join(get_image_dir(), filename)
    if os.path.exists(img_path):
        try:
            os.remove(img_path)
            print(f"Deleted image: {img_path}")
        except Exception as e:
            print(f"Error deleting image: {e}")

    # 2. Delete label file
    txt_name = os.path.splitext(filename)[0] + ".txt"
    lbl_path = os.path.join(get_label_dir(), txt_name)
    if os.path.exists(lbl_path):
        try:
            os.remove(lbl_path)
            print(f"Deleted label: {lbl_path}")
        except Exception as e:
            print(f"Error deleting label: {e}")

    # 3. Update state
    state = load_state()
    if username in state['assignments']:
        user_data = state['assignments'][username]
        if filename in user_data['images']:
            user_data['images'].remove(filename)
        if filename in user_data['completed']:
            user_data['completed'].remove(filename)
        save_state(state)

    return jsonify({"status": "success"})


@app.route('/api/image_data/<filename>')
def get_image_data(filename):
    txt_name = os.path.splitext(filename)[0] + ".txt"
    path = os.path.join(get_label_dir(), txt_name)
    labels = []

    if os.path.exists(path):
        with open(path, 'r') as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) >= 5:
                    label = {
                        "class_id": int(parts[0]),
                        "x": float(parts[1]),
                        "y": float(parts[2]),
                        "w": float(parts[3]),
                        "h": float(parts[4])
                    }
                    # Check if species code exists (6th field)
                    if len(parts) >= 6:
                        label["species"] = parts[5]
                    labels.append(label)
    return jsonify(labels)

@app.route('/images/<path:filename>')
def serve_image(filename):
    # Serve from the detected image directory
    img_dir = get_image_dir()
    print(f"[SERVE_IMAGE] Requested: {filename}")
    print(f"[SERVE_IMAGE] Serving from: {img_dir}")
    print(f"[SERVE_IMAGE] Full path: {os.path.join(img_dir, filename)}")
    print(f"[SERVE_IMAGE] File exists: {os.path.exists(os.path.join(img_dir, filename))}")

    # Use absolute path
    img_dir_abs = os.path.abspath(img_dir)
    print(f"[SERVE_IMAGE] Absolute path: {img_dir_abs}")

    return send_from_directory(img_dir_abs, filename)

@app.route('/api/save', methods=['POST'])
def save_labels():
    data = request.json
    username = data.get('username')
    filename = data.get('filename')
    labels = data.get('labels')

    txt_name = os.path.splitext(filename)[0] + ".txt"

    # Ensure label dir exists
    label_dir = get_label_dir()
    if not os.path.exists(label_dir):
        os.makedirs(label_dir, exist_ok=True)

    txt_path = os.path.join(label_dir, txt_name)

    with open(txt_path, 'w') as f:
        for l in labels:
            # Extended YOLO format: class_id x y w h species_code (optional)
            line = f"{l['class_id']} {l['x']:.6f} {l['y']:.6f} {l['w']:.6f} {l['h']:.6f}"
            if 'species' in l and l['species']:
                line += f" {l['species']}"
            line += "\n"
            f.write(line)

    state = load_state()
    if filename not in state['assignments'][username]['completed']:
        state['assignments'][username]['completed'].append(filename)
        save_state(state)

    return jsonify({"status": "success"})

@app.route('/api/rename_user', methods=['POST'])
def rename_user():
    data = request.json
    old_name = data.get('old_name')
    new_name = data.get('new_name')
    
    if not new_name or not new_name.strip():
         return jsonify({"status": "error", "message": "Invalid name"}), 400

    new_name = new_name.strip()
    
    state = load_state()
    if not state or old_name not in state['assignments']:
        return jsonify({"status": "error", "message": "User not found"}), 404
        
    if new_name in state['assignments']:
        return jsonify({"status": "error", "message": "Name already taken"}), 400
        
    # Rename the key in the dictionary
    state['assignments'][new_name] = state['assignments'].pop(old_name)
    save_state(state)
    
    return jsonify({"status": "success", "new_name": new_name})

@app.route('/api/add_class', methods=['POST'])
def add_class():
    new_class = request.json.get('name')
    state = load_state()
    if new_class and new_class not in state['classes']:
        state['classes'].append(new_class)
        save_state(state)

        with open(os.path.join(Config.DATASET_PATH, Config.CLASSES_FILE), 'w') as f:
            f.write('\n'.join(state['classes']))

        return jsonify({"status": "success", "id": len(state['classes'])-1})
    return jsonify({"status": "exists"})

@app.route('/api/species', methods=['GET'])
def get_species():
    """
    Get all bird species from database.

    This endpoint returns the complete list of bird species loaded from
    the tblSpeciesCodes table. Species are cached in memory on startup,
    so this endpoint is very fast.

    Returns:
        JSON response with species list and count:
        {
            "species": [
                {"code": "AMAV", "name": "American Avocet"},
                {"code": "AMOY", "name": "American Oystercatcher"},
                ...
            ],
            "count": 73
        }
    """
    try:
        service = get_species_service()
        species_list = service.get_all_species()

        return jsonify({
            "species": species_list,
            "count": len(species_list)
        })

    except Exception as e:
        print(f"ERROR in /api/species: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "status": "error",
            "message": str(e),
            "species": [],
            "count": 0
        }), 500

@app.route('/api/species/<species_code>/references', methods=['GET'])
def get_species_references(species_code):
    """
    Get reference images and links for a specific species.

    Returns:
        JSON with reference photos URLs, eBird link, and field guide link:
        {
            "name": "Brown Pelican",
            "photos": ["url1", "url2", "url3"],
            "ebird": "https://ebird.org/species/brnpel",
            "guide": "https://www.allaboutbirds.org/guide/Brown_Pelican"
        }
    """
    try:
        # Use complete reference images database with ALL 41 species
        from labeller.services.reference_images_complete import get_reference_images
        references = get_reference_images(species_code.upper())
        return jsonify(references)
    except Exception as e:
        print(f"ERROR in /api/species/{species_code}/references: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "name": species_code,
            "photos": [],
            "ebird": "https://ebird.org/explore",
            "guide": "https://www.allaboutbirds.org"
        }), 500

# ============================================================================
# NESTVISION CORRECTION ENDPOINTS
# ============================================================================

CROPS_DIR = "labeller/nestvision/crops"

def ensure_crops_dir():
    """Ensure crops directory exists"""
    os.makedirs(CROPS_DIR, exist_ok=True)

@app.route('/api/correction/upload', methods=['POST'])
def upload_correction_image():
    """Upload image and detections for correction - integrates with existing labeller"""
    try:
        data = request.json
        image_data = data.get('image_base64')
        detections = data.get('detections', [])

        # Decode and save image
        import base64
        image_bytes = base64.b64decode(image_data)

        # Generate unique filename with timestamp
        timestamp = int(time.time() * 1000)
        image_filename = f"correction_{timestamp}.jpg"

        # Save to nestvision/images (same as regular labelling)
        img_dir = get_image_dir()
        label_dir = get_label_dir()

        # Ensure directories exist
        os.makedirs(img_dir, exist_ok=True)
        os.makedirs(label_dir, exist_ok=True)

        img_path = os.path.join(img_dir, image_filename)

        print(f"[CORRECTION] DATASET_PATH: {Config.DATASET_PATH}")
        print(f"[CORRECTION] img_dir: {img_dir}")
        print(f"[CORRECTION] label_dir: {label_dir}")
        print(f"[CORRECTION] Saving image to: {img_path}")

        with open(img_path, 'wb') as f:
            f.write(image_bytes)

        print(f"[CORRECTION] Image saved successfully. Size: {len(image_bytes)} bytes")

        # Save initial detections as labels (YOLO format)
        txt_filename = os.path.splitext(image_filename)[0] + ".txt"
        labels_path = os.path.join(label_dir, txt_filename)

        # Get image dimensions
        img = cv2.imdecode(np.frombuffer(image_bytes, np.uint8), cv2.IMREAD_COLOR)
        if img is None:
            print(f"[CORRECTION] ERROR: Could not decode image!")
            return jsonify({"status": "error", "message": "Could not decode image"}), 500

        img_h, img_w = img.shape[:2]
        print(f"[CORRECTION] Image dimensions: {img_w}x{img_h}")

        with open(labels_path, 'w') as f:
            for det in detections:
                bbox = det.get('bbox', [])
                if len(bbox) == 4:
                    # Convert from [x1, y1, x2, y2] to YOLO format [class_id, x_center, y_center, width, height]
                    x1, y1, x2, y2 = bbox
                    x_center = (x1 + x2) / 2 / img_w
                    y_center = (y1 + y2) / 2 / img_h
                    width = (x2 - x1) / img_w
                    height = (y2 - y1) / img_h

                    # Use class_id 0 for now (will be corrected by user)
                    f.write(f"0 {x_center:.6f} {y_center:.6f} {width:.6f} {height:.6f}\n")

        print(f"[CORRECTION] Labels saved: {len(detections)} detections")

        # Load or create project state
        state = load_state()

        if not state:
            # Create initial state if it doesn't exist
            classes = get_classes()
            if not classes:
                classes = ["bird"]

            state = {
                "classes": classes,
                "assignments": {
                    "Corrections": {
                        "images": [image_filename],
                        "completed": []
                    }
                }
            }
        else:
            # Add to Corrections user or create if doesn't exist
            if "Corrections" not in state['assignments']:
                state['assignments']['Corrections'] = {
                    "images": [],
                    "completed": []
                }

            # Add image to corrections user's assignment
            if image_filename not in state['assignments']['Corrections']['images']:
                state['assignments']['Corrections']['images'].append(image_filename)

        # Save updated state
        save_state(state)

        print(f"[CORRECTION] Added to project state for user 'Corrections'")

        # Return URL to existing labeller editor
        return jsonify({
            "status": "success",
            "image_filename": image_filename,
            "correction_url": f"/editor/Corrections"
        })

    except Exception as e:
        print(f"[CORRECTION] ERROR: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/crop/save', methods=['POST'])
def save_crop():
    """Save a species-identified crop"""
    ensure_crops_dir()

    try:
        data = request.json
        crop_base64 = data.get('crop_base64')
        species_code = data.get('species_code')
        species_name = data.get('species_name', species_code)

        if not crop_base64 or not species_code:
            return jsonify({"status": "error", "message": "Missing crop data or species"}), 400

        # Decode crop image
        import base64
        crop_bytes = base64.b64decode(crop_base64)

        # Generate unique filename
        timestamp = int(time.time() * 1000)
        safe_species = species_name.replace(' ', '_').replace('/', '_')
        crop_filename = f"{safe_species}_{timestamp}.jpg"
        crop_path = os.path.join(CROPS_DIR, crop_filename)

        # Save crop
        with open(crop_path, 'wb') as f:
            f.write(crop_bytes)

        return jsonify({
            "status": "success",
            "filename": crop_filename,
            "path": crop_path
        })

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

def load_mobilesam_model():
    """Lazy load MobileSAM model from ultralytics on first use"""
    global MOBILESAM_MODEL

    if MOBILESAM_MODEL is None:
        try:
            from ultralytics import SAM

            print(f"Loading MobileSAM model...")

            # Load MobileSAM - ultralytics will download if not present
            # MobileSAM is optimized for speed and efficiency
            MOBILESAM_MODEL = SAM(MOBILESAM_MODEL_NAME)

            # Get device info
            device = 'cuda' if torch.cuda.is_available() else 'cpu'

            # Enable half precision (FP16) for faster inference on GPU
            if torch.cuda.is_available() and USE_HALF_PRECISION:
                try:
                    # Ultralytics handles half precision internally with half=True parameter
                    print(f"Half precision (FP16) enabled for faster inference")
                except Exception as e:
                    print(f"Could not enable half precision: {e}")

            # Warmup: Run a dummy inference to initialize CUDA/model
            # This ensures first real inference is fast
            if torch.cuda.is_available():
                print(f"Warming up MobileSAM on GPU...")
                dummy_img = np.zeros((SEGMENT_IMGSZ, SEGMENT_IMGSZ, 3), dtype=np.uint8)
                try:
                    MOBILESAM_MODEL(
                        dummy_img,
                        points=[[SEGMENT_IMGSZ//2, SEGMENT_IMGSZ//2]],
                        labels=[1],
                        imgsz=SEGMENT_IMGSZ,
                        verbose=False
                    )
                    print("GPU warmup complete!")
                except Exception as e:
                    print(f"GPU warmup failed: {e}, continuing anyway...")

            print(f"MobileSAM loaded successfully on {device.upper()}!")
            print(f"Image size: {SEGMENT_IMGSZ}x{SEGMENT_IMGSZ}")
            print(f"Segmentation confidence threshold: {SEGMENT_CONF_THRESHOLD}")

        except Exception as e:
            print(f"Failed to load MobileSAM model: {e}")
            import traceback
            traceback.print_exc()
            raise

    return MOBILESAM_MODEL

@app.route('/api/sam_status', methods=['GET'])
def sam_status():
    """Returns segmentation model status and device info (now using MobileSAM)"""
    try:
        model = load_mobilesam_model()
        device = 'cuda' if torch.cuda.is_available() else 'cpu'
        return jsonify({
            "status": "ready",
            "device": device,
            "model": "MobileSAM (Ultralytics)",
            "model_name": MOBILESAM_MODEL_NAME,
            "confidence_threshold": SEGMENT_CONF_THRESHOLD,
            "image_size": SEGMENT_IMGSZ,
            "half_precision": USE_HALF_PRECISION and torch.cuda.is_available(),
            "gpu_available": torch.cuda.is_available(),
            "gpu_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
            "optimizations": {
                "low_resolution": True,
                "image_caching": True,
                "fast_mask_processing": True,
                "fp16": USE_HALF_PRECISION and torch.cuda.is_available()
            }
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/sam_segment', methods=['POST'])
def sam_segment():
    """
    Accepts a single point click {x, y} in normalized 0-1, point_index, mode ('fast' or 'zoom'), and image filename.
    Returns a bounding box from MobileSAM segmentation of the clicked object.
    NOW USING: MobileSAM from ultralytics for fast, accurate segmentation.
    OPTIMIZED: Lower resolution, caching, and FP16 for sub-second inference.
    Supports Zoom mode for better small object detection with higher resolution.
    """
    try:
        import time

        data = request.json
        filename = data.get('filename')
        point_data = data.get('point')
        point_index = data.get('point_index', 0)
        detection_mode = data.get('mode', 'fast')  # 'fast' or 'zoom'

        if not point_data:
            return jsonify({"status": "error", "message": "No point provided"}), 400

        # Get image path
        img_path = os.path.join(get_image_dir(), filename)

        # Check cache to avoid reloading same image
        global IMAGE_CACHE
        current_time = time.time()

        # Clear cache if expired
        if IMAGE_CACHE["filename"] and IMAGE_CACHE["timestamp"]:
            if current_time - IMAGE_CACHE["timestamp"] > CACHE_TIMEOUT:
                IMAGE_CACHE = {"filename": None, "preprocessed_image": None, "timestamp": None}

        # Load or use cached image dimensions
        if IMAGE_CACHE["filename"] != filename:
            image = cv2.imread(img_path)
            if image is None:
                return jsonify({"status": "error", "message": "Image not found"}), 404
            h, w = image.shape[:2]
            IMAGE_CACHE["filename"] = filename
            IMAGE_CACHE["preprocessed_image"] = (h, w)
            IMAGE_CACHE["timestamp"] = current_time
        else:
            h, w = IMAGE_CACHE["preprocessed_image"]

        # Convert normalized to pixel coordinates
        click_x = int(float(point_data['x']) * w)
        click_y = int(float(point_data['y']) * h)

        print(f"MobileSAM point {point_index}: [{click_x}, {click_y}] on {w}x{h} (mode: {detection_mode})")

        # Load MobileSAM model
        model = load_mobilesam_model()

        # Configure parameters based on detection mode
        if detection_mode == 'zoom':
            # Zoom mode: Higher resolution for better small object detection
            imgsz = 1024  # Higher resolution
            retina_masks = True  # Better quality masks
            conf_threshold = 0.3  # Lower threshold for small objects
            print(f"  → Using Zoom mode: imgsz={imgsz}, retina_masks=True, conf={conf_threshold}")
        else:
            # Fast mode: Optimized for speed
            imgsz = SEGMENT_IMGSZ  # 720 for speed
            retina_masks = False  # Faster
            conf_threshold = SEGMENT_CONF_THRESHOLD
            print(f"  → Using Fast mode: imgsz={imgsz}, retina_masks=False, conf={conf_threshold}")

        # Use lock to prevent concurrent inference (prevents GPU stalling)
        # Only one inference at a time ensures stable, fast performance
        with INFERENCE_LOCK:
            # Run MobileSAM with selected mode parameters
            start = time.time()

            inference_params = {
                "source": img_path,
                "points": [[click_x, click_y]],
                "labels": [1],  # 1 = foreground point
                "imgsz": imgsz,
                "retina_masks": retina_masks,
                "conf": conf_threshold,
                "verbose": False,
                "stream": False  # Don't stream, return immediately
            }

            # Add half precision for GPU
            if torch.cuda.is_available() and USE_HALF_PRECISION:
                inference_params["half"] = True

            results = model(**inference_params)
            elapsed = time.time() - start
            print(f"  → Inference: {elapsed:.3f}s")

            # Quick validation
            if not results or len(results) == 0:
                return jsonify({"status": "error", "message": "No segmentation generated"}), 404

            result = results[0]

            if result.masks is None or len(result.masks) == 0:
                return jsonify({"status": "error", "message": "No object segmented at clicked point"}), 404

            # Intelligent mask processing and selection
            mask_start = time.time()

            # Get image area for size validation
            image_area = h * w
            max_area = image_area * MAX_SEGMENT_AREA_RATIO

            print(f"  → Processing {len(result.masks)} mask(s)...")

            # Try all masks and find the best one (smallest that contains the point)
            valid_masks = []

            for i, mask_obj in enumerate(result.masks):
                mask = mask_obj.data[0].cpu().numpy()
                mask_h, mask_w = mask.shape
                mask_binary = (mask > 0.5).astype(np.uint8)

                # Calculate mask area
                mask_area = np.sum(mask_binary)

                # Skip if mask is too large (likely whole image or wrong segmentation)
                if mask_area > max_area:
                    print(f"    Mask {i}: TOO LARGE ({mask_area/image_area:.1%} of image), skipping")
                    continue

                # Skip if mask is too small (noise)
                if mask_area < MIN_SEGMENT_AREA:
                    print(f"    Mask {i}: Too small ({mask_area} pixels), skipping")
                    continue

                # Get bounding box
                rows = np.any(mask_binary, axis=1)
                cols = np.any(mask_binary, axis=0)

                if not rows.any() or not cols.any():
                    continue

                ymin_m, ymax_m = np.where(rows)[0][[0, -1]]
                xmin_m, xmax_m = np.where(cols)[0][[0, -1]]

                # Scale coordinates from mask size to original image size
                scale_x = w / mask_w
                scale_y = h / mask_h

                xmin_img = int(xmin_m * scale_x)
                xmax_img = int(xmax_m * scale_x)
                ymin_img = int(ymin_m * scale_y)
                ymax_img = int(ymax_m * scale_y)

                # Check if clicked point is inside this mask's bbox
                if not (xmin_img <= click_x <= xmax_img and ymin_img <= click_y <= ymax_img):
                    print(f"    Mask {i}: Click point outside bbox, skipping")
                    continue

                # Check if clicked point is actually in the mask (not just bbox)
                # Scale click point to mask coordinates
                click_x_mask = int(click_x / scale_x)
                click_y_mask = int(click_y / scale_y)

                # Clamp to mask bounds
                click_x_mask = max(0, min(mask_w - 1, click_x_mask))
                click_y_mask = max(0, min(mask_h - 1, click_y_mask))

                if mask_binary[click_y_mask, click_x_mask] == 0:
                    print(f"    Mask {i}: Click point not in mask, skipping")
                    continue

                valid_masks.append({
                    "mask": mask_binary,
                    "area": mask_area,
                    "bbox": (xmin_img, ymin_img, xmax_img, ymax_img),
                    "index": i
                })

                bbox_area = (xmax_img - xmin_img) * (ymax_img - ymin_img)
                print(f"    Mask {i}: VALID! Area={mask_area} ({mask_area/image_area:.1%}), bbox_area={bbox_area}")

            if len(valid_masks) == 0:
                return jsonify({"status": "error", "message": "No valid mask found. Click directly on the bird."}), 404

            # Select the smallest valid mask (most precise for small objects)
            best_mask = min(valid_masks, key=lambda m: m["area"])
            xmin, ymin, xmax, ymax = best_mask["bbox"]

            print(f"  → Selected mask {best_mask['index']} (smallest valid)")

            # Add padding to bounding box for better coverage
            box_w = xmax - xmin
            box_h = ymax - ymin
            pad_w = int(box_w * BBOX_PADDING_RATIO)
            pad_h = int(box_h * BBOX_PADDING_RATIO)

            # Apply padding and clamp to image bounds
            xmin = max(0, xmin - pad_w)
            ymin = max(0, ymin - pad_h)
            xmax = min(w - 1, xmax + pad_w)
            ymax = min(h - 1, ymax + pad_h)

            print(f"  → Added {pad_w}px horizontal and {pad_h}px vertical padding")

            mask_time = time.time() - mask_start
            print(f"  → Mask processing: {mask_time:.3f}s")

            # Calculate normalized bbox (YOLO format) with padding applied
            box_w = xmax - xmin
            box_h = ymax - ymin
            center_x = float((xmin + box_w / 2) / w)
            center_y = float((ymin + box_h / 2) / h)
            norm_w = float(box_w / w)
            norm_h = float(box_h / h)

            total_time = time.time() - start
            print(f"  → Total: {total_time:.3f}s | bbox: [{xmin}, {ymin}, {xmax}, {ymax}]")

        return jsonify({
            "status": "success",
            "point_index": point_index,
            "box": {
                "x": center_x,
                "y": center_y,
                "w": norm_w,
                "h": norm_h
            },
            "inference_time": elapsed,
            "total_time": total_time
        })

    except Exception as e:
        print(f"MobileSAM error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/sam_auto_detect', methods=['POST'])
def sam_auto_detect():
    """
    Auto-detection is not available with MobileSAM (requires prompts).
    This endpoint is kept for compatibility but returns an informative message.
    Use point-based segmentation via /api/sam_segment instead.
    """
    return jsonify({
        "status": "info",
        "message": "Auto-detection not available with MobileSAM. Please use point-based segmentation.",
        "boxes": [],
        "count": 0
    })

# ==================== CLUSTER EXPLORER ROUTES ====================

@app.route('/clusters')
def cluster_explorer():
    """
    3D Cluster Explorer: Aerial view of bird clusters with actual images.

    View clusters from above like looking at mountain ranges.
    All bird images are loaded and visible.
    """
    return render_template('cluster_explorer_aerial.html')

@app.route('/clusters/fps')
def cluster_explorer_fps():
    """
    Alternative FPS-style cluster explorer (walk-through mode).
    """
    return render_template('cluster_explorer_fps.html')

@app.route('/clusters/orbit')
def cluster_explorer_orbit():
    """
    Alternative orbit-based cluster explorer (Three.js with orbit controls).
    """
    return render_template('cluster_explorer_threejs.html')

@app.route('/clusters/plotly')
def cluster_explorer_plotly():
    """
    Alternative Plotly-based cluster explorer (dot-based visualization).
    """
    return render_template('cluster_explorer_3d.html')

@app.route('/api/cluster_data')
def get_cluster_data():
    """
    API endpoint to serve cluster data for visualization.

    Returns:
        JSON with cluster assignments, t-SNE positions, and metadata
    """
    clusters_file = os.path.join(Config.DATASET_PATH, "bird_crops", "clusters", "clusters_for_labeling.json")
    results_file = os.path.join(Config.DATASET_PATH, "bird_crops", "clusters", "clustering_results.pkl")

    # Check if clustering has been run
    if not os.path.exists(clusters_file):
        return jsonify({
            "error": "No cluster data found",
            "message": "Run clustering first: python scripts/cluster_birds.py --data labeller/nestvision --clusters 30"
        }), 404

    # Load cluster data
    with open(clusters_file, 'r') as f:
        cluster_data = json.load(f)

    # Load t-SNE positions if available
    positions = []
    if os.path.exists(results_file):
        import pickle
        with open(results_file, 'rb') as f:
            results = pickle.load(f)

        # Extract t-SNE positions (prefer t-SNE over PCA for visualization)
        X_proj = results.get('X_tsne', results.get('X_pca'))
        labels = results.get('labels', [])
        metadata = results.get('metadata', [])

        if X_proj and labels:
            # Detect if 2D or 3D coordinates
            is_3d = len(X_proj[0]) == 3 if len(X_proj) > 0 else False

            for i, (pos, label) in enumerate(zip(X_proj, labels)):
                meta = metadata[i] if i < len(metadata) else {}
                position = {
                    'x': float(pos[0]),
                    'y': float(pos[1]),
                    'cluster': int(label),
                    'bird_id': i,
                    'image_name': meta.get('source_image', meta.get('image_name', 'unknown')),
                    'crop_path': f'/api/bird_crop/{i}'
                }

                # Add z coordinate if 3D
                if is_3d:
                    position['z'] = float(pos[2])

                positions.append(position)

    return jsonify({
        'total_birds': cluster_data['total_birds'],
        'n_clusters': cluster_data['n_clusters'],
        'clusters': cluster_data['clusters'],
        'positions': positions
    })

@app.route('/api/bird_crop/<int:crop_id>')
def get_bird_crop(crop_id):
    """
    Serve individual bird crop images for visualization.

    Args:
        crop_id: Index of the bird crop to retrieve
    """
    # Use absolute path to avoid working directory issues
    crops_dir = os.path.abspath(os.path.join(Config.DATASET_PATH, "bird_crops", "images"))

    # Try to find the crop file
    crop_filename = f"bird_{crop_id:06d}.jpg"
    crop_path = os.path.join(crops_dir, crop_filename)

    print(f"[DEBUG] Looking for bird crop {crop_id}")
    print(f"[DEBUG] Crops dir: {crops_dir}")
    print(f"[DEBUG] Crop path: {crop_path}")
    print(f"[DEBUG] Exists: {os.path.exists(crop_path)}")

    if os.path.exists(crop_path):
        return send_from_directory(crops_dir, crop_filename)

    # If not found, return placeholder
    from flask import send_file
    from io import BytesIO

    # Generate a placeholder image
    placeholder = np.ones((100, 100, 3), dtype=np.uint8) * 50
    cv2.putText(placeholder, 'N/A', (20, 60), cv2.FONT_HERSHEY_SIMPLEX, 1, (200, 200, 200), 2)

    _, buffer = cv2.imencode('.jpg', placeholder)
    return send_file(BytesIO(buffer.tobytes()), mimetype='image/jpeg')

# ==================== END CLUSTER EXPLORER ROUTES ====================

# ==================== CLUSTERING PIPELINE ROUTES ====================

@app.route('/clustering')
def clustering_dashboard():
    """
    Clustering Dashboard: Integrated UI for running the complete pipeline.

    Provides a step-by-step interface to:
    1. Extract bird crops
    2. Generate deep learning embeddings
    3. Run clustering and t-SNE
    """
    return render_template('clustering_dashboard.html')

@app.route('/api/clustering/status')
def clustering_status():
    """Check status of clustering pipeline"""
    crops_dir = os.path.join(Config.DATASET_PATH, "bird_crops")
    clusters_dir = os.path.join(crops_dir, "clusters")

    status = {
        'crops_extracted': False,
        'embeddings_generated': False,
        'clustering_done': False
    }

    # Check crops
    if os.path.exists(os.path.join(crops_dir, "metadata.json")):
        status['crops_extracted'] = True
        with open(os.path.join(crops_dir, "metadata.json"), 'r') as f:
            meta = json.load(f)
            status['num_crops'] = meta.get('total_crops', 0)

    # Check embeddings
    if os.path.exists(os.path.join(crops_dir, "embeddings.npy")):
        status['embeddings_generated'] = True
        with open(os.path.join(crops_dir, "config.json"), 'r') as f:
            config = json.load(f)
            status['embedding_dim'] = config.get('embedding_dim', 0)

    # Check clustering
    if os.path.exists(os.path.join(clusters_dir, "clusters_for_labeling.json")):
        status['clustering_done'] = True
        with open(os.path.join(clusters_dir, "clusters_for_labeling.json"), 'r') as f:
            cluster_data = json.load(f)
            status['n_clusters'] = cluster_data.get('n_clusters', 0)
            status['total_birds'] = cluster_data.get('total_birds', 0)

    return jsonify(status)

@app.route('/api/clustering/extract_crops', methods=['POST'])
def extract_crops():
    """Extract bird crops from YOLO dataset (can take 5-10 seconds)"""
    try:
        from labeller.services.embedding_service import BirdCropManager

        crops_dir = os.path.join(Config.DATASET_PATH, "bird_crops")
        print(f"[Clustering] Starting crop extraction from {Config.DATASET_PATH}")
        print(f"[Clustering] Output directory: {crops_dir}")

        manager = BirdCropManager(crops_dir)

        # Extract crops (no resizing for better quality, with padding for context)
        # Note: This can take 5-10 seconds for ~500 images
        manager.extract_and_save_crops(
            dataset_dir=Config.DATASET_PATH,
            resize=None,  # Preserve original resolution
            min_size=20,
            max_size=10000,
            padding_percent=0.15  # Add 15% padding around birds for full context
        )

        # Load metadata to get count
        metadata_path = os.path.join(crops_dir, "metadata.json")
        print(f"[Clustering] Reading metadata from {metadata_path}")

        if not os.path.exists(metadata_path):
            raise Exception(f"Metadata file not found at {metadata_path}")

        with open(metadata_path, 'r') as f:
            meta = json.load(f)

        total_crops = meta.get('total_crops', 0)
        print(f"[Clustering] ✓ Extracted {total_crops} crops successfully")

        return jsonify({
            'status': 'success',
            'total_crops': total_crops
        })

    except Exception as e:
        import traceback
        print(f"[Clustering] ✗ Error during extraction:")
        traceback.print_exc()
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/clustering/generate_embeddings', methods=['POST'])
def generate_embeddings():
    """Generate deep learning embeddings from bird crops"""
    try:
        from labeller.services.embedding_service import BirdCropManager

        data = request.json or {}
        model_name = data.get('model_name', 'efficientnet')  # Default to EfficientNet for speed

        crops_dir = os.path.join(Config.DATASET_PATH, "bird_crops")
        manager = BirdCropManager(crops_dir)

        # Generate embeddings
        manager.generate_embeddings(model_name=model_name, batch_size=32)

        # Load config to get info
        with open(os.path.join(crops_dir, "config.json"), 'r') as f:
            config = json.load(f)

        return jsonify({
            'status': 'success',
            'embedding_dim': config['embedding_dim'],
            'num_crops': config['num_crops'],
            'model_name': config['model_name']
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/clustering/run_clustering', methods=['POST'])
def run_clustering():
    """Run clustering on embeddings and generate 3D visualization"""
    try:
        from labeller.services.clustering_service import ClusteringService

        data = request.json or {}
        method = data.get('method', 'kmeans')
        n_clusters = data.get('n_clusters', 30)

        print(f"[Clustering] Running clustering with method={method}, n_clusters={n_clusters}")

        crops_dir = os.path.join(Config.DATASET_PATH, "bird_crops")
        service = ClusteringService(crops_dir)

        # Run clustering with 3D visualization
        # DBSCAN determines n_clusters automatically, K-means uses the provided value
        results = service.run_clustering(n_clusters=n_clusters, method=method)

        print(f"[Clustering] ✓ Clustering complete: {results['n_clusters']} clusters found")

        return jsonify({
            'status': 'success',
            **results
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

# ==================== END CLUSTERING PIPELINE ROUTES ====================

# ==================== SPECIES LABELING ROUTES ====================

@app.route('/classify')
def species_classification_interface():
    """
    Redirect to tree-based classification interface.
    Grid view has been removed - tree view is now the only classification method.
    """
    return redirect(url_for('species_classification_tree'))

@app.route('/classify-tree')
def species_classification_tree():
    """
    Decision Tree-Based Species Classification Interface.

    Uses hierarchical decision tree (Size → Color → Species) for accurate
    bird identification. Shows full original aerial images instead of crops,
    with birds highlighted by bounding boxes.

    This method addresses the low-resolution crop problem and provides
    systematic identification workflow based on ornithological research.
    """
    return render_template('species_classification_tree.html')

@app.route('/classify-akinator')
def classify_akinator():
    """
    Akinator-Style Classification Interface.

    Smart question-based identification using probabilistic feature matching.
    Shows full images with bounding boxes and asks progressive questions
    to narrow down species systematically.
    """
    return render_template('species_classification_akinator.html')

@app.route('/diagnostic')
def diagnostic_page():
    """
    Diagnostic page for testing image loading and API endpoints.

    Helps troubleshoot issues with image display, cluster data, and API responses.
    Access at: http://localhost:5000/diagnostic
    """
    return render_template('diagnostic.html')

@app.route('/test-images')
def test_reference_images():
    """
    Test page for reference image loading through proxy.
    Access at: http://localhost:5000/test-images
    """
    return send_from_directory('.', 'test_reference_images.html')

@app.route('/debug-gallery')
def debug_gallery():
    """
    Debug page for gallery image loading - comprehensive test.
    Access at: http://localhost:5000/debug-gallery
    """
    return render_template('debug_gallery.html')

@app.route('/api/original_image/<path:image_name>')
def get_original_image(image_name):
    """
    Serve full original aerial images for classification.

    Instead of serving low-res crops, this serves the full high-res image
    so experts can see bird details clearly. The frontend highlights the
    bird's bounding box on the full image.

    Args:
        image_name: Name of the image file (e.g., "29May2012Cam1Card3 227_x1024_y0")
                   Extension (.jpg) is added automatically if not present

    Returns:
        Full resolution image file
    """
    image_dir = get_image_dir()

    # Add .jpg extension if not present
    if not image_name.endswith('.jpg'):
        image_name = image_name + '.jpg'

    # Security: ensure the path doesn't escape the image directory
    safe_path = os.path.join(image_dir, os.path.basename(image_name))

    if not os.path.exists(safe_path):
        return jsonify({
            'status': 'error',
            'message': f'Image not found: {image_name}'
        }), 404

    return send_from_directory(image_dir, os.path.basename(image_name))

@app.route('/static/bird_classification_tree.json')
def get_decision_tree():
    """
    Serve the ornithological decision tree JSON.

    Returns the hierarchical classification tree with species data,
    key features, confidence tips, and identification guidance.
    """
    tree_path = os.path.join(os.path.dirname(__file__), 'bird_classification_tree.json')

    if not os.path.exists(tree_path):
        return jsonify({
            'status': 'error',
            'message': 'Decision tree file not found'
        }), 404

    with open(tree_path, 'r') as f:
        tree_data = json.load(f)

    return jsonify(tree_data)

@app.route('/api/labeling/progress')
def get_labeling_progress():
    """Get overall labeling progress across all clusters"""
    try:
        from labeller.services.labeling_service import LabelingService

        service = LabelingService(Config.DATASET_PATH)
        progress = service.get_overall_progress()

        return jsonify({
            'status': 'success',
            **progress
        })

    except FileNotFoundError as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 404
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/labeling/cluster/<int:cluster_id>/info')
def get_cluster_labeling_info(cluster_id):
    """Get detailed info about a cluster for labeling"""
    try:
        from labeller.services.labeling_service import LabelingService

        service = LabelingService(Config.DATASET_PATH)
        info = service.get_cluster_info(str(cluster_id))

        if info is None:
            return jsonify({
                'status': 'error',
                'message': f'Cluster {cluster_id} not found'
            }), 404

        return jsonify({
            'status': 'success',
            **info
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/labeling/cluster/<int:cluster_id>/next')
def get_next_bird_to_label(cluster_id):
    """Get next unlabeled bird in a cluster"""
    try:
        from labeller.services.labeling_service import LabelingService

        service = LabelingService(Config.DATASET_PATH)
        bird_data = service.get_next_unlabeled_bird(str(cluster_id))

        if bird_data is None:
            return jsonify({
                'status': 'success',
                'completed': True,
                'message': 'All birds in this cluster are labeled!'
            })

        return jsonify({
            'status': 'success',
            'completed': False,
            **bird_data
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/labeling/bird/<bird_id>/label', methods=['POST'])
def save_bird_label(bird_id):
    """Save species label for a bird"""
    try:
        from labeller.services.labeling_service import LabelingService

        data = request.json or {}
        species = data.get('species')
        confidence = data.get('confidence', 'high')
        cluster_id = data.get('cluster_id')

        if not species:
            return jsonify({
                'status': 'error',
                'message': 'Species code is required'
            }), 400

        service = LabelingService(Config.DATASET_PATH)
        label_data = service.save_label(bird_id, species, confidence, cluster_id)

        # Get updated progress
        progress = service.get_overall_progress()

        return jsonify({
            'status': 'success',
            'label': label_data,
            'progress': progress
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/labeling/cluster/<int:cluster_id>/outliers')
def get_cluster_outliers(cluster_id):
    """Detect potentially mislabeled birds in a cluster"""
    try:
        from labeller.services.labeling_service import LabelingService

        service = LabelingService(Config.DATASET_PATH)
        outliers = service.detect_outliers(str(cluster_id))

        return jsonify({
            'status': 'success',
            'outliers': outliers,
            'count': len(outliers)
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/species/list')
def list_species():
    """Get all species with codes and names"""
    try:
        species_service = get_species_service()
        species_list = species_service.get_all_species()

        return jsonify({
            'status': 'success',
            'species': species_list,
            'count': len(species_list)
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

# ==================== AKINATOR-STYLE IDENTIFICATION ROUTES ====================

# Global Akinator engine instances (one per session)
# In production, use Redis or session management
akinator_sessions = {}

@app.route('/api/akinator/start', methods=['POST'])
def start_akinator_session():
    """
    Start a new Akinator-style identification session.

    Request body:
    {
        "bird_id": 123,
        "cluster_id": 5  // optional, for species filtering
    }

    Returns session_id and first question
    """
    try:
        from labeller.services.akinator_engine import AkinatorEngine
        import uuid

        data = request.get_json()
        bird_id = data.get('bird_id')
        cluster_id = data.get('cluster_id')

        # Create new session
        session_id = str(uuid.uuid4())

        # Initialize Akinator engine with comprehensive species database
        species_db_path = os.path.join(Config.DATASET_PATH, "..", "data", "species_feature_profiles_FULL.json")
        engine = AkinatorEngine(species_db_path)

        # Start session (optionally filter by cluster)
        available_species = None
        if cluster_id is not None:
            # Get suggested species for this cluster
            labeling_service = get_labeling_service()
            cluster_info = labeling_service.get_cluster_info(str(cluster_id))
            suggested = cluster_info.get('suggested_species', [])
            if suggested:
                available_species = suggested

        engine.start_session(available_species)

        # Store in memory (use Redis in production)
        akinator_sessions[session_id] = {
            'engine': engine,
            'bird_id': bird_id,
            'cluster_id': cluster_id,
            'started_at': time.time()
        }

        # Get first question
        question = engine.get_next_question()

        # Include initial candidate gallery
        initial_candidates = engine.get_top_candidates(n=8)

        return jsonify({
            'status': 'success',
            'session_id': session_id,
            'question': question,
            'candidates': initial_candidates  # For live gallery
        })

    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@app.route('/api/akinator/answer', methods=['POST'])
def answer_akinator_question():
    """
    Answer a question and get the next one.

    Request body:
    {
        "session_id": "uuid",
        "feature": "color_white",
        "value": 0.9,
        "additional_features": {"color_black": 0.1}  // optional
    }

    Returns next question or final candidates
    """
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        feature = data.get('feature')
        value = data.get('value')
        additional_features = data.get('additional_features', {})

        # Get session
        if session_id not in akinator_sessions:
            return jsonify({
                'status': 'error',
                'message': 'Session not found or expired'
            }), 404

        session = akinator_sessions[session_id]
        engine = session['engine']

        # Record answer
        engine.answer_question(feature, value, additional_features)

        # Check if we should show results
        if engine.should_show_results():
            candidates = engine.get_top_candidates(n=5)
            return jsonify({
                'status': 'success',
                'show_results': True,
                'candidates': candidates,
                'questions_asked': len(engine.session_state['questions_asked'])
            })

        # Get next question
        question = engine.get_next_question()

        if question is None:
            # No more questions, show results
            candidates = engine.get_top_candidates(n=5)
            return jsonify({
                'status': 'success',
                'show_results': True,
                'candidates': candidates,
                'questions_asked': len(engine.session_state['questions_asked'])
            })

        # ALWAYS include top candidates for live gallery (even during questioning)
        top_candidates = engine.get_top_candidates(n=8)

        return jsonify({
            'status': 'success',
            'show_results': False,
            'question': question,
            'questions_asked': len(engine.session_state['questions_asked']),
            'candidates': top_candidates  # Live gallery data
        })

    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@app.route('/api/akinator/finalize', methods=['POST'])
def finalize_akinator_identification():
    """
    Finalize identification and save the label.

    Request body:
    {
        "session_id": "uuid",
        "species_code": "BRPE",
        "confidence": "high"
    }
    """
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        species_code = data.get('species_code')
        confidence = data.get('confidence', 'high')

        # Get session
        if session_id not in akinator_sessions:
            return jsonify({
                'status': 'error',
                'message': 'Session not found'
            }), 404

        session = akinator_sessions[session_id]
        bird_id = session['bird_id']
        cluster_id = session['cluster_id']

        # Save label using labeling service
        labeling_service = get_labeling_service()
        label_data = labeling_service.save_label(
            str(bird_id),
            species_code,
            confidence,
            cluster_id
        )

        # Get updated progress
        progress = labeling_service.get_overall_progress()

        # Clean up session
        del akinator_sessions[session_id]

        return jsonify({
            'status': 'success',
            'label': label_data,
            'progress': progress
        })

    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@app.route('/api/reference_image_proxy')
def reference_image_proxy():
    """
    Proxy endpoint to fetch reference images from Macaulay Library CDN.

    This avoids CORS issues by fetching images on the backend and serving
    them through Flask with proper headers.

    Usage: /api/reference_image_proxy?url=<encoded_url>
    """
    import requests
    from urllib.parse import unquote

    try:
        # Get the image URL from query parameter
        image_url = request.args.get('url')
        if not image_url:
            return jsonify({'error': 'No URL provided'}), 400

        # Decode URL if needed
        image_url = unquote(image_url)

        # Only allow Macaulay Library CDN URLs for security
        if not image_url.startswith('https://cdn.download.ams.birds.cornell.edu/'):
            return jsonify({'error': 'Invalid image source'}), 403

        # Fetch the image from CDN
        response = requests.get(image_url, timeout=10)
        response.raise_for_status()

        # Return image with proper headers
        return Response(
            response.content,
            mimetype=response.headers.get('content-type', 'image/jpeg'),
            headers={
                'Cache-Control': 'public, max-age=86400',  # Cache for 24 hours
                'Access-Control-Allow-Origin': '*'
            }
        )

    except requests.RequestException as e:
        return jsonify({'error': f'Failed to fetch image: {str(e)}'}), 502
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/bird/full_image/<bird_id>')
def get_bird_full_image_with_bbox(bird_id):
    """
    Get full image with bounding box overlay for a bird.

    Returns image with highlighted bbox around the specified bird.
    """
    try:
        # Get bird metadata
        labeling_service = get_labeling_service()
        metadata = labeling_service.bird_metadata.get(int(bird_id), {})

        if not metadata:
            return jsonify({'error': 'Bird not found'}), 404

        # Try both 'source_image' (from metadata) and 'image_name' (from labeling service)
        image_name = metadata.get('source_image') or metadata.get('image_name')
        bbox_yolo = metadata.get('bbox_yolo')  # [x_center, y_center, width, height] normalized

        if not image_name or not bbox_yolo:
            print(f"[FULL_IMAGE] ERROR: Missing data for bird {bird_id}")
            print(f"[FULL_IMAGE] image_name: {image_name}, bbox_yolo: {bbox_yolo}")
            return jsonify({'error': 'Missing image or bbox data'}), 404

        # Load FULL ORIGINAL image from main dataset (not crops!)
        images_dir = get_image_dir()  # This gets the actual original images directory

        # Add .jpg extension if not present
        if not image_name.endswith('.jpg'):
            image_name = image_name + '.jpg'

        image_path = os.path.join(images_dir, image_name)

        print(f"[FULL_IMAGE] Looking for: {image_name}")
        print(f"[FULL_IMAGE] Images dir: {images_dir}")
        print(f"[FULL_IMAGE] Full path: {image_path}")
        print(f"[FULL_IMAGE] Exists: {os.path.exists(image_path)}")

        if not os.path.exists(image_path):
            return jsonify({'error': f'Image file not found: {image_name}'}), 404

        # Read image
        img = cv2.imread(image_path)
        if img is None:
            return jsonify({'error': 'Failed to load image'}), 500

        height, width = img.shape[:2]
        print(f"[FULL_IMAGE] Image size: {width}x{height}")

        # Convert YOLO bbox to pixel coordinates
        x_center_norm, y_center_norm, w_norm, h_norm = bbox_yolo
        x_center = int(x_center_norm * width)
        y_center = int(y_center_norm * height)
        box_width = int(w_norm * width)
        box_height = int(h_norm * height)

        # Calculate corner coordinates
        x1 = int(x_center - box_width / 2)
        y1 = int(y_center - box_height / 2)
        x2 = int(x_center + box_width / 2)
        y2 = int(y_center + box_height / 2)

        print(f"[FULL_IMAGE] Bounding box: ({x1}, {y1}) to ({x2}, {y2})")

        # Draw bounding box (Claude orange color, thin line)
        color = (87, 119, 217)  # BGR format (Orange)
        thickness = 2  # Thin, clean line
        cv2.rectangle(img, (x1, y1), (x2, y2), color, thickness)

        # NO TEXT - just the box!

        # Encode as JPEG
        _, buffer = cv2.imencode('.jpg', img, [cv2.IMWRITE_JPEG_QUALITY, 92])

        from flask import Response
        return Response(buffer.tobytes(), mimetype='image/jpeg')

    except Exception as e:
        print(f"[FULL_IMAGE] ERROR: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ==================== END SPECIES LABELING ROUTES ====================

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--data', type=str, default='nestvision', help='Path to dataset')
    args = parser.parse_args()

    # Update Config from command line argument
    Config.DATASET_PATH = args.data

    # Update STATE_FILE to be in the parent directory of DATASET_PATH
    # So if DATASET_PATH is "labeller/nestvision", STATE_FILE should be "labeller/project_state.json"
    dataset_parent = os.path.dirname(Config.DATASET_PATH) if os.path.dirname(Config.DATASET_PATH) else "."
    Config.STATE_FILE = os.path.join(dataset_parent, "project_state.json")

    print(f"Starting Nestperts on {Config.DATASET_PATH}")
    print(f"State file: {Config.STATE_FILE}")
    print(f"Images directory: {get_image_dir()}")
    print(f"Labels directory: {get_label_dir()}")
    app.run(host='0.0.0.0', port=5000, debug=True)