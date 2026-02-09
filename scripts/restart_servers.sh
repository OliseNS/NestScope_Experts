#!/bin/bash

# Script to restart both backend and frontend servers

echo "🔄 Restarting NestScope servers..."
echo ""

# Kill any existing processes on ports 8000 and 8501
echo "📍 Stopping existing servers..."
lsof -ti:8000 | xargs kill -9 2>/dev/null
lsof -ti:8501 | xargs kill -9 2>/dev/null
sleep 2

# Start FastAPI backend
echo "🚀 Starting FastAPI backend on port 8000..."
cd /home/olise/Projects/nexus/server
nohup python main.py > ../logs/backend.log 2>&1 &
BACKEND_PID=$!
echo "   Backend PID: $BACKEND_PID"

# Wait for backend to start
sleep 3

# Start Streamlit frontend
echo "🚀 Starting Streamlit frontend on port 8501..."
cd /home/olise/Projects/nexus
nohup streamlit run frontend/app/app_ui.py > logs/frontend.log 2>&1 &
FRONTEND_PID=$!
echo "   Frontend PID: $FRONTEND_PID"

echo ""
echo "✅ Servers started successfully!"
echo ""
echo "📊 Backend API:  http://localhost:8000"
echo "🖥️  Frontend UI:  http://localhost:8501"
echo ""
echo "📝 Logs:"
echo "   Backend:  tail -f logs/backend.log"
echo "   Frontend: tail -f logs/frontend.log"
