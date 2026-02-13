import cv2
import os
import glob
import random

# CONFIG
DATASET_DIR = "nestvision"
IMG_DIR = os.path.join(DATASET_DIR, "images")
LABEL_DIR = os.path.join(DATASET_DIR, "labels")
OUTPUT_DEBUG = "debug_vis"
os.makedirs(OUTPUT_DEBUG, exist_ok=True)

CLASS_MAP = {
    0: "bird",
}

images = glob.glob(os.path.join(IMG_DIR, "*.jpg")) + glob.glob(os.path.join(IMG_DIR, "*.JPG"))
random.shuffle(images)

print(f"Checking {len(images)} images...")

for img_path in images[:70]: # Check 10 random images
    name = os.path.basename(img_path)
    label_path = os.path.join(LABEL_DIR, name.replace(".jpg", ".txt").replace(".JPG", ".txt"))
    
    img = cv2.imread(img_path)
    h_img, w_img, _ = img.shape
    
    if os.path.exists(label_path):
        with open(label_path, 'r') as f:
            for line in f:
                parts = line.split()
                cid = int(parts[0])
                cx, cy, w, h = map(float, parts[1:5])
                
                # Un-normalize
                x1 = int((cx - w/2) * w_img)
                y1 = int((cy - h/2) * h_img)
                x2 = int((cx + w/2) * w_img)
                y2 = int((cy + h/2) * h_img)
                
                label = CLASS_MAP.get(cid, str(cid))
                cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(img, label, (x1, y1-5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

    cv2.imwrite(os.path.join(OUTPUT_DEBUG, "vis_" + name), img)

print(f"Check the folder '{OUTPUT_DEBUG}' to see if boxes are correct.")