#!/bin/bash

# NestScope - Run both FastAPI server and Streamlit client concurrently

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Detect Python command and verify version
detect_python() {
    # Check if we're in a virtual environment (highest priority)
    if [ ! -z "$VIRTUAL_ENV" ] && command -v python &> /dev/null; then
        echo "python"
        return
    fi

    # Try common Python commands in order of preference
    for cmd in python3.13 python3.12 python3.11 python3.10 python3.9 python3.8 python3 python; do
        if command -v $cmd &> /dev/null; then
            # Verify it's Python 3.8+
            version=$($cmd -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null)
            if [ $? -eq 0 ]; then
                major=$(echo $version | cut -d. -f1)
                minor=$(echo $version | cut -d. -f2)
                if [ "$major" -ge 3 ] && [ "$minor" -ge 8 ]; then
                    echo $cmd
                    return
                fi
            fi
        fi
    done

    return 1
}

PYTHON_CMD=$(detect_python)
if [ -z "$PYTHON_CMD" ]; then
    echo -e "${RED}Error: Python 3.8+ not found${NC}"
    echo -e "${YELLOW}Please install Python 3.8 or higher${NC}"
    echo -e "${YELLOW}Visit: https://www.python.org/downloads/${NC}"
    exit 1
fi

# Verify Python version display
PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | grep -oP '\d+\.\d+\.\d+')
if [ -z "$PYTHON_VERSION" ]; then
    PYTHON_VERSION="unknown"
fi

echo -e "${BLUE}================================${NC}"
echo -e "${BLUE}   NestScope Startup Script     ${NC}"
echo -e "${BLUE}================================${NC}\n"

if [ ! -z "$VIRTUAL_ENV" ]; then
    echo -e "${GREEN}✓ Virtual environment detected${NC}"
fi
echo -e "${GREEN}✓ Using Python: ${PYTHON_CMD} (${PYTHON_VERSION})${NC}"

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
    echo -e "${YELLOW}Please run: ${PYTHON_CMD} scripts/import_all_to_sqlite.py${NC}"
    exit 1
fi

# Check if required packages are installed
echo -e "${YELLOW}Checking dependencies...${NC}"
MISSING_DEPS=()

if ! $PYTHON_CMD -c "import fastapi" &> /dev/null; then
    MISSING_DEPS+=("fastapi")
fi
if ! $PYTHON_CMD -c "import uvicorn" &> /dev/null; then
    MISSING_DEPS+=("uvicorn")
fi
if ! $PYTHON_CMD -c "import streamlit" &> /dev/null; then
    MISSING_DEPS+=("streamlit")
fi

if [ ${#MISSING_DEPS[@]} -gt 0 ]; then
    echo -e "${RED}Error: Missing required packages: ${MISSING_DEPS[*]}${NC}"
    echo -e "${YELLOW}Install with: ${PYTHON_CMD} -m pip install -r requirements.txt${NC}"
    exit 1
fi

echo -e "${GREEN}✓ All dependencies installed${NC}"

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
$PYTHON_CMD -m uvicorn server.main:app --host 0.0.0.0 --port 8000 --reload > logs/server.log 2>&1 &
SERVER_PID=$!

# Wait for server to start with retry logic
echo -e "${YELLOW}Waiting for server to start...${NC}"
MAX_RETRIES=10
RETRY_COUNT=0
SERVER_READY=false

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    sleep 2
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Server health check passed${NC}"
        SERVER_READY=true
        break
    fi
    RETRY_COUNT=$((RETRY_COUNT + 1))
    echo -e "${YELLOW}  Retry $RETRY_COUNT/$MAX_RETRIES...${NC}"
done

if [ "$SERVER_READY" = false ]; then
    echo -e "${RED}⚠ Server health check failed after $MAX_RETRIES attempts${NC}"
    echo -e "${YELLOW}Check logs: tail -f logs/server.log${NC}"
    echo -e "${YELLOW}Continuing anyway...${NC}"
fi

# Start Streamlit client in background
echo -e "${GREEN}Starting Streamlit client on http://localhost:8501${NC}"
$PYTHON_CMD -m streamlit run frontend/app/app_ui.py --server.port 8501 > logs/streamlit.log 2>&1 &
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

