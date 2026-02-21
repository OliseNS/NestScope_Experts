import os
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
from flask import Flask, render_template, request, jsonify, send_from_directory, redirect, url_for

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
    """Load species codes and names from CSV file for expert identification"""
    species_csv = os.path.join("..", "CSV_Files", "tblSpeciesCodes.csv")
    species_list = []

    if os.path.exists(species_csv):
        try:
            with open(species_csv, 'r') as f:
                # Skip header
                next(f)
                for line in f:
                    # Parse CSV line (handle quoted strings)
                    parts = line.strip().split(',')
                    if len(parts) >= 2:
                        code = parts[0].strip('"')
                        name = parts[1].strip('"')
                        if code and name:
                            species_list.append({"code": code, "name": name})
        except Exception as e:
            print(f"Warning: Could not load species list: {e}")
    else:
        print(f"Warning: Species CSV not found at {species_csv}")

    return species_list

@app.route('/')
def index():
    state = load_state()
    if not state:
        return render_template('index.html', setup_needed=True)
    
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
    
    return render_template('index.html', setup_needed=False, users=users_progress)

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