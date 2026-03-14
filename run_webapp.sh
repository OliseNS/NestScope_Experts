#!/bin/bash

# NestScope - Run FastAPI backend + Flask webapp

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}================================${NC}"
echo -e "${BLUE}   NestScope Web Application    ${NC}"
echo -e "${BLUE}================================${NC}\n"

# Create logs directory
mkdir -p logs

# Detect Python
PYTHON_CMD=python3
if ! command -v $PYTHON_CMD &> /dev/null; then
    PYTHON_CMD=python
fi

echo -e "${GREEN}✓ Using Python: ${PYTHON_CMD}${NC}"

# Check if .env exists
if [ ! -f .env ]; then
    echo -e "${YELLOW}Warning: .env file not found${NC}"
    echo -e "${YELLOW}Creating default .env file...${NC}"
    cat > .env << 'EOF'
OPENROUTER_API_KEY=your-api-key-here
DB_PATH=data/bird_data_complete.db
DB_TYPE=sqlite
API_BASE_URL=http://localhost:8000
EOF
    echo -e "${RED}Please update .env with your OpenRouter API key${NC}"
    exit 1
fi

# Check if database exists
if [ ! -f "data/bird_data_complete.db" ]; then
    echo -e "${RED}Error: Database not found at data/bird_data_complete.db${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Database found${NC}"

# Cleanup function
cleanup() {
    echo -e "\n${YELLOW}Shutting down servers...${NC}"
    if [ ! -z "$SERVER_PID" ]; then
        kill $SERVER_PID 2>/dev/null || true
    fi
    if [ ! -z "$WEBAPP_PID" ]; then
        kill $WEBAPP_PID 2>/dev/null || true
    fi
    if [ ! -z "$LABELLER_PID" ]; then
        kill $LABELLER_PID 2>/dev/null || true
    fi
    echo -e "${GREEN}Servers stopped${NC}"
    exit 0
}

# Trap Ctrl+C
trap cleanup INT TERM

# Start FastAPI backend
echo -e "${GREEN}Starting FastAPI backend...${NC}"
$PYTHON_CMD -m uvicorn server.main:app --host 0.0.0.0 --port 8000 --reload > logs/server.log 2>&1 &
SERVER_PID=$!

# Wait for backend to start
echo -e "${YELLOW}Waiting for backend...${NC}"
sleep 3

# Check backend health
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Backend is ready${NC}"
else
    echo -e "${YELLOW}⚠ Backend health check failed (continuing anyway)${NC}"
fi

# Start Flask webapp
echo -e "${GREEN}Starting Flask webapp...${NC}"
cd webapp && $PYTHON_CMD app.py > ../logs/webapp.log 2>&1 &
WEBAPP_PID=$!
cd ..

sleep 2

# Start Nestperts (optional)
if [ -d "labeller" ]; then
    echo -e "${GREEN}Starting Nestperts...${NC}"
    cd labeller && bash run_nestperts.sh > ../logs/nestperts.log 2>&1 &
    LABELLER_PID=$!
    cd ..
    sleep 1
fi

echo -e "\n${BLUE}================================${NC}"
echo -e "${GREEN}✓ NestScope is running!${NC}"
echo -e "${BLUE}================================${NC}"
echo -e "\n${GREEN}Backend:${NC}     http://localhost:8000"
echo -e "${GREEN}Frontend:${NC}    http://localhost:8501"
if [ ! -z "$LABELLER_PID" ]; then
    echo -e "${GREEN}Nestperts:${NC}   http://localhost:5000"
fi
echo -e "${GREEN}API Docs:${NC}    http://localhost:8000/docs"
echo -e "\n${YELLOW}Logs:${NC}"
echo -e "  Backend:  tail -f logs/server.log"
echo -e "  Webapp:   tail -f logs/webapp.log"
if [ ! -z "$LABELLER_PID" ]; then
    echo -e "  Nestperts: tail -f logs/nestperts.log"
fi
echo -e "\n${YELLOW}Press Ctrl+C to stop all servers${NC}\n"

# Wait for processes
wait
