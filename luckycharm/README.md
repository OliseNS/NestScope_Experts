# 🍀 LuckyCharm - Bird Detection Speed Demo

An interactive gong-powered demonstration showcasing the speed and accuracy of NestScope's AI bird detection models.

## 🎯 Overview

LuckyCharm processes thousands of Gulf Coast bird images in real-time, demonstrating:
- **Fast Detection**: YOLO v26 End-to-End format with SAHI support
- **Species Classification**: 7 bird species groups (COLOR_WADER, DARK, GULL, PELICAN, SHOREBIRD, TERN, WHITE_WADER)
- **Real-time Stats**: Images/second, birds detected, processing time
- **Visual Results**: Annotated images with bounding boxes and species labels

## 🚀 Quick Start

```bash
cd luckycharm
./run.sh
```

Then open http://localhost:5001 in your browser and **click the gong** to start!

## 📁 Structure

```
luckycharm/
├── app.py                      # Flask server
├── inference_engine.py         # Detection + classification engine
├── swift_UQ.onnx              # Detection model
├── classifier_swift.onnx       # Species classifier
├── demoday_images/            # Images to process
├── templates/
│   └── index.html             # Gong interface
├── static/
│   ├── css/style.css          # Coastal theme
│   └── js/
│       ├── app.js             # Main app logic
│       └── gong-sound.js      # Synthesized gong sound
└── requirements.txt           # Python dependencies
```

## 🎮 How It Works

1. **Hit the Gong** - Click to start processing all images
2. **Watch the Stats** - Real-time updates on speed and detections
3. **See Results** - Annotated images appear as they're processed
4. **Hit Again to Stop** - Stop processing early if needed
5. **View Summary** - Final statistics and performance metrics

## 🔧 Features

### SAHI (Slicing Aided Hyper Inference)
- Splits large images into overlapping tiles
- Better detection of small birds
- Automatic NMS to merge overlapping detections

### YOLO v26 End-to-End Support
- Supports both traditional YOLO format (8400 predictions)
- And YOLO v26 End-to-End format (300 predictions with NMS)

### Species Classification
- 7 species groups with confidence scores
- Color-coded bounding boxes per species
- Real-time classification as images process

## 📊 Performance

Expected performance on typical hardware:
- **CPU**: 2-3 images/second
- **GPU**: 8-12 images/second
- **Detection + Classification**: ~0.5-2s per image

## 🎨 Design

Coastal-themed interface with:
- Gradient backgrounds (coastal blue to ocean)
- Animated gong with ripple effects
- Glass-morphism stat cards
- Responsive gallery with fade-in animations
- Synthesized gong sound using Web Audio API

## 🛠️ Manual Setup

If `run.sh` doesn't work:

```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install flask opencv-python numpy onnxruntime

# Run server
python app.py
```

## 📝 Notes

- Models must be in the root `luckycharm/` directory
- Images must be in `demoday_images/` folder
- Supports JPG and PNG formats
- Results are displayed in real-time as processing happens
- All processing happens server-side for speed

## 🏆 Demo Tips

For competition/demo day:
1. Pre-load the page before showing
2. Hit the gong for dramatic effect
3. Highlight the real-time stats updating
4. Show the annotated images appearing
5. Stop early if time is limited (still shows summary)
6. Emphasize images/second metric for speed comparison

## 🐛 Troubleshooting

**Models not found**: Ensure `swift_UQ.onnx` and `classifier_swift.onnx` are in the luckycharm folder

**No images**: Copy images to `demoday_images/` folder

**Slow processing**: Check if CUDA is available with `onnxruntime-gpu`

**Port in use**: Change port in `app.py` (line with `app.run(port=5001)`)

---

Built for DevDays 2026 Hackathon 🌊
