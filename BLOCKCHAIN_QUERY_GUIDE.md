# 📋 Blockchain Transaction Query Guide

## Overview

This guide explains how to view all transactions stored on the Hyperledger Fabric blockchain in FinSentinel AI.

---

## 🎯 Quick Start

### Easiest Method: Backend API

```bash
curl "http://localhost:8000/api/v1/blockchain/transactions/all" | jq .
```

---

## 📚 Methods to View Blockchain Transactions

### Method 1: Backend API Endpoint (Recommended)

**Get All Transactions:**

```bash
curl "http://localhost:8000/api/v1/blockchain/transactions/all" | jq .
```

**Response Format:**

```json
{
  "success": true,
  "total": 15,
  "transactions": [
    {
      "id": "manual_tx_1763168481.87162",
      "account_id": "acc_1",
      "amount": -75.5,
      "merchant_name": "Real-Time Test Store",
      "category": ["Shopping"],
      "date": "2025-11-15",
      "transaction_type": "debit",
      "location": "New York",
      "payment_method": "card",
      "fraud_score": 0.05,
      "risk_level": "LOW",
      "risk_factors": [],
      "ml_model_version": "ML-Model-v1.0",
      "is_anomaly": false,
      "anomaly_type": "NORMAL",
      "recorded_at": "2025-11-15T01:01:21Z",
      "recorded_by": "FinSentinel-AI"
    }
  ]
}
```

**Get Specific Transaction:**

```bash
curl "http://localhost:8000/api/v1/blockchain/transaction/<TRANSACTION_ID>" | jq .
```

**Get Blockchain Status:**

```bash
curl "http://localhost:8000/api/v1/blockchain/status" | jq .
```

---

### Method 2: Direct Peer CLI Command

**Setup Environment (Org1):**

```bash
cd /Users/sumanhm/Downloads/finance/fabric-samples/test-network

export CORE_PEER_TLS_ENABLED=true
export CORE_PEER_LOCALMSPID="Org1MSP"
export CORE_PEER_TLS_ROOTCERT_FILE=${PWD}/organizations/peerOrganizations/org1.example.com/tlsca/tlsca.org1.example.com-cert.pem
export CORE_PEER_MSPCONFIGPATH=${PWD}/organizations/peerOrganizations/org1.example.com/users/Admin@org1.example.com/msp
export CORE_PEER_ADDRESS=localhost:7051
export FABRIC_CFG_PATH=${PWD}/../config/
```

**Query All Transactions:**

```bash
../bin/peer chaincode query \
  -C finsentinel-channel \
  -n fraud-detector \
  -c '{"function":"GetAllTransactions","Args":[]}' | jq .
```

**Query Specific Transaction:**

```bash
../bin/peer chaincode query \
  -C finsentinel-channel \
  -n fraud-detector \
  -c '{"function":"GetTransaction","Args":["<TRANSACTION_ID>"]}' | jq .
```

**Query High-Risk Transactions:**

```bash
# Fraud score > 0.7
../bin/peer chaincode query \
  -C finsentinel-channel \
  -n fraud-detector \
  -c '{"function":"GetHighRiskTransactions","Args":["0.7"]}' | jq .
```

---

### Method 3: Using the Helper Script

**Run the viewer script:**

```bash
cd /Users/sumanhm/Downloads/finance
./view_blockchain_transactions.sh
```

This script displays all transactions with formatted output.

---

## 🔍 Advanced Queries

### Filter by Fraud Score

```bash
# Get all transactions and filter by fraud score > 0.5
curl -s "http://localhost:8000/api/v1/blockchain/transactions/all" | \
  jq '[.transactions[] | select(.fraud_score > 0.5)]'
```

### Filter by Date

```bash
# Get transactions from a specific date
curl -s "http://localhost:8000/api/v1/blockchain/transactions/all" | \
  jq '[.transactions[] | select(.date == "2025-11-15")]'
```

### Filter by Merchant

```bash
# Get transactions from specific merchant
curl -s "http://localhost:8000/api/v1/blockchain/transactions/all" | \
  jq '[.transactions[] | select(.merchant_name == "Walmart")]'
```

### Count Transactions by Risk Level

```bash
curl -s "http://localhost:8000/api/v1/blockchain/transactions/all" | \
  jq '.transactions | group_by(.risk_level) | map({risk_level: .[0].risk_level, count: length})'
```

---

## 📊 Available Chaincode Functions

The `fraud-detector` chaincode provides these query functions:

| Function                  | Description                            | Args                      |
| ------------------------- | -------------------------------------- | ------------------------- |
| `GetTransaction`          | Get single transaction by ID           | `[transaction_id]`        |
| `GetAllTransactions`      | Get all transactions                   | `[]`                      |
| `GetHighRiskTransactions` | Get transactions above fraud threshold | `[fraud_score_threshold]` |
| `GetFraudAlert`           | Get fraud alert by ID                  | `[alert_id]`              |

---

## 🛠️ Transaction Data Structure

Each transaction on the blockchain contains:

- **Transaction Details:**

  - `id`: Unique transaction identifier
  - `account_id`: Account identifier
  - `amount`: Transaction amount
  - `merchant_name`: Merchant name
  - `category`: Transaction category
  - `date`: Transaction date
  - `transaction_type`: debit/credit
  - `location`: Transaction location
  - `payment_method`: Payment method used

- **ML Fraud Analysis:**

  - `fraud_score`: ML model fraud score (0-1)
  - `risk_level`: HIGH/MEDIUM/LOW
  - `risk_factors`: Array of detected risk factors
  - `is_anomaly`: Boolean flag
  - `anomaly_type`: Type of anomaly detected
  - `ml_model_version`: Version of ML model used

- **Blockchain Metadata:**
  - `recorded_at`: Timestamp when recorded on blockchain
  - `recorded_by`: System that recorded the transaction

---

## 🔐 Security Notes

- All blockchain queries use TLS encryption
- Queries are authenticated via MSP (Membership Service Provider)
- Read-only queries don't modify the blockchain ledger
- Transaction data is immutable once recorded

---

## 📈 Performance Tips

1. **Use API endpoint for frequent queries** - It's faster and includes caching
2. **Filter on the client side** - Get all transactions once, then filter locally
3. **Use specific queries** - `GetTransaction` is faster than `GetAllTransactions`
4. **High-risk queries** - Use `GetHighRiskTransactions` for fraud analysis

---

## 🆘 Troubleshooting

**"Connection refused" error:**

```bash
# Check if Hyperledger Fabric network is running
docker ps | grep -E "peer|orderer"
```

**"Chaincode not found" error:**

```bash
# Verify chaincode is deployed
cd /Users/sumanhm/Downloads/finance/fabric-samples/test-network
../bin/peer lifecycle chaincode queryinstalled
```

**Empty result:**

```bash
# Check if transactions are being recorded
tail -f /Users/sumanhm/Downloads/finance/backend/server.log | grep "⛓️"
```

---

## 📝 Examples

### Example 1: View Summary of All Transactions

```bash
curl -s "http://localhost:8000/api/v1/blockchain/transactions/all" | \
  jq '{
    total: .total,
    by_risk_level: (.transactions | group_by(.risk_level) |
      map({risk: .[0].risk_level, count: length})),
    avg_fraud_score: (.transactions | map(.fraud_score) | add / length)
  }'
```

### Example 2: Find Anomalous Transactions

```bash
curl -s "http://localhost:8000/api/v1/blockchain/transactions/all" | \
  jq '[.transactions[] | select(.is_anomaly == true) | {
    id,
    merchant: .merchant_name,
    amount,
    fraud_score,
    anomaly_type
  }]'
```

### Example 3: Recent Transactions

```bash
curl -s "http://localhost:8000/api/v1/blockchain/transactions/all" | \
  jq '[.transactions | sort_by(.recorded_at) | reverse | .[0:10]]'
```

---

## 🔗 Related Documentation

- [HYPERLEDGER_INTEGRATION.md](HYPERLEDGER_INTEGRATION.md) - Complete blockchain integration guide
- [README.md](README.md) - Project overview
- [SETUP.md](SETUP.md) - Initial setup instructions

---

## 💡 Quick Reference Commands

```bash
# View all transactions (API)
curl "http://localhost:8000/api/v1/blockchain/transactions/all" | jq .

# View specific transaction
curl "http://localhost:8000/api/v1/blockchain/transaction/tx_1" | jq .

# Run helper script
./view_blockchain_transactions.sh

# Direct peer query
cd fabric-samples/test-network && \
  ../bin/peer chaincode query -C finsentinel-channel -n fraud-detector \
  -c '{"function":"GetAllTransactions","Args":[]}' | jq .

# Count total transactions
curl -s "http://localhost:8000/api/v1/blockchain/transactions/all" | jq '.total'

# View high fraud score transactions
curl -s "http://localhost:8000/api/v1/blockchain/transactions/all" | \
  jq '[.transactions[] | select(.fraud_score > 0.6)]'
```
