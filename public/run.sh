#!/bin/bash

# NestScope Public - Local Startup Script
# Single unified server (FastAPI serves both API and webapp)

set -e

echo "🚀 Starting NestScope Public..."
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "⚠️  No .env file found! Creating from .env.example..."
    cp .env.example .env
    echo "✓ Created .env file"
    echo "⚠️  Please edit .env and add your OPENROUTER_API_KEY"
    echo ""
fi

# Load environment variables
export $(cat .env | grep -v '^#' | xargs)

# Check for API key
if [ -z "$OPENROUTER_API_KEY" ] || [ "$OPENROUTER_API_KEY" = "your-api-key-here" ]; then
    echo "❌ Error: OPENROUTER_API_KEY not set in .env"
    echo "   Get your key at: https://openrouter.ai/keys"
    exit 1
fi

# Check database exists
if [ ! -f "${DB_PATH:-data/bird_data_complete.db}" ]; then
    echo "❌ Error: Database not found at ${DB_PATH:-data/bird_data_complete.db}"
    exit 1
fi

echo "✓ Environment variables loaded"
echo "✓ Database found at ${DB_PATH:-data/bird_data_complete.db}"
echo ""

# Create logs directory
mkdir -p logs

# Start unified server
PORT=${PORT:-8000}
echo "🔧 Starting NestScope Public (port $PORT)..."
echo "   Webapp:   http://localhost:$PORT"
echo "   API Docs: http://localhost:$PORT/docs"
echo ""

# Run with auto-reload for development
# IMPORTANT: This must be run from within an activated virtual environment
# Run: source ../.venv/bin/activate (or activate the venv before running this script)

if command -v uvicorn &> /dev/null; then
    # uvicorn is in PATH (venv is activated)
    uvicorn main:app --host 0.0.0.0 --port $PORT --reload
else
    # Fallback: try to use parent venv directly
    if [ -f ../.venv/bin/uvicorn ]; then
        echo "⚠️  Using parent venv (../.venv)"
        ../.venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port $PORT --reload
    else
        echo "❌ Error: uvicorn not found!"
        echo "   Please install dependencies: pip install -r requirements.txt"
        echo "   Or activate your virtual environment first"
        exit 1
    fi
fi

# Note: Ctrl+C will stop the server
