#!/bin/bash

# Run Vision Train UI

GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}================================${NC}"
echo -e "${BLUE}   Vision Train UI Launcher    ${NC}"
echo -e "${BLUE}================================${NC}\n"

# Detect Python
if command -v python3 &> /dev/null; then
    PYTHON_CMD=python3
elif command -v python &> /dev/null; then
    PYTHON_CMD=python
else
    echo -e "${RED}Error: Python not found${NC}"
    exit 1
fi

echo -e "${GREEN}Starting Vision Train UI on http://localhost:8502${NC}"
echo -e "${GREEN}Press Ctrl+C to stop${NC}\n"

$PYTHON_CMD -m streamlit run VisionTrain/train_ui.py --server.port 8502
