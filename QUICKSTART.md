# LuckyCharm + RunPod Quick Start

**NestScope repo:** [https://github.com/OliseNS/nexus_project](https://github.com/OliseNS/nexus_project) (includes `luckycharm/` and related tooling.)

Process bird images on cloud GPU, visualize on your PC.

## Architecture Summary

```
RunPod (GPU)                 Your PC
────────────                 ───────
Process images  ──JSON──>   Draw bboxes
Port 8888                    Port 5001
```

**Key Point**: Only JSON is sent over network, not images. Bandwidth efficient!

## Step-by-Step Setup

### 1. RunPod Server (GPU Processing)

```bash
# On RunPod terminal
cd /workspace

# Upload runpod/ folder to RunPod
# (Use Jupyter file upload or git clone)

cd runpod

# Copy model files and images
# Place these in runpod/:
# - swift_UQ.onnx (9.7MB)
# - classifier_swift.onnx (6.0MB)
# - demoday_images/ folder with your images

# Install dependencies
pip install -r requirements.txt

# Start server
python server.py
```

**Get Public URL:**
1. Go to RunPod dashboard
2. Click your pod → **Connect**
3. Click **HTTP Service [Port 8888]**
4. Copy URL: `https://xxxxx-8888.proxy.runpod.net`

### 2. Local Client (Visualization)

```bash
# On your PC
cd luckycharm

# Ensure you have same images as RunPod
ls demoday_images/  # Should match RunPod exactly

# Install dependencies
pip install -r requirements.txt

# Start client
python app.py
```

Open http://localhost:5001 in your browser

### 3. Connect and Run

1. **Paste RunPod URL** into input field
2. **Click the gong** to start
3. **Watch real-time stats** update
4. **See annotated images** appear in gallery
5. **Click gong again** to stop

## What You'll See

### Stats (updates every 500ms)
- Images processed
- Birds detected
- Processing speed (img/s)
- Elapsed time

### Gallery
- High-quality images (1200px, 95% JPEG)
- Color-coded bounding boxes by species
- Confidence scores
- Species counts

### Species Colors
- **PELICAN**: Cyan
- **GULL**: White
- **TERN**: Yellow
- **WHITE_WADER**: Cream
- **COLOR_WADER**: Orange
- **SHOREBIRD**: Light Green
- **DARK**: Gray

## Expected Performance

### RunPod GPU
- **TensorRT**: 20-40 images/second
- **CUDA**: 8-15 images/second
- **CPU fallback**: 2-4 images/second

### Network
- JSON size: ~1-2 KB per image
- Poll interval: 500ms
- Minimal bandwidth usage

## File Requirements

### RunPod needs:
```
runpod/
├── server.py
├── inference_engine.py
├── requirements.txt
├── swift_UQ.onnx              ← Copy from models/
├── classifier_swift.onnx       ← Copy from models/
└── demoday_images/             ← Your images
```

### Local needs:
```
luckycharm/
├── app.py
├── draw_utils.py
├── requirements.txt
├── demoday_images/             ← Same images as RunPod
├── templates/index.html
└── static/
```

## Troubleshooting

### "Cannot reach RunPod"
- Check RunPod pod is running
- Verify URL includes https://
- Make sure it ends with port 8888

### "Local image not found"
- Ensure local images match RunPod exactly
- Check filename case (image.jpg vs image.JPG)

### Slow processing
- Check if TensorRT detected (see RunPod startup logs)
- Verify GPU is being used: `nvidia-smi` on RunPod
- Reduce SAHI slicing if out of memory

### No images appearing
- Open browser console (F12) for errors
- Check RunPod logs for processing errors
- Verify network tab shows /status polling

## Demo Tips

1. **Pre-test**: Connect before demo day
2. **Bookmark**: Save RunPod URL
3. **Prepare**: Have local client running
4. **Show**: Real-time stats and color-coded boxes
5. **Emphasize**: No images sent, only JSON (efficient!)

## Cost

RunPod pricing (approximate):
- **RTX 4090**: $0.30-0.50/hour
- **RTX 3090**: $0.25-0.40/hour
- **A4000**: $0.40-0.60/hour

For 5000 images:
- Processing time: 3-8 minutes
- Cost: **< $0.10**

## Next Steps

See detailed guides:
- `runpod/README.md` - RunPod server setup
- `luckycharm/LOCAL_GUIDE.md` - Local client details
- `ARCHITECTURE.md` - Full system architecture

---

**Ready to process!** Start RunPod server first, then connect from local client.
