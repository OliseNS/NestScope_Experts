#!/bin/bash

# Nestperts V2 Startup Script with Unlimited Uploads
# Uses waitress for production-ready serving without size limits

cd "$(dirname "$0")"

# Use venv Python (go up one level to find .venv)
# Detect OS: Windows venv uses Scripts/, Linux/Mac uses bin/
if [ -f "../.venv/Scripts/python.exe" ]; then
    PYTHON="../.venv/Scripts/python"
    PIP="../.venv/Scripts/pip"
else
    PYTHON="../.venv/bin/python"
    PIP="../.venv/bin/pip"
fi

# Check if waitress is installed, install if missing
if ! $PYTHON -c "import waitress" 2>/dev/null; then
    echo "⚠️  Installing waitress for unlimited uploads..." >&2
    $PIP install -q waitress 2>&1
fi

# Run with waitress (no upload limits)
$PYTHON -c "
import sys
sys.path.insert(0, '.')
from waitress import serve
from app import app

# Ensure unlimited uploads
app.config['MAX_CONTENT_LENGTH'] = None

# Configure waitress for large uploads
# Note: max_request_body_size in bytes (100GB = 100*1024*1024*1024)
serve(
    app,
    host='0.0.0.0',
    port=5000,
    threads=4,
    channel_timeout=7200,
    recv_bytes=1048576,  # 1MB receive buffer
    send_bytes=1048576,  # 1MB send buffer
    max_request_body_size=107374182400  # 100GB limit (effectively unlimited)
)
"
