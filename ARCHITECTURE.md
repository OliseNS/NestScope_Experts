# LuckyCharm + RunPod Architecture

**Repo:** [nexus_project](https://github.com/OliseNS/nexus_project)

Efficient client-server bird detection system.

## Overview

```
┌──────────────────┐         ┌──────────────────┐
│   RunPod (8888)  │         │  Local PC (5001) │
│  ──────────────  │         │  ──────────────  │
│  GPU Processing  │  JSON   │  Visualization   │
│  Detection       │ ──────> │  Draw Bboxes     │
│  Classification  │  Only   │  Gallery         │
│  SAHI Slicing    │         │  Stats           │
└──────────────────┘         └──────────────────┘
```

## Components

### RunPod Server (GPU)
**Port**: 8888
**Location**: `/runpod/`

**Responsibilities**:
- Load ONNX models (detection + classification)
- Process images with GPU (TensorRT/CUDA)
- Run SAHI for better accuracy
- Send JSON results only

**Files**:
- `server.py` - Flask server
- `inference_engine.py` - GPU-optimized detection
- `swift_UQ.onnx` - Detection model (9.7MB)
- `classifier_swift.onnx` - Classification model (6.0MB)
- `demoday_images/` - Images to process

**Endpoints**:
- `POST /start` - Start processing
- `POST /stop` - Stop processing
- `GET /status` - Current stats (images processed, speed, etc.)
- `GET /results` - All results
- `GET /results/latest?last_index=N` - Stream new results
- `GET /health` - Health check

### Local Client (CPU)
**Port**: 5001
**Location**: `/luckycharm/`

**Responsibilities**:
- Connect to RunPod server
- Poll for new results (every 500ms)
- Read local images
- Draw color-coded bboxes
- Display gallery and stats

**Files**:
- `app.py` - Flask client server
- `draw_utils.py` - Bbox drawing utilities
- `demoday_images/` - Same images as RunPod (local copy)
- `templates/index.html` - Gong UI with RunPod URL input
- `static/` - CSS and JS for visualization

**Flow**:
1. User enters RunPod URL
2. Clicks gong to start
3. Client triggers RunPod /start
4. Client polls /results/latest every 500ms
5. For each result:
   - Read local image by filename
   - Draw bboxes from JSON coordinates
   - Encode as base64
   - Add to gallery
6. Update stats in real-time

## Data Flow

### JSON Format (RunPod → Local)

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

**Why JSON Only?**
- Image file: ~3-5 MB
- JSON metadata: ~1-2 KB
- **500-5000x smaller** bandwidth usage

### Species Groups (7 classes)
1. **COLOR_WADER** - Orange
2. **DARK** - Gray
3. **GULL** - White
4. **PELICAN** - Cyan
5. **SHOREBIRD** - Light Green
6. **TERN** - Yellow
7. **WHITE_WADER** - Cream

## Performance

### RunPod GPU Processing
- **TensorRT**: 20-40 img/s
- **CUDA**: 8-15 img/s
- **CPU**: 2-4 img/s (fallback)

### Local Rendering
- Bbox drawing: <10ms per image
- Encoding to base64: ~50ms
- Gallery update: instant

### Network Latency
- Poll interval: 500ms
- JSON size: ~1-2 KB per image
- Total latency: ~500ms per batch

## Deployment

### RunPod Setup
```bash
cd /workspace
# Upload runpod/ folder
cd runpod
pip install -r requirements.txt
python server.py
```

Access via RunPod HTTP proxy: `https://xxxxx-8888.proxy.runpod.net`

### Local Setup
```bash
cd luckycharm
pip install -r requirements.txt
python app.py
```

Access at: `http://localhost:5001`

## Requirements

### RunPod
- NVIDIA GPU (RTX 3090/4090/A4000+)
- CUDA 11.8+
- Python 3.8+
- `onnxruntime-gpu`

### Local
- Any CPU (no GPU needed)
- Python 3.8+
- `opencv-python`, `flask`, `requests`
- Same images as RunPod server

## Advantages

1. **Bandwidth Efficient**: Only JSON sent, not images
2. **High Quality**: Local rendering at full resolution
3. **Scalable**: Add more RunPod GPUs easily
4. **Flexible**: Local visualization can be customized
5. **Fast**: GPU processing + instant local display
6. **Secure**: Images never leave your local machine or RunPod

## Use Cases

- **Demo Day**: Show real-time GPU processing speed
- **Research**: Process large datasets on cloud GPU
- **Production**: Deploy detection service, visualize locally
- **Batch Processing**: Queue images on RunPod, view results anywhere

---

Built for DevDays 2026 Hackathon
