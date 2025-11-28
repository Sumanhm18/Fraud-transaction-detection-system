#!/bin/bash

set -e

echo "🚀 Starting FinSentinel AI WebSocket Service..."

# Navigate to project directory
cd /Users/sumanhm/Downloads/finance

# Activate virtual environment
if [ -f "backend/venv/bin/activate" ]; then
    source backend/venv/bin/activate
elif [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
else
    echo "❌ Virtual environment not found. Creating one..."
    python3 -m venv backend/venv
    source backend/venv/bin/activate
    pip install -r backend/requirements.txt
fi

# Set environment variables
export PYTHONPATH=/Users/sumanhm/Downloads/finance/backend
export REDIS_URL=${REDIS_URL:-redis://localhost:6379/0}
export DATABASE_URL=${DATABASE_URL:-sqlite:///./finsentinel.db}
export WS_PORT=${WS_PORT:-8000}

# Kill existing processes
echo "🔄 Stopping existing services..."
pkill -f "uvicorn.*demo_server:app" || true
pkill -f "python.*demo_server.py" || true
sleep 2

# Check Redis is running (optional)
echo "⏳ Checking Redis..."
if ! redis-cli ping > /dev/null 2>&1; then
    echo "⚠️  Redis not running. Some features may be limited."
else
    echo "✅ Redis is ready"
fi

# Create logs directory
mkdir -p /Users/sumanhm/Downloads/finance/logs

# Start the backend with WebSocket support
echo "🚀 Starting FastAPI with WebSocket..."
cd /Users/sumanhm/Downloads/finance/backend

nohup python demo_server.py \
    > /Users/sumanhm/Downloads/finance/logs/websocket.log 2>&1 &

PYTHON_PID=$!
echo $PYTHON_PID > /tmp/finsentinel-ws.pid

sleep 3

# Verify server is running
if ps -p $PYTHON_PID > /dev/null; then
    echo "✅ WebSocket service started successfully (PID: $PYTHON_PID)"
    echo "📊 API: http://localhost:${WS_PORT}"
    echo "🔌 WebSocket: ws://localhost:${WS_PORT}/ws"
    echo "📝 Logs: tail -f /Users/sumanhm/Downloads/finance/logs/websocket.log"
    echo ""
    echo "Opening logs..."
    tail -f /Users/sumanhm/Downloads/finance/logs/websocket.log
else
    echo "❌ Failed to start WebSocket service"
    cat /Users/sumanhm/Downloads/finance/logs/websocket.log
    exit 1
fi
