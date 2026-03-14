#!/bin/bash

# Simple Nestperts Startup for Debugging
# Uses Flask development server instead of waitress

cd "$(dirname "$0")"

# Use venv Python
PYTHON="../.venv/bin/python"

echo "Starting Nestperts on http://localhost:5000"
echo "Logs will appear below:"
echo "================================"

# Run Flask directly
$PYTHON app.py
