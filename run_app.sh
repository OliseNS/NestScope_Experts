#!/bin/bash

# NestScope - Run both FastAPI server and Streamlit client concurrently

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Optional: install dependencies
# pip install -r requirements.txt

echo -e "${BLUE}================================${NC}"
echo -e "${BLUE}   NestScope Startup Script     ${NC}"
echo -e "${BLUE}================================${NC}\n"

# Create logs directory if it doesn't exist
mkdir -p logs
echo -e "${GREEN}✓ Logs directory ready${NC}"

# Check if .env exists
if [ ! -f .env ]; then
    echo -e "${YELLOW}Warning: .env file not found${NC}"
    echo -e "${YELLOW}Creating default .env file...${NC}"
    cat > .env << 'EOF'
OPENROUTER_API_KEY=your-api-key-here
DB_PATH=data/bird_data_complete.db
DB_TYPE=sqlite
EOF
    echo -e "${RED}Please update .env with your OpenRouter API key before running again${NC}"
    exit 1
fi

# Check if database exists
if [ ! -f "data/bird_data_complete.db" ]; then
    echo -e "${RED}Error: Database not found at data/bird_data_complete.db${NC}"
    echo -e "${YELLOW}Please run: python scripts/import_all_to_sqlite.py${NC}"
    exit 1
fi

# Function to cleanup background processes on exit
cleanup() {
    echo -e "\n${YELLOW}Shutting down servers...${NC}"
    if [ ! -z "$SERVER_PID" ]; then
        kill $SERVER_PID 2>/dev/null || true
    fi
    if [ ! -z "$CLIENT_PID" ]; then
        kill $CLIENT_PID 2>/dev/null || true
    fi
    echo -e "${GREEN}Servers stopped${NC}"
    exit 0
}

# Trap Ctrl+C and call cleanup
trap cleanup INT TERM

# Start FastAPI server in background
echo -e "${GREEN}Starting FastAPI server on http://localhost:8000${NC}"
python -m uvicorn server.main:app --host 0.0.0.0 --port 8000 --reload > logs/server.log 2>&1 &
SERVER_PID=$!

# Wait for server to start
echo -e "${YELLOW}Waiting for server to start...${NC}"
sleep 3

# Check if server is running
if ! curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo -e "${RED}Warning: Server health check failed, but continuing...${NC}"
fi

# Start Streamlit client in background
echo -e "${GREEN}Starting Streamlit client on http://localhost:8501${NC}"
python -m streamlit run frontend/app/app_ui.py --server.port 8501 > logs/streamlit.log 2>&1 &
CLIENT_PID=$!

# Wait a bit for Streamlit to start
sleep 3

echo -e "\n${BLUE}================================${NC}"
echo -e "${GREEN}✓ NestScope is running!${NC}"
echo -e "${BLUE}================================${NC}"
echo -e "\n${GREEN}FastAPI Server:${NC}  http://localhost:8000"
echo -e "${GREEN}Streamlit App:${NC}   http://localhost:8501"
echo -e "${GREEN}API Docs:${NC}        http://localhost:8000/docs"
echo -e "\n${YELLOW}Logs:${NC}"
echo -e "  Server:    tail -f logs/server.log"
echo -e "  Streamlit: tail -f logs/streamlit.log"
echo -e "\n${YELLOW}Press Ctrl+C to stop both servers${NC}\n"

# Wait for both processes
wait

