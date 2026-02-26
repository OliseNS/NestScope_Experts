#!/bin/bash
# Test script to verify clustering endpoints work

echo "Testing Clustering API Endpoints"
echo "=================================="
echo ""

# Activate venv
source .venv/bin/activate

# Check if Flask is running
echo "1. Checking if Flask is running..."
if curl -s http://localhost:5000/api/clustering/status > /dev/null; then
    echo "   ✓ Flask is running"
else
    echo "   ✗ Flask is not running. Start it with: ./activate_and_run.sh"
    exit 1
fi

echo ""
echo "2. Testing status endpoint..."
curl -s http://localhost:5000/api/clustering/status | jq '.' || echo "   ✗ Failed"

echo ""
echo "3. Testing crop extraction (this may take 5-10 seconds)..."
echo "   Please wait..."
curl -X POST http://localhost:5000/api/clustering/extract_crops \
    -H "Content-Type: application/json" \
    --max-time 30 \
    -w "\n   Status: %{http_code}\n   Time: %{time_total}s\n" \
    | jq '.' || echo "   ✗ Failed"

echo ""
echo "=================================="
echo "Test complete!"
