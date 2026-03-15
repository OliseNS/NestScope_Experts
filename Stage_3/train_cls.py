from ultralytics import YOLO

# 1. Load your base classification model
model = YOLO('cls_swift.pt')

# 2. Define Anti-Overfitting Hyperparameters for 75 Classes
train_params = {
    # Provide the path to the master directory folder
    "data": "yolo_cls", 
    "epochs": 100,
    
    # High resolution to catch fine-grained feather/beak details
    "imgsz": 512,          
    "batch": 32,           
    "device": 0,           
    "patience": 25,        # Stops early if validation accuracy plateaus
    
    # --- OPTIMIZER (Anti-Overfitting Focus) ---
    "optimizer": "AdamW",  
    "lr0": 0.001,          
    "weight_decay": 0.001, # UPDATED: Strict penalty against memorizing the 500 images
    "dropout": 0.3,        # ADDED: Randomly disables 30% of neurons to force robust learning
    
    # --- AUGMENTATIONS (Tuned for Classification) ---
    "degrees": 0.0,        
    "scale": 0.5,          
    "fliplr": 0.5,         
    "hsv_h": 0.015,        
    "hsv_s": 0.7,
    "hsv_v": 0.4,
    
    # THE SECRET WEAPON FOR CLASSIFICATION: Random Erasing
    "erasing": 0.4,        # UPDATED: Drops bigger black boxes to force the model to look at the whole bird
    
    # --- OPERATIONAL ---
    "project": "bird_classification_runs",
    "name": "adamw_75_classes_dropout",
    "exist_ok": True,
    "pretrained": True,
}

# 3. Execute Training
if __name__ == "__main__":
    print("🦅 Starting 75-Class Fine-Grained Classification with Anti-Overfitting...")
    model.train(**train_params)