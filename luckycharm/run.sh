#!/bin/bash
# LuckyCharm Demo - Startup Script

echo "🍀 Starting LuckyCharm Demo..."
echo "================================"

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

# Activate virtual environment
source .venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -q -r requirements.txt

# Check models exist
if [ ! -f "swift_UQ.onnx" ] || [ ! -f "classifier_swift.onnx" ]; then
    echo "❌ Error: Model files not found!"
    echo "Please ensure swift_UQ.onnx and classifier_swift.onnx are in this directory."
    exit 1
fi

# Check images exist
if [ ! -d "demoday_images" ] || [ -z "$(ls -A demoday_images)" ]; then
    echo "❌ Error: No images found in demoday_images/"
    echo "Please ensure images are copied to the demoday_images folder."
    exit 1
fi

# Count images
IMAGE_COUNT=$(find demoday_images -type f \( -iname "*.jpg" -o -iname "*.png" \) | wc -l)
echo "✅ Found $IMAGE_COUNT images to process"

# Start server
echo ""
echo "🚀 Starting server..."
echo "🌐 Open http://localhost:5001 in your browser"
echo ""
python app.py
