# Labeller - Nestperts Expert Annotation Platform

**Nestperts** (Nest + Experts) is a web-based tool for bird species annotation and training data curation. It's built with **Flask**, a lightweight Python web framework, and uses **MobileSAM** for intelligent segmentation.

## What Problem Does This Solve?

When training AI models to identify bird species, we need **labeled training data**:
- Images with bounding boxes around each bird
- Species labels for each bird
- High-quality annotations verified by experts

Manual labeling is tedious. Nestperts makes it faster by:
1. Starting with AI detections from NestVision
2. Letting experts refine boxes with smart segmentation (MobileSAM)
3. Adding species labels for each bird
4. Tracking work across multiple experts

## How to Run

Start the Nestperts server:
```bash
python labeller/app.py --data labeller/nestvision
```

Then open your browser to: **http://localhost:5000**

### Command-Line Arguments
- `--data`: Path to YOLO dataset folder (contains `images/` and `labels/`)
- `--port`: Port number (default: 5000)
- `--host`: Host address (default: 0.0.0.0)

## Project Structure

```
labeller/
├── app.py                  # Flask web server with API endpoints
├── templates/              # HTML files for the UI
│   ├── index.html         # Main annotation interface
│   └── ...                # Other UI pages
├── data_vis.py            # Data visualization utilities (unused)
├── nestvision/            # YOLO dataset folder
│   ├── images/            # Training images (.jpg, .png)
│   ├── labels/            # YOLO format labels (.txt)
│   ├── classes.txt        # List of species class names
│   └── species_info.json  # Species metadata (confidence, expert notes)
└── project_state.json     # Annotation progress tracking
```

## Key Concepts

### 1. Flask Web Framework
Flask is a minimalist Python framework for building web applications. Unlike Streamlit, you have full control:
- Write HTML templates
- Handle HTTP routes (URLs)
- Use JavaScript for interactivity

**Example route:**
```python
@app.route('/api/sam_segment', methods=['POST'])
def sam_segment():
    # Handle POST request to /api/sam_segment
    data = request.get_json()
    return jsonify({"result": "success"})
```

### 2. MobileSAM (Segment Anything Model)
MobileSAM is a computer vision model that creates precise object masks from simple point clicks.

**How it works:**
1. You click on a bird in the image
2. MobileSAM generates a segmentation mask (pixel-level outline)
3. We convert the mask to a bounding box
4. The box is saved in YOLO format

**Why MobileSAM?**
- Fast inference (mobile-optimized)
- Works with point prompts (just click!)
- More accurate than manual box drawing

### 3. YOLO Label Format
YOLO uses normalized coordinates (0-1 range) for bounding boxes:
```
<class_id> <x_center> <y_center> <width> <height>
```

**Example label file** (`labels/bird_image.txt`):
```
0 0.5 0.3 0.2 0.15
1 0.7 0.6 0.18 0.12
```

- `0`: Class ID (e.g., Brown Pelican)
- `0.5`: X-center (50% from left edge)
- `0.3`: Y-center (30% from top)
- `0.2`: Width (20% of image width)
- `0.15`: Height (15% of image height)

**Why normalized coordinates?**
Works with any image size! A 0.5 x-center is always the middle, whether the image is 640px or 4000px wide.

## Workflow

### 1. Initial Detection in NestVision
```
User uploads image → NestVision detects birds → User clicks "Train with Experts"
```

### 2. Image Transfer to Nestperts
```
POST /api/correction/upload
├── Receives: Image + initial detections
├── Saves: Image to nestvision/images/
└── Saves: Labels to nestvision/labels/
```

### 3. Expert Refinement
```
Expert opens image → Clicks on bird → MobileSAM generates box → Expert assigns species
```

### 4. Data Export
```
All labels saved in YOLO format → Ready for model training
```

## API Endpoints

### POST `/api/sam_segment`
Point-based segmentation using MobileSAM.

**Request:**
```json
{
  "filename": "bird_photo.jpg",
  "x": 0.5,
  "y": 0.3
}
```

**Response:**
```json
{
  "success": true,
  "bbox": [0.4, 0.2, 0.6, 0.4],
  "mask": "base64_encoded_mask_image"
}
```

### GET `/api/sam_status`
Check MobileSAM model status and device info.

**Response:**
```json
{
  "loaded": true,
  "device": "cuda",
  "model_size": "mobile_sam.pt"
}
```

### POST `/api/correction/upload`
Upload image with initial detections from NestVision.

**Request (FormData):**
- `file`: Image file
- `detections`: JSON array of bounding boxes

**Response:**
```json
{
  "message": "Image uploaded successfully",
  "filename": "bird_photo.jpg"
}
```

## MobileSAM Integration

### Model Loading
```python
from ultralytics import SAM

# Load model on startup
sam_model = SAM('models/mobile_sam.pt')
```

### Point-Based Segmentation
```python
# User clicks at (x=512, y=384) on a 1024x768 image
results = sam_model.predict(
    source='image.jpg',
    points=[[512, 384]],
    labels=[1]  # 1 = foreground, 0 = background
)

# Extract mask and convert to bounding box
mask = results[0].masks.data[0]
bbox = mask_to_bbox(mask)
```

### Two Inference Modes

**Fast Mode** (default):
- Resolution: 720x720
- Retina masks: Disabled
- Best for: Quick annotation

**SAHI Mode**:
- Resolution: 1024x1024
- Retina masks: Enabled
- Best for: Small or distant birds

## Important Implementation Details

### 1. Image Cache
```python
IMAGE_CACHE = {}  # Stores loaded images to avoid repeated disk reads
```
**Why?** Loading large images is slow. Cache them in memory after first load.

### 2. Inference Lock
```python
INFERENCE_LOCK = threading.Lock()  # Prevents concurrent model inference
```
**Why?** Running MobileSAM twice simultaneously can cause GPU memory issues. Lock ensures one at a time.

### 3. Mask Validation
We filter out bad segmentation results:
- **Too large**: Mask covers >30% of image (probably background)
- **Too small**: Mask <50 pixels (probably noise)

### 4. Bounding Box Padding
We add 5% padding to boxes for better coverage:
```python
width = width * 1.05
height = height * 1.05
```
**Why?** Segmentation masks are tight. Padding ensures we capture the full bird.

## Project State Tracking

The `project_state.json` file tracks annotation progress:
```json
{
  "images": {
    "bird_photo.jpg": {
      "status": "in_progress",
      "expert": "olise",
      "annotations": 12,
      "last_modified": "2025-02-21T10:30:00"
    }
  }
}
```

This allows multiple experts to work simultaneously without conflicts.

## Species Information

The `nestvision/species_info.json` file stores metadata:
```json
{
  "bird_photo.jpg": {
    "birds": [
      {
        "bbox": [0.5, 0.3, 0.2, 0.15],
        "species": "Brown Pelican",
        "confidence": "high",
        "notes": "Juvenile, distinctive plumage"
      }
    ]
  }
}
```

This is separate from YOLO labels because it contains extra information not needed for training.

## Development Tips

### Testing Segmentation
Use the test endpoint to check if MobileSAM is working:
```bash
curl http://localhost:5000/api/sam_status
```

### Debugging Flask
Flask prints all errors to the terminal. Look for stack traces after failed requests.

### Checking Logs
Nestperts logs to `logs/nestperts.log`:
```bash
tail -f logs/nestperts.log
```

### Inspecting Labels
YOLO labels are plain text. Open any file in `nestvision/labels/`:
```bash
cat nestvision/labels/bird_photo.txt
```

## Common Issues

### "CUDA Out of Memory"
**Problem**: GPU doesn't have enough memory for MobileSAM
**Solution**:
- Close other GPU-using programs
- Switch to CPU mode (slower but works):
  ```python
  sam_model = SAM('models/mobile_sam.pt').to('cpu')
  ```

### "Model Not Found"
**Problem**: `models/mobile_sam.pt` doesn't exist
**Solution**: Download MobileSAM:
  ```bash
  wget https://github.com/ChaoningZhang/MobileSAM/raw/master/weights/mobile_sam.pt -O models/mobile_sam.pt
  ```

### Segmentation Returns Empty Mask
**Problem**: Click location has no object
**Solution**:
- Try clicking directly on the bird's body (not background)
- Check if image loaded correctly
- Verify click coordinates are within image bounds

## Performance Optimization

### 1. Use Fast Mode for Initial Pass
Start with fast mode to quickly annotate many images. Switch to SAHI mode only for challenging cases.

### 2. Batch Processing
Process multiple images before switching tasks to maximize efficiency.

### 3. GPU Acceleration
If you have an NVIDIA GPU:
- Install CUDA toolkit
- Install `torch` with CUDA support
- MobileSAM will automatically use GPU

Check GPU usage:
```bash
nvidia-smi
```

## Learning Resources

- **Flask Documentation**: https://flask.palletsprojects.com/
- **MobileSAM Paper**: https://arxiv.org/abs/2306.14289
- **Ultralytics SAM**: https://docs.ultralytics.com/models/sam/
- **YOLO Format**: https://docs.ultralytics.com/datasets/detect/

## Next Steps

To understand the labeller better:
1. Read `app.py` - see how Flask routes work
2. Check `templates/index.html` - the UI structure
3. Test MobileSAM with `/api/sam_status` endpoint
4. Try segmenting a bird in the UI
5. Inspect the generated YOLO label files

## Training Pipeline Connection

Annotated data from Nestperts feeds directly into the training pipeline:
```
Nestperts labels → VisionTrain/training_data → Model training → New ONNX model
```

See `VisionTrain/README.md` for training instructions.
