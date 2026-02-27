#!/usr/bin/env python3
"""
Compare PyTorch (.pt) vs ONNX inference side-by-side

This script runs inference using both models and shows you the results
so you can verify the ONNX model is not "lobotomized".
"""

from ultralytics import YOLO
import onnxruntime as ort
import cv2
import numpy as np
from pathlib import Path
import time


def preprocess_for_onnx(image_path, imgsz=1024):
    """Preprocess image for ONNX (same as your inference.py)"""
    image = cv2.imread(image_path)
    h, w = image.shape[:2]

    # Calculate scale
    scale = min(imgsz / w, imgsz / h)
    nw, nh = int(w * scale), int(h * scale)

    # Resize
    resized = cv2.resize(image, (nw, nh))

    # Pad to square
    padded = np.full((imgsz, imgsz, 3), 114, dtype=np.uint8)
    pad_w, pad_h = (imgsz - nw) // 2, (imgsz - nh) // 2
    padded[pad_h:pad_h+nh, pad_w:pad_w+nw] = resized

    # Normalize and transpose
    img_rgb = cv2.cvtColor(padded, cv2.COLOR_BGR2RGB)
    img_norm = img_rgb.astype(np.float32) / 255.0
    img_chw = np.transpose(img_norm, (2, 0, 1))
    img_batch = np.expand_dims(img_chw, axis=0).astype(np.float32)

    return img_batch, image, scale, (pad_w, pad_h)


def test_comparison(test_image_path: str):
    """Run side-by-side comparison"""

    print("="*70)
    print("🔬 PyTorch vs ONNX Comparison Test")
    print("="*70)
    print(f"📸 Test image: {test_image_path}\n")

    # =========================================================================
    # 1. PyTorch (.pt) Inference
    # =========================================================================
    print("🟢 Testing PyTorch (.pt) model...")
    pt_model = YOLO("models/nano.pt")

    pt_start = time.perf_counter()
    pt_results = pt_model(test_image_path, conf=0.25, verbose=False)
    pt_time = time.perf_counter() - pt_start

    pt_boxes = pt_results[0].boxes.data.cpu().numpy()
    pt_count = len(pt_boxes)

    print(f"   Detections: {pt_count}")
    print(f"   Time: {pt_time*1000:.1f} ms")

    # Show first few detections
    if pt_count > 0:
        print(f"   Sample boxes (first 3):")
        for i, box in enumerate(pt_boxes[:3]):
            x1, y1, x2, y2, conf, cls = box
            w, h = x2 - x1, y2 - y1
            print(f"      Box {i+1}: [{x1:.0f}, {y1:.0f}, {x2:.0f}, {y2:.0f}] "
                  f"size={w:.0f}×{h:.0f} conf={conf:.2f}")

    # =========================================================================
    # 2. ONNX Inference (OLD - if it exists)
    # =========================================================================
    old_onnx_path = "models/nano.onnx"
    if Path(old_onnx_path).exists():
        print(f"\n🔴 Testing OLD ONNX (opset 12) model...")
        try:
            old_session = ort.InferenceSession(old_onnx_path)
            preprocessed, original, scale, pad = preprocess_for_onnx(test_image_path)

            old_start = time.perf_counter()
            old_output = old_session.run(None, {'images': preprocessed})
            old_time = time.perf_counter() - old_start

            # Count detections (max_det format: [1, 300, 6])
            confidences = old_output[0][0, :, 4]
            old_count = int(np.sum(confidences >= 0.25))

            print(f"   Detections: {old_count}")
            print(f"   Time: {old_time*1000:.1f} ms")

            # Show confidence distribution
            high_conf = np.sum(confidences >= 0.5)
            med_conf = np.sum((confidences >= 0.25) & (confidences < 0.5))
            print(f"   Confidence dist: {high_conf} high (≥0.5), {med_conf} medium (0.25-0.5)")

            # Check if it looks broken
            if old_count > pt_count * 3:
                print(f"   ⚠️  WARNING: Way too many detections! Model might be broken.")
            elif old_count < pt_count * 0.3:
                print(f"   ⚠️  WARNING: Way too few detections! Model might be broken.")

        except Exception as e:
            print(f"   ❌ Failed: {e}")
    else:
        print(f"\n🔴 OLD ONNX model not found (that's okay)")

    # =========================================================================
    # 3. ONNX Inference (NEW - fixed)
    # =========================================================================
    new_onnx_path = "models/nano_fixed.onnx"
    print(f"\n🟢 Testing NEW ONNX (opset 17) model...")

    if not Path(new_onnx_path).exists():
        print(f"   ❌ File not found: {new_onnx_path}")
        return

    new_session = ort.InferenceSession(new_onnx_path)
    preprocessed, original, scale, pad = preprocess_for_onnx(test_image_path)

    new_start = time.perf_counter()
    new_output = new_session.run(None, {'images': preprocessed})
    new_time = time.perf_counter() - new_start

    # Count detections
    confidences = new_output[0][0, :, 4]
    new_count = int(np.sum(confidences >= 0.25))

    print(f"   Detections: {new_count}")
    print(f"   Time: {new_time*1000:.1f} ms")

    # Show confidence distribution
    high_conf = np.sum(confidences >= 0.5)
    med_conf = np.sum((confidences >= 0.25) & (confidences < 0.5))
    print(f"   Confidence dist: {high_conf} high (≥0.5), {med_conf} medium (0.25-0.5)")

    # Show first few detections
    valid_mask = confidences >= 0.25
    valid_boxes = new_output[0][0, valid_mask, :]
    if len(valid_boxes) > 0:
        print(f"   Sample boxes (first 3):")
        for i, box in enumerate(valid_boxes[:3]):
            x, y, w, h, conf, cls = box
            print(f"      Box {i+1}: center=[{x:.0f}, {y:.0f}] "
                  f"size={w:.0f}×{h:.0f} conf={conf:.2f}")

    # =========================================================================
    # 4. Comparison Summary
    # =========================================================================
    print(f"\n" + "="*70)
    print("📊 COMPARISON SUMMARY")
    print("="*70)
    print(f"PyTorch (.pt):      {pt_count:4d} detections in {pt_time*1000:6.1f} ms")
    print(f"ONNX (fixed):       {new_count:4d} detections in {new_time*1000:6.1f} ms")

    # Calculate difference
    if pt_count > 0:
        diff_pct = abs(pt_count - new_count) / pt_count * 100
        print(f"\nDifference: {diff_pct:.1f}%")

        if diff_pct < 20:
            print("✅ EXCELLENT! Models are very similar.")
        elif diff_pct < 40:
            print("✅ GOOD! Models are reasonably close.")
        else:
            print("⚠️  Models differ significantly. May need tuning.")

    # Speed comparison
    speedup = pt_time / new_time
    if speedup > 1:
        print(f"\n⚡ ONNX is {speedup:.1f}× faster than PyTorch!")
    else:
        print(f"\n📝 PyTorch is {1/speedup:.1f}× faster (CPU doesn't benefit much from ONNX)")

    print("="*70)


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        test_image = sys.argv[1]
    else:
        # Default test image
        test_image = "server/cv_tools/images/15May2022_Cam1Card1_1027.jpg"

    if not Path(test_image).exists():
        print(f"❌ Image not found: {test_image}")
        print(f"\nUsage: python test_nano_fixed.py <image_path>")
        sys.exit(1)

    test_comparison(test_image)
