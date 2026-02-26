#!/bin/bash
# Activate virtual environment and run NestScope

# Activate the virtual environment
source .venv/bin/activate

echo "✓ Virtual environment activated"
echo "✓ Python: $(which python3)"
echo "✓ VIRTUAL_ENV: $VIRTUAL_ENV"

# Verify torch is available
if python3 -c "import torch" 2>/dev/null; then
    echo "✓ torch is available"
else
    echo "✗ torch not found! Install with: pip install -r requirements.txt"
    exit 1
fi

# Run the app
./run_app.sh
