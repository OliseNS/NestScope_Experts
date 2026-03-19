"""
LuckyCharm Demo Server - Gong-powered bird detection showcase

A fun, interactive demo showing processing speed with a gong interface.
"""

from flask import Flask, render_template, jsonify, send_from_directory
from pathlib import Path
import time
import base64
import cv2
import threading
import json
from datetime import datetime
from inference_engine import FastBirdDetector, draw_detections

app = Flask(__name__)

# Global state
detector = None
processing_state = {
    'active': False,
    'current_image': 0,
    'total_images': 0,
    'processed_images': [],
    'start_time': None,
    'total_birds': 0,
    'total_time': 0
}
processing_lock = threading.Lock()

# Paths
BASE_DIR = Path(__file__).parent
IMAGES_DIR = BASE_DIR / 'demoday_images'
DETECTOR_PATH = BASE_DIR / 'swift_UQ.onnx'
CLASSIFIER_PATH = BASE_DIR / 'classifier_swift.onnx'


def initialize_detector():
    """Initialize the detector on startup"""
    global detector
    try:
        print("🚀 Initializing LuckyCharm detector...")
        detector = FastBirdDetector(
            detector_path=str(DETECTOR_PATH),
            classifier_path=str(CLASSIFIER_PATH),
            conf_threshold=0.25,
            iou_threshold=0.45
        )
        print("✅ Detector ready!")
    except Exception as e:
        print(f"❌ Failed to initialize detector: {e}")
        detector = None


def process_images_worker():
    """Background worker to process images"""
    global processing_state

    # Get list of images
    image_files = sorted(IMAGES_DIR.glob('*.jpg')) + sorted(IMAGES_DIR.glob('*.JPG')) + \
                  sorted(IMAGES_DIR.glob('*.png')) + sorted(IMAGES_DIR.glob('*.PNG'))

    with processing_lock:
        processing_state['total_images'] = len(image_files)
        processing_state['processed_images'] = []
        processing_state['current_image'] = 0
        processing_state['total_birds'] = 0
        processing_state['total_time'] = 0

    for idx, image_path in enumerate(image_files):
        # Check if still active
        with processing_lock:
            if not processing_state['active']:
                break
            processing_state['current_image'] = idx + 1

        try:
            # Run detection and classification
            result = detector.detect_and_classify(str(image_path), sahi_slices=2)

            # Read and annotate image
            image = cv2.imread(str(image_path))
            if image is not None and 'detections' in result:
                annotated = draw_detections(image, result['detections'])

                # Resize for web display (max 800px width)
                h, w = annotated.shape[:2]
                if w > 800:
                    scale = 800 / w
                    new_w, new_h = int(w * scale), int(h * scale)
                    annotated = cv2.resize(annotated, (new_w, new_h))

                # Encode to base64
                _, buffer = cv2.imencode('.jpg', annotated, [cv2.IMWRITE_JPEG_QUALITY, 85])
                img_base64 = base64.b64encode(buffer).decode('utf-8')

                # Update state
                with processing_lock:
                    processing_state['processed_images'].append({
                        'filename': image_path.name,
                        'bird_count': result['bird_count'],
                        'inference_time': result['inference_time'],
                        'image_data': img_base64,
                        'detections': result['detections']
                    })
                    processing_state['total_birds'] += result['bird_count']
                    processing_state['total_time'] += result['inference_time']

        except Exception as e:
            print(f"Error processing {image_path.name}: {e}")
            continue

    # Mark as complete
    with processing_lock:
        processing_state['active'] = False


@app.route('/')
def index():
    """Serve the gong interface"""
    return render_template('index.html')


@app.route('/start', methods=['POST'])
def start_processing():
    """Start processing images (gong hit!)"""
    global processing_state

    with processing_lock:
        if processing_state['active']:
            return jsonify({'error': 'Already processing'}), 400

        if detector is None:
            return jsonify({'error': 'Detector not initialized'}), 500

        # Reset state
        processing_state['active'] = True
        processing_state['start_time'] = time.time()
        processing_state['processed_images'] = []
        processing_state['current_image'] = 0
        processing_state['total_birds'] = 0
        processing_state['total_time'] = 0

    # Start worker thread
    thread = threading.Thread(target=process_images_worker, daemon=True)
    thread.start()

    return jsonify({'status': 'started', 'message': 'Processing initiated!'})


@app.route('/stop', methods=['POST'])
def stop_processing():
    """Stop processing images (gong hit again!)"""
    global processing_state

    with processing_lock:
        if not processing_state['active']:
            return jsonify({'error': 'Not currently processing'}), 400

        processing_state['active'] = False

    return jsonify({'status': 'stopped', 'message': 'Processing stopped!'})


@app.route('/status')
def get_status():
    """Get current processing status"""
    with processing_lock:
        elapsed = time.time() - processing_state['start_time'] if processing_state['start_time'] else 0

        return jsonify({
            'active': processing_state['active'],
            'current_image': processing_state['current_image'],
            'total_images': processing_state['total_images'],
            'total_birds': processing_state['total_birds'],
            'total_time': processing_state['total_time'],
            'elapsed_time': elapsed,
            'images_per_second': processing_state['current_image'] / elapsed if elapsed > 0 else 0,
            'birds_per_second': processing_state['total_birds'] / elapsed if elapsed > 0 else 0,
            'processed_images_count': len(processing_state['processed_images'])
        })


@app.route('/results')
def get_results():
    """Get processed images"""
    with processing_lock:
        return jsonify({
            'images': processing_state['processed_images'],
            'total_birds': processing_state['total_birds'],
            'total_images': len(processing_state['processed_images'])
        })


@app.route('/results/<int:index>')
def get_result_image(index):
    """Get a specific processed image"""
    with processing_lock:
        if 0 <= index < len(processing_state['processed_images']):
            return jsonify(processing_state['processed_images'][index])
    return jsonify({'error': 'Image not found'}), 404


@app.route('/static/<path:path>')
def serve_static(path):
    """Serve static files"""
    return send_from_directory('static', path)


if __name__ == '__main__':
    # Initialize detector
    initialize_detector()

    # Count images
    image_count = len(list(IMAGES_DIR.glob('*.jpg'))) + \
                  len(list(IMAGES_DIR.glob('*.JPG'))) + \
                  len(list(IMAGES_DIR.glob('*.png'))) + \
                  len(list(IMAGES_DIR.glob('*.PNG')))

    print(f"\n{'='*60}")
    print(f"🎊 LuckyCharm Demo Server")
    print(f"{'='*60}")
    print(f"📷 Images ready: {image_count}")
    print(f"🔧 Detector: {'✅ Ready' if detector else '❌ Not loaded'}")
    print(f"🌐 Server starting on http://localhost:5001")
    print(f"{'='*60}\n")

    # Run server
    app.run(host='0.0.0.0', port=5001, debug=False, threaded=True)
