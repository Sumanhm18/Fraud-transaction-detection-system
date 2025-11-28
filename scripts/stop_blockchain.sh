#!/bin/bash

# FinSentinel AI - Stop Blockchain Network
# Safely shuts down Hyperledger Fabric network

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
NETWORK_DIR="$PROJECT_ROOT/fabric-samples/test-network"

echo "🛑 Stopping Hyperledger Fabric blockchain network..."
echo ""

cd "$NETWORK_DIR"
./network.sh down

echo ""
echo "✅ Blockchain network stopped successfully!"
echo "   All containers removed"
echo "   Volumes cleaned up"
echo ""
echo "💡 To restart: ./scripts/start_blockchain.sh"
