"""
Jetson Nano Edge Detection Script for NestScope
================================================

PURPOSE:
  Runs bird detection on the Jetson Nano using your YOLO model,
  then sends the results back to your laptop's NestScope server.

THE FLOW:
  1. You give it an image (file path or camera capture)
  2. Jetson runs YOLO detection locally (using GPU!)
  3. Results (bird count, bounding boxes) are sent via HTTP
     to your laptop's FastAPI server at /edge/scan
  4. Server saves results to SQLite database
  5. NestChat can now query: "How many birds in the last scan?"

SETUP ON JETSON:
  pip install ultralytics requests Pillow

USAGE:
  # Detect birds in a single image:
  python jetson_detect.py --image path/to/bird_photo.jpg

  # Use webcam/CSI camera for a single capture:
  python jetson_detect.py --camera

  # Continuous camera mode (helicopter simulation!):
  # Captures every 5 seconds, detects, sends — like a real aerial survey
  python jetson_detect.py --camera-loop
  python jetson_detect.py --camera-loop --interval 3   # every 3 seconds

  # Watch a folder for new images (monitoring mode):
  python jetson_detect.py --watch /path/to/folder

  # Override server IP:
  python jetson_detect.py --image photo.jpg --server 192.168.1.100

  # Offline mode — results saved locally, synced when server is reachable:
  python jetson_detect.py --camera-loop --interval 5
  # (buffering happens automatically if server is unreachable)

WHAT YOU NEED:
  - swift.pt model file copied to the Jetson (same folder as this script)
  - Your laptop running: python -m uvicorn server.main:app --host 0.0.0.0 --port 8000
  - Both devices on the same network (WiFi/Ethernet to same router)
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from PIL import Image

# ── Configuration ──────────────────────────────────────────────
# Change SERVER_IP to your laptop's IP address on the local network
# Find it with: hostname -I (Linux/Mac) or ipconfig (Windows)
SERVER_IP = "192.168.1.105"
SERVER_PORT = 8000
MODEL_PATH = "swift.pt"           # YOLO model file (copy from laptop's models/ folder)
CONFIDENCE_THRESHOLD = 0.25       # Minimum confidence to count a detection
DEVICE_NAME = "jetson-nano"       # Identifier for this edge device
OFFLINE_BUFFER_FILE = "offline_buffer.json"  # Stores results when server is unreachable


# ── Offline Buffer ─────────────────────────────────────────────
# WHY DO WE NEED THIS?
# In a real helicopter deployment, the Jetson may lose contact with
# the base station (WiFi range, interference, etc). Instead of losing
# those detections forever, we save them to a local JSON file.
# When the server becomes reachable again, we automatically send
# all buffered results — no data loss.

def _load_buffer() -> list:
    """Load the offline buffer from disk. Returns empty list if no buffer."""
    if os.path.exists(OFFLINE_BUFFER_FILE):
        try:
            with open(OFFLINE_BUFFER_FILE, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return []
    return []


def _save_buffer(buffer: list):
    """Save the offline buffer to disk (overwrites previous)."""
    with open(OFFLINE_BUFFER_FILE, "w") as f:
        json.dump(buffer, f)


def _add_to_buffer(payload: dict):
    """Add a single scan result to the offline buffer."""
    buffer = _load_buffer()
    buffer.append(payload)
    _save_buffer(buffer)
    print(f"  Buffered locally ({len(buffer)} scan{'s' if len(buffer) != 1 else ''} waiting)")


def flush_buffer(server_ip: str, server_port: int):
    """
    Try to send all buffered results to the server.

    Called automatically before each new send attempt.
    If the server is reachable, all buffered scans get delivered
    in order — oldest first.

    Returns:
        Number of successfully sent buffered items
    """
    buffer = _load_buffer()
    if not buffer:
        return 0

    url = f"http://{server_ip}:{server_port}/edge/scan"
    sent = 0

    for payload in buffer[:]:
        try:
            response = requests.post(url, json=payload, timeout=10)
            if response.status_code == 200:
                sent += 1
            else:
                break  # Server is having issues, stop trying
        except (requests.ConnectionError, requests.Timeout):
            break  # Server unreachable, keep remaining in buffer

    if sent > 0:
        # Remove sent items from buffer
        remaining = buffer[sent:]
        _save_buffer(remaining)
        print(f"  Synced {sent} buffered scan{'s' if sent != 1 else ''} to server"
              f"{f' ({len(remaining)} still waiting)' if remaining else ' (buffer empty)'}")

    return sent


def load_model(model_path: str):
    """
    Load the YOLO model using Ultralytics.

    WHY ULTRALYTICS?
    - It auto-detects if you have a GPU (CUDA) and uses it
    - On Jetson, this means fast inference using the onboard GPU
    - The .pt format is native PyTorch, so no conversion needed

    Args:
        model_path: Path to the .pt model file

    Returns:
        YOLO model object ready for inference
    """
    try:
        from ultralytics import YOLO
    except ImportError:
        print("ERROR: ultralytics not installed!")
        print("Run: pip install ultralytics")
        sys.exit(1)

    if not os.path.exists(model_path):
        print(f"ERROR: Model not found at '{model_path}'")
        print(f"Copy swift.pt from your laptop: scp user@laptop_ip:path/to/nexus/models/swift.pt .")
        sys.exit(1)

    print(f"Loading model: {model_path}")
    model = YOLO(model_path)
    print(f"Model loaded! Device: {model.device}")
    return model


def detect_birds(model, image_path: str, conf_threshold: float = CONFIDENCE_THRESHOLD):
    """
    Run bird detection on a single image.

    HOW YOLO WORKS (simplified):
    - The image is divided into a grid
    - For each grid cell, the model predicts:
      * Is there an object here? (confidence score)
      * Where exactly is it? (bounding box: x, y, width, height)
    - We keep only predictions above our confidence threshold

    Args:
        model: Loaded YOLO model
        image_path: Path to the image file
        conf_threshold: Minimum confidence (0.0 to 1.0)

    Returns:
        dict with bird_count, detections list, and inference_time
    """
    if not os.path.exists(image_path):
        print(f"ERROR: Image not found: {image_path}")
        return None

    # Get image dimensions for the response
    img = Image.open(image_path)
    img_width, img_height = img.size

    print(f"Running detection on: {image_path} ({img_width}x{img_height})")
    start_time = time.time()

    # Run YOLO inference
    # verbose=False suppresses the default YOLO output
    results = model(image_path, conf=conf_threshold, imgsz=1024, verbose=False)

    inference_time = time.time() - start_time

    # Parse detections from YOLO results
    detections = []
    for result in results:
        boxes = result.boxes
        if boxes is not None:
            for i in range(len(boxes)):
                # Get bounding box coordinates (x1, y1, x2, y2 format)
                box = boxes.xyxy[i].cpu().numpy()
                confidence = float(boxes.conf[i].cpu().numpy())

                detections.append({
                    "bbox": {
                        "x1": float(box[0]),
                        "y1": float(box[1]),
                        "x2": float(box[2]),
                        "y2": float(box[3])
                    },
                    "confidence": round(confidence, 3),
                    "class": "bird"
                })

    bird_count = len(detections)
    print(f"Detected {bird_count} bird{'s' if bird_count != 1 else ''} "
          f"in {inference_time:.2f}s")

    return {
        "bird_count": bird_count,
        "detections": detections,
        "inference_time": round(inference_time, 3),
        "image_width": img_width,
        "image_height": img_height,
        "image_name": os.path.basename(image_path),
        "confidence_threshold": conf_threshold
    }


def send_to_server(results: dict, server_ip: str, server_port: int):
    """
    Send detection results to the NestScope server on your laptop.

    THIS IS THE KEY PART of the edge deployment story:
    - Jetson detects birds locally (fast, no internet needed)
    - Results are small JSON data (just numbers + coordinates)
    - Sent over local WiFi to your laptop's FastAPI server
    - Server saves to SQLite → NestChat can query it immediately

    Args:
        results: Detection results from detect_birds()
        server_ip: Laptop's IP address
        server_port: FastAPI server port (default: 8000)

    Returns:
        True if successful, False if failed
    """
    url = f"http://{server_ip}:{server_port}/edge/scan"

    payload = {
        "device_name": DEVICE_NAME,
        "image_name": results["image_name"],
        "bird_count": results["bird_count"],
        "detections": results["detections"],
        "inference_time": results["inference_time"],
        "image_width": results["image_width"],
        "image_height": results["image_height"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "confidence_threshold": results.get("confidence_threshold", CONFIDENCE_THRESHOLD)
    }

    # First, try to flush any previously buffered results
    flush_buffer(server_ip, server_port)

    try:
        print(f"Sending results to {url}...")
        response = requests.post(url, json=payload, timeout=10)

        if response.status_code == 200:
            data = response.json()
            print(f"Server received! Scan ID: {data.get('scan_id', 'N/A')}")
            return True
        else:
            print(f"Server error {response.status_code} — buffering locally")
            _add_to_buffer(payload)
            return False

    except requests.ConnectionError:
        print(f"Cannot reach server — buffering locally")
        _add_to_buffer(payload)
        return False
    except requests.Timeout:
        print("Request timed out — buffering locally")
        _add_to_buffer(payload)
        return False


def capture_from_camera():
    """
    Capture a single frame from camera (USB webcam or CSI camera).

    On Jetson Nano:
    - CSI camera uses GStreamer pipeline
    - USB webcam uses standard OpenCV capture

    Returns:
        Path to saved temporary image, or None if failed
    """
    try:
        import cv2
    except ImportError:
        print("ERROR: OpenCV not installed!")
        print("Run: pip install opencv-python")
        return None

    # Try USB camera first (simpler)
    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        print("No camera found. Trying CSI camera...")
        # GStreamer pipeline for Jetson CSI camera
        gst_pipeline = (
            "nvarguscamerasrc ! "
            "video/x-raw(memory:NVMM), width=1920, height=1080, framerate=30/1 ! "
            "nvvidconv ! video/x-raw, format=BGRx ! "
            "videoconvert ! video/x-raw, format=BGR ! appsink"
        )
        cap = cv2.VideoCapture(gst_pipeline, cv2.CAP_GSTREAMER)

    if not cap.isOpened():
        print("ERROR: Could not open any camera")
        return None

    ret, frame = cap.read()
    cap.release()

    if not ret:
        print("ERROR: Could not capture frame")
        return None

    # Save to temp file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    temp_path = f"/tmp/jetson_capture_{timestamp}.jpg"
    cv2.imwrite(temp_path, frame)
    print(f"Captured image: {temp_path}")
    return temp_path


def camera_loop(model, interval: float, conf_threshold: float,
                server_ip: str, server_port: int, no_send: bool = False):
    """
    Continuous camera capture mode — simulates a helicopter aerial survey.

    HOW IT WORKS:
    - Every `interval` seconds, captures a frame from the camera
    - Runs bird detection on that frame
    - Sends results to the server (or buffers if server is unreachable)
    - Repeats until you press Ctrl+C

    THIS IS THE HELICOPTER MODE:
    Imagine the Jetson mounted on a helicopter with a downward-facing camera.
    As it flies over a bird colony, it captures images at regular intervals.
    Each image gets processed on-board (no internet needed!) and results
    are transmitted back to the base station.

    Args:
        model: Loaded YOLO model
        interval: Seconds between captures
        conf_threshold: Minimum confidence
        server_ip: Base station IP
        server_port: Base station port
        no_send: If True, don't send to server (local-only testing)
    """
    try:
        import cv2
    except ImportError:
        print("ERROR: OpenCV not installed! Run: pip install opencv-python")
        return

    # Try USB camera first, then CSI
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("No USB camera. Trying CSI camera...")
        gst_pipeline = (
            "nvarguscamerasrc ! "
            "video/x-raw(memory:NVMM), width=1920, height=1080, framerate=30/1 ! "
            "nvvidconv ! video/x-raw, format=BGRx ! "
            "videoconvert ! video/x-raw, format=BGR ! appsink"
        )
        cap = cv2.VideoCapture(gst_pipeline, cv2.CAP_GSTREAMER)

    if not cap.isOpened():
        print("ERROR: Could not open any camera")
        return

    scan_count = 0
    total_birds = 0

    print("\n" + "=" * 50)
    print("  NESTSCOPE AERIAL SURVEY MODE")
    print("  Capturing every", interval, "seconds")
    print("  Press Ctrl+C to stop")
    print("=" * 50 + "\n")

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("WARNING: Failed to capture frame, retrying...")
                time.sleep(1)
                continue

            # Save frame to temp file for YOLO
            scan_count += 1
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            temp_path = f"/tmp/aerial_scan_{timestamp}.jpg"
            cv2.imwrite(temp_path, frame)

            print(f"\n--- Scan #{scan_count} [{timestamp}] ---")
            results = detect_birds(model, temp_path, conf_threshold)

            if results:
                total_birds += results["bird_count"]

                if not no_send:
                    send_to_server(results, server_ip, server_port)
                else:
                    print(f"  (local only — not sending)")

                print(f"  Running total: {total_birds} birds across {scan_count} scans")

            # Clean up temp image to save disk space
            try:
                os.remove(temp_path)
            except OSError:
                pass

            time.sleep(interval)

    except KeyboardInterrupt:
        print(f"\n\nSurvey complete!")
        print(f"  Total scans:  {scan_count}")
        print(f"  Total birds:  {total_birds}")
        buffer = _load_buffer()
        if buffer:
            print(f"  Buffered:     {len(buffer)} scans waiting to sync")
            print(f"  Run again with --flush to send buffered results")
    finally:
        cap.release()


def watch_folder(model, folder_path: str, server_ip: str, server_port: int):
    """
    Watch a folder for new images and auto-detect birds.

    MONITORING MODE:
    - Checks the folder every 2 seconds for new .jpg/.png files
    - Runs detection on any new image
    - Sends results to server
    - Useful for simulating a live feed during demo

    Args:
        model: Loaded YOLO model
        folder_path: Folder to watch
        server_ip: Laptop's IP address
        server_port: Server port
    """
    folder = Path(folder_path)
    if not folder.exists():
        print(f"ERROR: Folder not found: {folder_path}")
        return

    processed = set()
    image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff'}

    print(f"Watching folder: {folder_path}")
    print("Drop images into this folder to auto-detect birds.")
    print("Press Ctrl+C to stop.\n")

    try:
        while True:
            for img_file in folder.iterdir():
                if img_file.suffix.lower() in image_extensions and img_file.name not in processed:
                    processed.add(img_file.name)
                    results = detect_birds(model, str(img_file))
                    if results:
                        send_to_server(results, server_ip, server_port)
                    print()  # Blank line between detections
            time.sleep(2)
    except KeyboardInterrupt:
        print("\nStopped watching.")


def main():
    parser = argparse.ArgumentParser(
        description="NestScope Edge Detection - Run bird detection on Jetson Nano",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python jetson_detect.py --image birds.jpg
  python jetson_detect.py --image birds.jpg --server 192.168.1.50
  python jetson_detect.py --camera
  python jetson_detect.py --camera-loop                    # aerial survey mode!
  python jetson_detect.py --camera-loop --interval 3       # every 3 seconds
  python jetson_detect.py --watch /home/jetson/images/
  python jetson_detect.py --flush                          # send buffered results
        """
    )

    # Input source (pick one)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--image", type=str, help="Path to image file for detection")
    group.add_argument("--camera", action="store_true", help="Single capture from camera")
    group.add_argument("--camera-loop", action="store_true",
                        help="Continuous camera capture (aerial survey mode)")
    group.add_argument("--watch", type=str, help="Watch folder for new images")
    group.add_argument("--flush", action="store_true",
                        help="Send all buffered offline results to server")

    # Configuration
    parser.add_argument("--server", type=str, default=SERVER_IP,
                        help=f"Laptop server IP (default: {SERVER_IP})")
    parser.add_argument("--port", type=int, default=SERVER_PORT,
                        help=f"Server port (default: {SERVER_PORT})")
    parser.add_argument("--model", type=str, default=MODEL_PATH,
                        help=f"Model file path (default: {MODEL_PATH})")
    parser.add_argument("--conf", type=float, default=CONFIDENCE_THRESHOLD,
                        help=f"Confidence threshold (default: {CONFIDENCE_THRESHOLD})")
    parser.add_argument("--interval", type=float, default=5.0,
                        help="Seconds between captures in --camera-loop mode (default: 5)")
    parser.add_argument("--no-send", action="store_true",
                        help="Run detection only, don't send to server")

    args = parser.parse_args()

    # --flush doesn't need a model, handle it first
    if args.flush:
        buffer = _load_buffer()
        if not buffer:
            print("No buffered results to send.")
        else:
            print(f"Flushing {len(buffer)} buffered scan{'s' if len(buffer) != 1 else ''}...")
            sent = flush_buffer(args.server, args.port)
            if sent == 0:
                print("Could not reach server. Try again later.")
        return

    # Load model
    model = load_model(args.model)

    # Run based on input mode
    if args.image:
        results = detect_birds(model, args.image, args.conf)
        if results and not args.no_send:
            send_to_server(results, args.server, args.port)
        elif results:
            print("\nResults (not sent to server):")
            print(json.dumps(results, indent=2))

    elif args.camera:
        image_path = capture_from_camera()
        if image_path:
            results = detect_birds(model, image_path, args.conf)
            if results and not args.no_send:
                send_to_server(results, args.server, args.port)

    elif args.camera_loop:
        camera_loop(model, args.interval, args.conf,
                    args.server, args.port, args.no_send)

    elif args.watch:
        watch_folder(model, args.watch, args.server, args.port)


if __name__ == "__main__":
    main()
