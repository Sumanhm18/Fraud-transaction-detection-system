#!/bin/bash
# Script to view all transactions stored on Hyperledger Fabric blockchain

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📋 HYPERLEDGER FABRIC BLOCKCHAIN TRANSACTION VIEWER"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Method 1: Using Backend API (Easiest)
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "METHOD 1: Backend API"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🔍 Querying all transactions via API..."
echo ""

curl -s "http://localhost:8000/api/v1/blockchain/transactions/all" | jq '{
  success,
  total: .total,
  transactions: [.transactions[] | {
    id,
    merchant: .merchant_name,
    amount,
    date,
    location,
    fraud_analysis: {
      fraud_score,
      risk_level,
      is_anomaly,
      anomaly_type,
      ml_model: .ml_model_version
    },
    blockchain_metadata: {
      recorded_at,
      recorded_by
    }
  }]
}'

echo ""
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "METHOD 2: Direct Peer CLI Query"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Command to run manually:"
echo ""
echo "cd /Users/sumanhm/Downloads/finance/fabric-samples/test-network"
echo ""
echo "# Set Org1 environment"
echo 'export CORE_PEER_TLS_ENABLED=true'
echo 'export CORE_PEER_LOCALMSPID="Org1MSP"'
echo 'export CORE_PEER_TLS_ROOTCERT_FILE=${PWD}/organizations/peerOrganizations/org1.example.com/tlsca/tlsca.org1.example.com-cert.pem'
echo 'export CORE_PEER_MSPCONFIGPATH=${PWD}/organizations/peerOrganizations/org1.example.com/users/Admin@org1.example.com/msp'
echo 'export CORE_PEER_ADDRESS=localhost:7051'
echo 'export FABRIC_CFG_PATH=${PWD}/../config/'
echo ""
echo "# Query all transactions"
echo "../bin/peer chaincode query -C finsentinel-channel -n fraud-detector -c '{\"function\":\"GetAllTransactions\",\"Args\":[]}' | jq ."
echo ""
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "OTHER USEFUL QUERIES:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "# Get specific transaction:"
echo 'curl "http://localhost:8000/api/v1/blockchain/transaction/<TRANSACTION_ID>" | jq .'
echo ""
echo "# Get blockchain status:"
echo 'curl "http://localhost:8000/api/v1/blockchain/status" | jq .'
echo ""
echo "# Query high-risk transactions (fraud_score > 0.7):"
echo "../bin/peer chaincode query -C finsentinel-channel -n fraud-detector -c '{\"function\":\"GetHighRiskTransactions\",\"Args\":[\"0.7\"]}' | jq ."
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
