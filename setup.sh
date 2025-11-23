#!/bin/bash

echo "🚀 Setting up Real-Time Chat App Environment"

# Backend setup
echo "📦 Setting up backend virtual environment..."
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
echo "✅ Backend dependencies installed"

# Redis setup instructions
echo "🔴 Redis Setup Required:"
echo "Run: sudo apt install redis-server"
echo "Then: redis-server"
echo "Test: redis-cli ping"

echo "🎉 Setup complete! Next steps:"
echo "1. Install Redis: sudo apt install redis-server"
echo "2. Start Redis: redis-server"
echo "3. Activate backend: cd backend && source venv/bin/activate"
echo "4. Run backend: uvicorn main:app --reload"