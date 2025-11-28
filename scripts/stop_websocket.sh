#!/bin/bash

set -e

echo "🛑 Stopping FinSentinel AI WebSocket Service..."

# Kill by PID file
if [ -f /tmp/finsentinel-ws.pid ]; then
    PID=$(cat /tmp/finsentinel-ws.pid)
    if ps -p $PID > /dev/null 2>&1; then
        kill $PID
        echo "✅ Stopped WebSocket service (PID: $PID)"
    fi
    rm /tmp/finsentinel-ws.pid
fi

# Kill any remaining processes
pkill -f "uvicorn.*demo_server:app" || true
pkill -f "python.*demo_server.py" || true

echo "✅ WebSocket service stopped"
