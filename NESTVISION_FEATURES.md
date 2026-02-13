# NestVision New Features Guide

## Overview

The NestVision module has been enhanced with three major features to improve model accuracy and enable species identification:

1. **AI Correction Tool** - Correct false detections and improve training data
2. **Species Identification** - Build a species classification dataset
3. **User-Friendly Vision Train UI** - Easy model training for non-experts

---

## 1. AI Correction Tool

### What It Does
After NestVision detects birds in an image, you can correct any errors the AI made. This helps improve the model by creating better training data.

### How to Use

1. **Run Detection** in NestVision
2. Click the **"🔧 Correct AI"** button after detection completes
3. The image will be uploaded to the labeller tool
4. A new window will open with the correction interface where you can:
   - **Click boxes** to change their class
   - **Draw new boxes** by dragging on the canvas
   - **Delete boxes** by selecting them and pressing Delete
5. Click **"💾 Save Corrections"** when done

### Data Storage
- Corrected images: `nestvision/corrections/images/`
- Corrected labels: `nestvision/corrections/labels/`

These can be merged into your training dataset to improve the model.

---

## 2. Species Identification

### What It Does
After detecting birds, NestVision shows you 5 random crops from the detections. You can identify the species of each bird, which helps build a dataset for species classification.

### How to Use

1. **Run Detection** in NestVision
2. Scroll down to the **"🐦 Species Identification Training"** section
3. For each crop:
   - Select the species from the dropdown
   - Click **"💾 Save"**
4. The crop is saved with the species label

### Available Species
Species are loaded from `CSV_Files/tblSpeciesData2015_2018_2021.csv`, including:
- BLSK (Black Skimmer)
- BRPE (Brown Pelican)
- GBTE (Gull-billed Tern)
- LAGU (Laughing Gull)
- ROYT (Royal Tern)
- FOTE (Forster's Tern)
- And many more...

### Data Storage
- Species-identified crops: `nestvision/crops/`
- Filename format: `{species_name}_{timestamp}.jpg`

These crops can be used to train a species classification model.

---

## 3. Vision Train UI

### What It Does
A user-friendly interface for training YOLO bird detection models without needing to write code or use the command line.

### How to Run

```bash
streamlit run VisionTrain/train_ui.py --server.port 8502
```

Or add it to your workflow by visiting `http://localhost:8502`

### Features

#### 🚀 Train Model Tab
- **Dataset Settings**: Specify your dataset path and data.yaml
- **Training Parameters**:
  - Epochs (how long to train)
  - Batch size (images per iteration)
  - Image size (resolution)
  - Early stopping patience
- **Model Settings**:
  - Start from pre-trained YOLO or continue training
  - Learning rate control
  - Optimizer selection (AdamW recommended)
- **Advanced Options**:
  - Image caching for faster training
  - Data augmentation for better generalization
- **Command Preview**: See exactly what will run
- **One-Click Start**: Generate and start training with one button

#### 📊 Monitor Progress Tab
- View training metrics in real-time
- Track loss curves
- View mAP (mean Average Precision) scores
- See confusion matrices
- Browse training sample images

#### ℹ️ Help Tab
- Quick start guide
- Dataset preparation instructions
- Parameter recommendations for beginners
- Troubleshooting tips
- Links to documentation

### Recommended Settings for Beginners

**For a small dataset (100-200 images):**
- Epochs: 50
- Batch Size: 16
- Image Size: 1024
- Learning Rate: 0.001
- Optimizer: AdamW

**For a large dataset (500+ images):**
- Epochs: 100
- Batch Size: 16 (or 8 if memory errors)
- Image Size: 1024
- Learning Rate: 0.001
- Optimizer: AdamW

---

## Complete Workflow

Here's how to use all features together to improve your model:

### Step 1: Run NestVision Detection
1. Upload an image in the NestVision tab
2. Run bird detection
3. Review the results

### Step 2: Correct AI Errors
1. Click "Correct AI" if there are any false positives/negatives
2. Fix the bounding boxes
3. Save corrections

### Step 3: Identify Species
1. Scroll to the Species Identification section
2. Identify 5 random bird crops
3. Save each identification

### Step 4: Accumulate Data
Repeat steps 1-3 for multiple images to build a comprehensive dataset.

### Step 5: Train Improved Model
1. Open Vision Train UI: `streamlit run VisionTrain/train_ui.py --server.port 8502`
2. Configure training parameters
3. Start training
4. Monitor progress
5. Deploy improved model

### Step 6: Iterate
1. Test new model in NestVision
2. Correct new errors
3. Retrain with expanded dataset
4. Repeat until satisfied with performance

---

## Directory Structure

```
nexus/
├── nestvision/
│   ├── corrections/
│   │   ├── images/          # Corrected detection images
│   │   └── labels/          # Corrected YOLO labels
│   └── crops/               # Species-identified bird crops
├── VisionTrain/
│   ├── train.py             # Original training script
│   ├── train_ui.py          # New user-friendly UI
│   └── train_generated.py  # Auto-generated from UI
├── labeller/
│   ├── app.py               # Flask app with new endpoints
│   └── templates/
│       └── correction_editor.html  # Correction interface
└── frontend/app/
    └── app_ui.py            # Enhanced NestVision tab
```

---

## Technical Details

### New API Endpoints (Labeller)

#### Upload Image for Correction
```
POST /api/correction/upload
Body: {
  "image_base64": "...",
  "detections": [...],
  "filename": "..."
}
Returns: {
  "status": "success",
  "image_hash": "...",
  "correction_url": "/correct/{hash}"
}
```

#### Get Correction Labels
```
GET /api/correction/labels/{image_hash}
Returns: [
  {"class_id": 0, "x": 0.5, "y": 0.5, "w": 0.1, "h": 0.1},
  ...
]
```

#### Save Corrections
```
POST /api/correction/save
Body: {
  "image_hash": "...",
  "labels": [...]
}
```

#### Save Species Crop
```
POST /api/crop/save
Body: {
  "crop_base64": "...",
  "species_code": "BRPE",
  "species_name": "Brown Pelican"
}
```

### New Functions (Frontend)

- `load_species_list()`: Load species from CSV
- `extract_crops_from_detections()`: Extract random crops from detections
- Helper functions for crop identification workflow

---

## Requirements

### Running Services

For full functionality, you need both services running:

1. **FastAPI Server** (port 8000): Main NestScope backend
   ```bash
   python -m uvicorn server.main:app --port 8000
   ```

2. **Labeller Flask App** (port 5000): Correction and crop saving
   ```bash
   python labeller/app.py --data nestvision
   ```

3. **Streamlit Frontend** (port 8501): Main UI
   ```bash
   streamlit run frontend/app/app_ui.py --server.port 8501
   ```

4. **Vision Train UI** (port 8502, optional): Training interface
   ```bash
   streamlit run VisionTrain/train_ui.py --server.port 8502
   ```

### Or use the convenience script:
```bash
./run_app.sh
```

Then separately run the labeller:
```bash
python labeller/app.py --data nestvision
```

---

## Troubleshooting

### "Make sure labeller app is running"
- Start the labeller: `python labeller/app.py --data nestvision`
- Check it's on port 5000: `curl http://localhost:5000`

### "No species found"
- Verify CSV exists: `CSV_Files/tblSpeciesData2015_2018_2021.csv`
- Check CSV format has a `SpeciesCode` column

### "Out of memory" during training
- Reduce batch size to 8 or 4
- Reduce image size to 800 or 640
- Close other applications

### Corrections not saving
- Check permissions on `nestvision/corrections/` directory
- Verify labeller app is running
- Check browser console for errors

---

## Future Enhancements

Planned improvements:
- [ ] Automatic merging of corrections into training dataset
- [ ] Species classification model training
- [ ] Integration of species classifier with detector
- [ ] Batch correction tool for multiple images
- [ ] Advanced species identification with confidence scores
- [ ] Export corrected dataset in multiple formats

---

## Questions or Issues?

If you encounter problems:
1. Check the troubleshooting section above
2. Verify all services are running
3. Check terminal logs for error messages
4. Ensure directories have proper permissions

For more help, check the application logs:
- Server: `logs/server.log`
- Streamlit: `logs/streamlit.log`
- Labeller: Check terminal output
