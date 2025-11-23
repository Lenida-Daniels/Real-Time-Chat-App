#!/bin/bash

# Real-Time Chat App Startup Script
# This script starts Redis, FastAPI backend, and opens the frontend

echo "🚀 Starting Real-Time Chat Application..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check if a port is in use
port_in_use() {
    lsof -i :$1 >/dev/null 2>&1
}

echo -e "${BLUE}📋 Checking prerequisites...${NC}"

# Check Redis
if command_exists redis-server; then
    echo -e "${GREEN}✅ Redis is installed${NC}"
else
    echo -e "${RED}❌ Redis is not installed${NC}"
    echo -e "${YELLOW}Please install Redis first:${NC}"
    echo "  Ubuntu/Debian: sudo apt install redis-server"
    echo "  macOS: brew install redis"
    echo "  Windows: Install Memurai from https://www.memurai.com/"
    exit 1
fi

# Check Python
if command_exists python3; then
    echo -e "${GREEN}✅ Python 3 is installed${NC}"
else
    echo -e "${RED}❌ Python 3 is not installed${NC}"
    echo -e "${YELLOW}Please install Python 3 first${NC}"
    exit 1
fi

# Start Redis if not running
echo -e "${BLUE}🔴 Starting Redis server...${NC}"
if port_in_use 6379; then
    echo -e "${YELLOW}⚠️  Redis is already running on port 6379${NC}"
else
    redis-server --daemonize yes --port 6379
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Redis server started successfully${NC}"
    else
        echo -e "${RED}❌ Failed to start Redis server${NC}"
        exit 1
    fi
fi

# Test Redis connection
echo -e "${BLUE}🔍 Testing Redis connection...${NC}"
redis-cli ping >/dev/null 2>&1
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Redis connection successful${NC}"
else
    echo -e "${RED}❌ Cannot connect to Redis${NC}"
    exit 1
fi

# Setup Python virtual environment
echo -e "${BLUE}🐍 Setting up Python environment...${NC}"
cd backend

if [ ! -d "venv" ]; then
    echo -e "${YELLOW}📦 Creating virtual environment...${NC}"
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo -e "${BLUE}📦 Installing Python dependencies...${NC}"
pip install -r requirements.txt

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Failed to install Python dependencies${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Python dependencies installed${NC}"

# Start FastAPI backend
echo -e "${BLUE}🚀 Starting FastAPI backend server...${NC}"

if port_in_use 8000; then
    echo -e "${YELLOW}⚠️  Port 8000 is already in use${NC}"
    echo -e "${YELLOW}Stopping existing process...${NC}"
    pkill -f "uvicorn main:app" 2>/dev/null
    sleep 2
fi

# Go back to root directory first
cd ..

# Create logs directory if it doesn't exist
mkdir -p logs

# Go back to backend directory
cd backend

# Start the backend server in background
nohup uvicorn main:app --host 0.0.0.0 --port 8000 --reload > ../logs/backend.log 2>&1 &
BACKEND_PID=$!

# Wait a moment for server to start
sleep 3

# Check if backend is running
if port_in_use 8000; then
    echo -e "${GREEN}✅ FastAPI backend started successfully (PID: $BACKEND_PID)${NC}"
else
    echo -e "${RED}❌ Failed to start FastAPI backend${NC}"
    exit 1
fi

# Go back to root directory
cd ..

# Start frontend HTTP server
echo -e "${BLUE}🌐 Starting frontend server...${NC}"
cd frontend
nohup python3 -m http.server 3000 > ../logs/frontend.log 2>&1 &
FRONTEND_PID=$!
cd ..

# Wait for frontend server to start
sleep 2

# Check if frontend is running
if port_in_use 3000; then
    echo -e "${GREEN}✅ Frontend server started on port 3000${NC}"
else
    echo -e "${RED}❌ Failed to start frontend server${NC}"
fi

# Open frontend in browser
echo -e "${BLUE}🌐 Opening chat application in browser...${NC}"
if command_exists xdg-open; then
    # Linux
    xdg-open "http://localhost:3000"
elif command_exists open; then
    # macOS
    open "http://localhost:3000"
elif command_exists start; then
    # Windows (Git Bash)
    start "http://localhost:3000"
else
    echo -e "${YELLOW}⚠️  Could not auto-open browser${NC}"
    echo -e "${BLUE}Please manually open: http://localhost:3000${NC}"
fi

echo ""
echo -e "${GREEN}🎉 Real-Time Chat Application is now running!${NC}"
echo ""
echo -e "${BLUE}📡 Services:${NC}"
echo -e "  • Redis Server: ${GREEN}localhost:6379${NC}"
echo -e "  • FastAPI Backend: ${GREEN}http://localhost:8000${NC}"
echo -e "  • API Documentation: ${GREEN}http://localhost:8000/docs${NC}"
echo -e "  • Frontend Application: ${GREEN}http://localhost:3000${NC}"
echo ""
echo -e "${BLUE}📋 Useful Commands:${NC}"
echo -e "  • View backend logs: ${YELLOW}tail -f logs/backend.log${NC}"
echo -e "  • View frontend logs: ${YELLOW}tail -f logs/frontend.log${NC}"
echo -e "  • Stop all services: ${YELLOW}pkill -f uvicorn && pkill -f 'python.*http.server'${NC}"
echo -e "  • Stop Redis: ${YELLOW}redis-cli shutdown${NC}"
echo -e "  • Test API: ${YELLOW}curl http://localhost:8000${NC}"
echo ""
echo -e "${BLUE}🔧 Troubleshooting:${NC}"
echo -e "  • If connection fails, check that Redis and FastAPI are running"
echo -e "  • Check logs in the 'logs' directory for error details"
echo -e "  • Ensure ports 6379 (Redis) and 8000 (FastAPI) are not blocked"
echo ""
echo -e "${GREEN}Press Ctrl+C to stop all services${NC}"

# Keep script running and handle Ctrl+C
trap 'echo -e "\n${YELLOW}🛑 Stopping services...${NC}"; pkill -f "uvicorn main:app"; pkill -f "python.*http.server"; redis-cli shutdown 2>/dev/null; echo -e "${GREEN}✅ All services stopped${NC}"; exit 0' INT

# Wait for user to stop
while true; do
    sleep 1
done