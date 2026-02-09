#!/bin/bash

# Quick restart script for NestScope

echo "Stopping any running servers..."

# Kill uvicorn processes
pkill -f "uvicorn server.main:app" 2>/dev/null
pkill -f "streamlit run" 2>/dev/null

sleep 1

echo "Servers stopped. Starting fresh..."
./run_app.sh
