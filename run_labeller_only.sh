#!/bin/bash

# Run only the Nestperts/Labeller app for debugging

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}   Nestperts Standalone Start   ${NC}"
echo -e "${GREEN}================================${NC}\n"

# Detect Python
PYTHON_CMD=$(which python3)
if [ -z "$PYTHON_CMD" ]; then
    PYTHON_CMD=$(which python)
fi

if [ -d ".venv" ]; then
    echo -e "${GREEN}✓ Using virtual environment${NC}"
    PYTHON_CMD=".venv/bin/python"
fi

echo -e "${GREEN}✓ Using Python: $PYTHON_CMD${NC}\n"

# Kill any existing process on port 5000
if lsof -Pi :5000 -sTCP:LISTEN -t >/dev/null 2>&1 ; then
    echo -e "${YELLOW}⚠ Killing existing process on port 5000...${NC}"
    lsof -ti:5000 | xargs kill -9 2>/dev/null || true
    sleep 1
fi

# Navigate to labeller directory
cd labeller || exit 1

echo -e "${GREEN}Starting Nestperts on http://localhost:5000${NC}"
echo -e "${YELLOW}Press Ctrl+C to stop${NC}\n"
echo -e "================================\n"

# Run the app
FLASK_ENV=development $PYTHON_CMD app.py
