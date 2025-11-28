#!/bin/bash


set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
NETWORK_DIR="$PROJECT_ROOT/fabric-samples/test-network"

echo "🔗 FinSentinel AI - Starting Blockchain Network"
echo "================================================"

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running!"
    echo "Please start Docker Desktop and try again."
    exit 1
fi

echo "✅ Docker is running"

# Navigate to test network
cd "$NETWORK_DIR"

# Clean up any existing network
echo ""
echo "🧹 Cleaning up old network..."
./network.sh down

# Start network with Certificate Authorities
echo ""
echo "🚀 Starting Hyperledger Fabric network..."
./network.sh up createChannel -ca

# Deploy basic chaincode
echo ""
echo "📦 Deploying chaincode..."
./network.sh deployCC -ccn basic -ccp ../asset-transfer-basic/chaincode-go -ccl go

# Verify network status
echo ""
echo "✅ Blockchain network started successfully!"
echo ""
echo "📊 Network Status:"
docker ps --filter "name=peer0\|orderer" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

echo ""
echo "================================================"
echo "✅ Blockchain Ready!"
echo "   Channel: mychannel"
echo "   Chaincode: basic"
echo "   Orderer: localhost:7050"
echo "   Peer Org1: localhost:7051"
echo "   Peer Org2: localhost:9051"
echo ""
echo "💡 Transactions will be automatically recorded to the blockchain"
echo "🔍 Query transactions: ./scripts/query_blockchain.sh"
echo "🛑 Stop network: ./scripts/stop_blockchain.sh"
echo "================================================"
