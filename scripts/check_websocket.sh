#!/bin/bash

echo "🔍 Checking FinSentinel AI WebSocket Service..."

# Check if process is running
if pgrep -f "python.*demo_server.py" > /dev/null; then
    echo "✅ Process running"
    PID=$(pgrep -f "python.*demo_server.py" | head -1)
    echo "   PID: $PID"
else
    echo "❌ Process not running"
    exit 1
fi

# Check HTTP endpoint
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ HTTP endpoint responding"
    curl -s http://localhost:8000/health | jq .
else
    echo "❌ HTTP endpoint not responding"
fi

# Check WebSocket status
if curl -s http://localhost:8000/api/v1/ws/status > /dev/null 2>&1; then
    echo "✅ WebSocket status endpoint responding"
    curl -s http://localhost:8000/api/v1/ws/status | jq .
else
    echo "⚠️  WebSocket status endpoint not available"
fi

echo ""
echo "📊 Service URLs:"
echo "   API: http://localhost:8000"
echo "   WebSocket: ws://localhost:8000/ws"
echo "   Docs: http://localhost:8000/docs"
echo "   Dashboard: http://localhost:3000"
