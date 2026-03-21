# 🍀 LuckyCharm - Bird Detection System

Complete bird detection system with cloud GPU processing and local visualization.

## Architecture

```
luckycharm/
├── local/              # Local visualization client (port 5001)
├── runpod/             # GPU processing server (port 8888)
└── demoday_images/     # Shared images (15,000 Gulf Coast birds)
```

**How it works:**
1. **RunPod** processes images on GPU → sends JSON metadata
2. **Local** receives JSON → draws bboxes on local images → displays gallery

**Benefits:**
- No images sent over network (only JSON ~1-2 KB per image)
- High-quality local rendering (1200px, 95% JPEG)
- Real-time stats and gallery updates
- GPU acceleration (TensorRT/CUDA)

## Quick Start

### 1. Download Images (First Time)

```bash
cd luckycharm
# Already downloading 15,000 images...
# Check status: ls demoday_images | wc -l
```

### 2. Run RunPod Server

```bash
cd runpod

# Copy models first (from nexus/models/)
cp ../../models/swift_UQ.onnx .
cp ../../models/classifier_swift.onnx .

# Install and run
pip install -r requirements.txt
python server.py
```

Get your RunPod URL: `https://xxxxx-8888.proxy.runpod.net`

### 3. Run Local Client

```bash
cd local
pip install -r requirements.txt
python app.py
```

Open http://localhost:5001

### 4. Connect and Process

1. Enter RunPod URL in the input field
2. Click the gong to start
3. Watch real-time processing and gallery

## Folder Details

### `local/` - Visualization Client
- **Port**: 5001
- **Purpose**: Connect to RunPod, draw bboxes, show gallery
- **Files**:
  - `app.py` - Flask server with polling
  - `draw_utils.py` - Bbox rendering (color-coded by species)
  - `templates/` - Gong interface
  - `static/` - CSS/JS
  - `requirements.txt` - No GPU needed

### `runpod/` - GPU Server
- **Port**: 8888
- **Purpose**: Process images on GPU, send JSON
- **Files**:
  - `server.py` - Flask API server
  - `inference_engine.py` - TensorRT-optimized detection
  - `requirements.txt` - GPU dependencies
  - `SETUP.md` - Deployment guide
  - Need: `swift_UQ.onnx`, `classifier_swift.onnx`

### `demoday_images/` - Shared Dataset
- 15,000 Gulf Coast bird images
- Same folder used by both local and RunPod
- Downloaded from TWI S3 bucket

## JSON Format

RunPod sends only metadata:

```json
{
  "filename": "image_001.jpg",
  "image_size": {"width": 4000, "height": 3000},
  "detections": [
    {
      "bbox": [100, 200, 300, 400],
      "confidence": 0.95,
      "species": "PELICAN",
      "species_confidence": 0.88
    }
  ],
  "bird_count": 12,
  "inference_time": 1.2
}
```

## Species (7 Groups)

| Species | Color |
|---------|-------|
| PELICAN | Cyan |
| GULL | White |
| TERN | Yellow |
| WHITE_WADER | Cream |
| COLOR_WADER | Orange |
| SHOREBIRD | Green |
| DARK | Gray |

## Performance

### RunPod GPU
- **TensorRT**: 20-40 img/s
- **CUDA**: 8-15 img/s
- **CPU fallback**: 2-4 img/s

### Local Rendering
- Bbox drawing: <10ms
- Gallery update: Real-time

### Network
- JSON: 1-2 KB per image
- Poll interval: 500ms
- Total bandwidth: Minimal

## Documentation

- **`QUICKSTART.md`** - Fast setup guide
- **`ARCHITECTURE.md`** - System design
- **`local/LOCAL_GUIDE.md`** - Local client usage
- **`runpod/SETUP.md`** - RunPod deployment

## Development

Run locally without RunPod (for testing):

```bash
# Terminal 1: Mock server
cd runpod
python server.py

# Terminal 2: Local client
cd local
python app.py
```

Then connect to `http://localhost:8888` instead of RunPod URL.

---

Built for DevDays 2026 Hackathon
