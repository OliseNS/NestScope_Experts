import os
from deepforest import main
from pytorch_lightning import Trainer
from pytorch_lightning.callbacks import ModelCheckpoint

# 1. Initialize DeepForest and load pre-trained NEON weights
model = main.deepforest()
model.use_release()

# 2. Configure Training & Validation Data Paths
# Updated to point directly to the nestvision folder
base_dir = "nestvision"

model.config["train"]["csv_file"] = os.path.join(base_dir, "train_annotations.csv")
model.config["train"]["root_dir"] = os.path.join(base_dir, "images")

model.config["validation"]["csv_file"] = os.path.join(base_dir, "val_annotations.csv")
model.config["validation"]["root_dir"] = os.path.join(base_dir, "images")

# 3. Configure Hyperparameters
# 512x512 provides high resolution for small birds without OOM (Out Of Memory) errors.
model.config["patch_size"] = 512 

# Batch size of 4 to 8 is usually the sweet spot for 512x512 patches on standard GPUs
model.config["train"]["batch_size"] = 4  
model.config["validation"]["batch_size"] = 4 

# Keep the learning rate small (1e-4) so we don't destroy the pre-trained weights
model.config["train"]["lr"] = 1e-4       
model.config["train"]["epochs"] = 30     

# 4. Set up Checkpointing
# We want to save the model that performs best on the validation set
checkpoint_callback = ModelCheckpoint(
    dirpath="checkpoints",
    save_top_k=1,
    monitor="val_loss", 
    mode="min",
    filename="best_bird_model-{epoch:02d}-{val_loss:.2f}"
)

# Initialize the PyTorch Lightning Trainer
trainer = Trainer(
    max_epochs=model.config["train"]["epochs"],
    callbacks=[checkpoint_callback],
    accelerator="auto", # Automatically detects and uses your GPU
    devices=1
)

# 5. Start Fine-tuning!
if __name__ == "__main__":
    print("Starting DeepForest fine-tuning...")
    print(f"Training on patches of size: {model.config['patch_size']}")
    
    trainer.fit(model)

    print("-" * 50)
    print("Training Complete!")
    print(f"Your best model weights will be saved in the 'checkpoints' directory.")