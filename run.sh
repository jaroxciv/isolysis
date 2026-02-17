#!/usr/bin/env bash
# run.sh - Isolysis Development Environment

# Colors for output
GREEN="\033[32m"
YELLOW="\033[33m"
RED="\033[31m"
RESET="\033[0m"

echo -e "${GREEN}🚀 Starting Isolysis Development Environment${RESET}"

# Check if .venv exists
if [ ! -d ".venv" ]; then
    echo -e "${RED}❌ No .venv directory found. Please create virtual environment first.${RESET}"
    exit 1
fi

# Activate virtual environment
echo -e "${YELLOW}📦 Activating virtual environment...${RESET}"
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
else
    echo -e "${RED}❌ Could not find virtual environment activation script${RESET}"
    exit 1
fi

# Track process PIDs
API_PID=""
RASTER_PID=""

# Cleanup function
cleanup() {
    echo -e "\n${YELLOW}🛑 Shutting down services...${RESET}"
    if [ -n "$API_PID" ] && kill -0 "$API_PID" 2>/dev/null; then
        kill "$API_PID"
        echo -e "${GREEN}✅ API server stopped${RESET}"
    fi
    if [ -n "$RASTER_PID" ] && kill -0 "$RASTER_PID" 2>/dev/null; then
        kill "$RASTER_PID"
        echo -e "${GREEN}✅ Raster app stopped${RESET}"
    fi
    exit 0
}

# Trap signals for cleanup
trap cleanup SIGINT SIGTERM EXIT

# Start API server in background
echo -e "${YELLOW}🔧 Starting API server...${RESET}"
uv run uvicorn api.app:app --reload --port 8000 &
API_PID=$!

# Wait for API to start
echo -e "${YELLOW}⏳ Waiting for API server to start...${RESET}"
sleep 3

# Check if API is running
if curl -s --max-time 5 http://localhost:8000/health > /dev/null 2>&1; then
    echo -e "${GREEN}✅ API server running on http://localhost:8000${RESET}"
    echo -e "${GREEN}📖 API docs available at http://localhost:8000/docs${RESET}"
else
    echo -e "${RED}❌ API server failed to start or health check failed${RESET}"
    cleanup
fi

# Start Raster Streamlit app in background
echo -e "${YELLOW}🗺️ Starting Raster app...${RESET}"
uv run streamlit run st_raster_app.py --server.port 8502 &
RASTER_PID=$!
echo -e "${GREEN}🌐 Raster app at http://localhost:8502${RESET}"

# Start Isochrone Streamlit app (blocks until stopped)
echo -e "${YELLOW}🎨 Starting Isochrone app...${RESET}"
echo -e "${GREEN}🌐 Isochrone app at http://localhost:8501${RESET}"
echo -e "${YELLOW}Press Ctrl+C to stop all services${RESET}"

uv run streamlit run st_app.py
