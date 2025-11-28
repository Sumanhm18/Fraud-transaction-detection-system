#!/bin/bash

# FinSentinel AI - Query Blockchain Transactions
# Retrieves all transactions from Hyperledger Fabric ledger

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
NETWORK_DIR="$PROJECT_ROOT/fabric-samples/test-network"

cd "$NETWORK_DIR"

# Set environment variables for Org1
export CORE_PEER_TLS_ENABLED=true
export CORE_PEER_LOCALMSPID="Org1MSP"
export CORE_PEER_TLS_ROOTCERT_FILE=${PWD}/organizations/peerOrganizations/org1.example.com/tlsca/tlsca.org1.example.com-cert.pem
export CORE_PEER_MSPCONFIGPATH=${PWD}/organizations/peerOrganizations/org1.example.com/users/Admin@org1.example.com/msp
export CORE_PEER_ADDRESS=localhost:7051
export FABRIC_CFG_PATH=${PWD}/../config/

echo "🔍 Querying all blockchain transactions..."
echo ""

../bin/peer chaincode query -C mychannel -n basic -c '{"function":"GetAllAssets","Args":[]}' | jq '.'

echo ""
echo "✅ Query complete!"
