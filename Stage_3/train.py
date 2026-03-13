from ultralytics import YOLO

# 1. Load the model
model = YOLO('swift.pt')

# 2. Define High-Recall & Tight-Box Hyperparameters
train_params = {
    "data": "licksplit/data.yaml",
    "epochs": 100,
    "imgsz": 1024,
    "batch": 16,
    "lr0": 0.0005,
    "patience": 35,
    "device": 0,           # Set to 'cpu' if no GPU
    
    # --- Performance Targets ---
    "box": 10.0,           
    "cls": 0.3,            
    "dfl": 2.0,            
    
    # --- Multi-Scale & Robustness ---
    "multi_scale": 0.2,    # <-- CORRECTED: float value (varies imgsz by +/- 20%)
    "scale": 0.9,          # Object scaling within images
    "fliplr": 0.5,         # Horizontal flip
    "mosaic": 1.0,         # 4-image stitch
    "mixup": 0.15,         # Image blending 
    "copy_paste": 0.3,     # Instance cloning 
    
    # --- Environment/Augmentation ---
    "hsv_h": 0.015,
    "hsv_s": 0.7,
    "hsv_v": 0.4,
    "close_mosaic": 10,    # Clean fine-tuning at the end
    
    # --- Operational ---
    "project": "bird_detection_v26",
    "name": "recall_priority_run",
    "exist_ok": True,
    "pretrained": True,
    "optimizer": 'SGD'     # YOLO26 also supports 'MuSGD', but SGD is rock solid here
}

# 3. Execute Training
if __name__ == "__main__":
    model.train(**train_params)