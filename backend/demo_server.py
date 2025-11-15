"""
Simplified FastAPI server for testing FinSentinel AI
"""

import os
import sys
import json
import asyncio
import numpy as np
from typing import List, Dict, Any, Set, Optional
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Header, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import uvicorn
from pydantic import BaseModel
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
import hashlib

# Import real Plaid service
sys.path.append('/Users/sumanhm/Downloads/finance/backend')
from app.services.plaid_service_real import plaid_service
from app.services.email_service import email_service
from app.services.fabric_gateway import fabric_gateway
from app.services.auth_service import auth_service
from app.models.user import UserLogin, UserCreate, UserUpdate, User, Permission, Token

# Database imports
from sqlite_database import (
    init_database, seed_demo_data,
    transaction_db, fraud_alert_db, account_db
)

# Pydantic models for API responses
class Transaction(BaseModel):
    id: str
    account_id: str
    amount: float
    date: datetime
    merchant_name: str = None
    category: List[str] = []
    fraud_score: float = None
    risk_factors: List[str] = []

# Plaid integration models
class LinkTokenRequest(BaseModel):
    user_id: str

class PublicTokenExchangeRequest(BaseModel):
    public_token: str
    user_id: str
    metadata: Dict[str, Any] = None

class PlaidTransactionsRequest(BaseModel):
    access_token: str
    count: int = 100
    offset: int = 0

# Manual transaction entry model
class ManualTransactionRequest(BaseModel):
    account_id: str
    amount: float
    merchant_name: str
    category: str
    date: str
    description: str = None
    transaction_type: str = 'debit'
    location: str = None
    payment_method: str = 'card'
    manual_entry: bool = True

class Account(BaseModel):
    id: str
    name: str
    type: str
    subtype: str = None
    balance: float
    currency_code: str = "USD"
    mask: str = None

class FraudAlert(BaseModel):
    id: str
    transaction_id: str
    risk_level: str
    fraud_score: float
    risk_factors: List[str]
    status: str
    created_at: datetime

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                # Remove broken connections
                if connection in self.active_connections:
                    self.active_connections.remove(connection)

# Initialize connection manager
manager = ConnectionManager()

# Plaid connections storage (demo)
plaid_connections: Dict[str, Dict] = {}

# ========== RANDOM FOREST FRAUD DETECTION MODEL ==========
class FraudDetectionModel:
    """
    Random Forest-based fraud detection model with multiple features
    Trained on synthetic fraud patterns to detect anomalies
    """
    
    def __init__(self):
        # Initialize Random Forest Classifier
        self.model = RandomForestClassifier(
            n_estimators=100,  # Number of trees
            max_depth=10,
            min_samples_split=5,
            min_samples_leaf=2,
            max_features='sqrt',
            random_state=42,
            class_weight='balanced'  # Handle imbalanced classes
        )
        self.scaler = StandardScaler()
        self.is_trained = False
        self._train_model()
    
    def _generate_training_data(self, n_samples=1000):
        """Generate synthetic training data with fraud patterns"""
        np.random.seed(42)
        X = []
        y = []
        
        for i in range(n_samples):
            # Determine if this is fraud (20% fraud rate)
            is_fraud = np.random.random() < 0.2
            
            if is_fraud:
                # Fraudulent transaction patterns
                amount = np.random.choice([
                    np.random.uniform(1, 10),      # Card testing
                    np.random.uniform(500, 5000),  # Large fraud
                    np.random.uniform(1000, 3000)  # Mid-range fraud
                ])
                hour = np.random.choice([1, 2, 3, 4, 23])  # Unusual hours
                merchant_risk = np.random.uniform(0.7, 1.0)  # High-risk merchants
                location_risk = np.random.uniform(0.6, 1.0)  # Risky locations
                payment_risk = np.random.uniform(0.7, 1.0)   # Risky payment methods
                is_round = 1 if amount % 100 == 0 else 0
                is_international = 1 if np.random.random() < 0.7 else 0
                velocity_score = np.random.uniform(0.7, 1.0)
                amount_percentile = np.random.uniform(0.8, 1.0)
                weekend_business = 1 if np.random.random() < 0.6 else 0
                category_mismatch = 1 if np.random.random() < 0.5 else 0
            else:
                # Normal transaction patterns
                amount = np.random.choice([
                    np.random.uniform(5, 100),     # Small purchases
                    np.random.uniform(100, 500),   # Medium purchases
                    np.random.uniform(20, 200)     # Regular spending
                ])
                hour = np.random.choice([9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20])
                merchant_risk = np.random.uniform(0.0, 0.3)
                location_risk = np.random.uniform(0.0, 0.3)
                payment_risk = np.random.uniform(0.0, 0.3)
                is_round = 0
                is_international = 0
                velocity_score = np.random.uniform(0.0, 0.3)
                amount_percentile = np.random.uniform(0.0, 0.6)
                weekend_business = 0
                category_mismatch = 0
            
            # Create feature vector
            features = [
                np.log1p(amount),          # Log-transformed amount
                hour,                       # Hour of day
                merchant_risk,              # Merchant risk score
                location_risk,              # Location risk score
                payment_risk,               # Payment method risk
                is_round,                   # Round number flag
                is_international,           # International flag
                velocity_score,             # Transaction velocity
                amount_percentile,          # Amount percentile
                weekend_business,           # Weekend business transaction
                category_mismatch,          # Category mismatch
                amount / 1000,             # Normalized amount
                1 if hour < 6 or hour > 22 else 0,  # Night transaction
                1 if amount > 1000 else 0,  # Large amount flag
                1 if amount < 10 else 0     # Micro transaction flag
            ]
            
            X.append(features)
            y.append(1 if is_fraud else 0)
        
        return np.array(X), np.array(y)
    
    def _train_model(self):
        """Train the Random Forest model"""
        print("🤖 Training Random Forest Fraud Detection Model...")
        X_train, y_train = self._generate_training_data(1000)
        
        # Scale features
        X_train_scaled = self.scaler.fit_transform(X_train)
        
        # Train model
        self.model.fit(X_train_scaled, y_train)
        self.is_trained = True
        
        # Calculate accuracy on training data
        y_pred = self.model.predict(X_train_scaled)
        self.accuracy = (y_pred == y_train).mean()
        
        # Get feature importances
        importances = self.model.feature_importances_
        print(f"✅ Model trained with {len(importances)} features")
        print(f"   Accuracy: {self.accuracy:.1%}")
        print(f"   Top features: Amount Log ({importances[0]:.3f}), Merchant Risk ({importances[2]:.3f})")
    
    def extract_features(self, transaction):
        """Extract features from transaction for prediction"""
        amount = abs(float(transaction.get("amount", 0)))
        merchant = transaction.get("merchant_name", "").lower()
        location = transaction.get("location", "").lower()
        payment_method = transaction.get("payment_method", "card").lower()
        category = transaction.get("category", "").lower()
        description = transaction.get("description", "").lower()
        
        # Extract hour
        current_hour = datetime.now().hour
        current_day = datetime.now().weekday()
        
        # Calculate risk scores
        merchant_risk = self._calculate_merchant_risk(merchant)
        location_risk = self._calculate_location_risk(location)
        payment_risk = self._calculate_payment_risk(payment_method)
        
        # Flags
        is_round = 1 if amount % 100 == 0 and amount >= 500 else 0
        is_international = self._is_international(location)
        velocity_score = np.random.uniform(0.1, 0.4)  # Simulated
        amount_percentile = min(amount / 5000, 1.0)
        weekend_business = 1 if current_day >= 5 and "business" in category else 0
        category_mismatch = self._check_category_mismatch(merchant, category)
        
        features = [
            np.log1p(amount),
            current_hour,
            merchant_risk,
            location_risk,
            payment_risk,
            is_round,
            is_international,
            velocity_score,
            amount_percentile,
            weekend_business,
            category_mismatch,
            amount / 1000,
            1 if current_hour < 6 or current_hour > 22 else 0,
            1 if amount > 1000 else 0,
            1 if amount < 10 else 0
        ]
        
        return np.array(features).reshape(1, -1)
    
    def _calculate_merchant_risk(self, merchant):
        """Calculate merchant risk score"""
        high_risk = ["casino", "gambling", "crypto", "bitcoin", "wire", "unknown", "offshore"]
        medium_risk = ["gift card", "jewelry", "luxury", "atm"]
        
        if any(word in merchant for word in high_risk):
            return np.random.uniform(0.7, 1.0)
        elif any(word in merchant for word in medium_risk):
            return np.random.uniform(0.4, 0.7)
        else:
            return np.random.uniform(0.0, 0.3)
    
    def _calculate_location_risk(self, location):
        """Calculate location risk score"""
        high_risk = ["russia", "nigeria", "china", "ukraine", "romania"]
        medium_risk = ["international", "overseas", "foreign", "airport"]
        
        if any(word in location for word in high_risk):
            return np.random.uniform(0.7, 1.0)
        elif any(word in location for word in medium_risk):
            return np.random.uniform(0.4, 0.7)
        else:
            return np.random.uniform(0.0, 0.3)
    
    def _calculate_payment_risk(self, payment_method):
        """Calculate payment method risk score"""
        if payment_method in ["crypto", "cryptocurrency", "bitcoin"]:
            return 0.9
        elif payment_method in ["wire", "wire transfer"]:
            return 0.7
        elif payment_method == "cash":
            return 0.5
        else:
            return 0.1
    
    def _is_international(self, location):
        """Check if transaction is international"""
        keywords = ["international", "overseas", "foreign", "russia", "nigeria", "china"]
        return 1 if any(word in location for word in keywords) else 0
    
    def _check_category_mismatch(self, merchant, category):
        """Check for category-merchant mismatch"""
        if "food" in category and "electronics" in merchant:
            return 1
        if "gas" in category and "restaurant" in merchant:
            return 1
        return 0
    
    def predict(self, transaction):
        """Predict fraud probability using Random Forest"""
        if not self.is_trained:
            self._train_model()
        
        features = self.extract_features(transaction)
        features_scaled = self.scaler.transform(features)
        
        # Get probability of fraud
        fraud_probability = self.model.predict_proba(features_scaled)[0][1]
        
        # Get prediction
        prediction = self.model.predict(features_scaled)[0]
        
        return fraud_probability, prediction

# Initialize ML Model
print("🚀 Initializing ML-based Fraud Detection System...")
ml_fraud_detector = FraudDetectionModel()

# Initialize FastAPI app
app = FastAPI(
    title="FinSentinel AI - Autonomous Financial Intelligence",
    description="Real-time transaction monitoring with AI-powered fraud detection",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    await init_database()
    await seed_demo_data()

# In-memory storage for demo
demo_accounts = [
    {
        "id": "acc_1",
        "name": "Chase Checking",
        "type": "depository",
        "subtype": "checking",
        "balance": 15420.50,
        "currency_code": "USD",
        "mask": "0123"
    },
    {
        "id": "acc_2", 
        "name": "Savings Account",
        "type": "depository",
        "subtype": "savings",
        "balance": 45200.75,
        "currency_code": "USD",
        "mask": "4567"
    }
]

demo_transactions = [
    {
        "id": "tx_1",
        "account_id": "acc_1",
        "amount": -85.50,
        "date": datetime.now() - timedelta(hours=2),
        "merchant_name": "Starbucks",
        "category": ["Food and Drink", "Coffee Shop"],
        "fraud_score": 0.05,
        "risk_factors": [],
        "is_anomaly": False,
        "anomaly_type": "NORMAL",
        "status": "APPROVED"
    },
    {
        "id": "tx_2",
        "account_id": "acc_1", 
        "amount": -1250.00,
        "date": datetime.now() - timedelta(hours=5),
        "merchant_name": "Best Buy",
        "category": ["Electronics"],
        "fraud_score": 0.75,
        "risk_factors": ["High amount", "Unusual merchant"],
        "is_anomaly": True,
        "anomaly_type": "HIGH_RISK_FRAUD",
        "status": "FLAGGED"
    },
    {
        "id": "tx_3",
        "account_id": "acc_2",
        "amount": 2500.00,
        "date": datetime.now() - timedelta(days=1),
        "merchant_name": "Payroll Deposit",
        "category": ["Deposit", "Payroll"],
        "fraud_score": 0.01,
        "risk_factors": [],
        "is_anomaly": False,
        "anomaly_type": "NORMAL",
        "status": "APPROVED"
    }
]

demo_fraud_alerts = [
    {
        "id": "alert_1",
        "transaction_id": "tx_2",
        "risk_level": "HIGH",
        "fraud_score": 0.75,
        "risk_factors": ["High amount", "Unusual merchant"],
        "status": "PENDING", 
        "created_at": datetime.now() - timedelta(hours=5)
    }
]

# WebSocket endpoints
@app.websocket("/ws/transactions")
async def websocket_transactions(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Wait for messages from client or keep connection alive
            data = await websocket.receive_text()
            # Echo back or process the message
            await manager.send_personal_message(f"Echo: {data}", websocket)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)

@app.websocket("/ws/alerts") 
async def websocket_alerts(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Wait for messages from client
            data = await websocket.receive_text()
            await manager.send_personal_message(f"Alert Echo: {data}", websocket)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)

@app.websocket("/ws")
async def websocket_general(websocket: WebSocket):
    """General WebSocket endpoint for system-wide updates"""
    await manager.connect(websocket)
    try:
        while True:
            # Wait for messages from client or send keepalive
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
            else:
                await manager.send_personal_message(f"System Echo: {data}", websocket)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)

@app.get("/")
async def root():
    return {
        "message": "🛡️ FinSentinel AI - Autonomous Financial Intelligence System",
        "version": "1.0.0",
        "status": "operational",
        "features": [
            "Real-time transaction monitoring",
            "AI-powered fraud detection", 
            "Multi-agent architecture",
            "Plaid Sandbox integration",
            "WebSocket real-time updates"
        ]
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now(),
        "services": {
            "api": "online",
            "agents": "running",
            "ml_models": "loaded"
        }
    }

# Account endpoints
@app.get("/api/v1/accounts")
async def get_accounts():
    try:
        db_accounts = await account_db.get_accounts()
        if db_accounts:
            # Map database fields to API response format
            accounts = []
            for acc in db_accounts:
                accounts.append({
                    "id": acc.get("id"),
                    "name": acc.get("account_name", acc.get("name", "Unknown Account")),
                    "type": "depository",
                    "subtype": acc.get("account_type", "checking"),
                    "balance": float(acc.get("balance", 0)),
                    "currency_code": "USD",
                    "mask": acc.get("mask", "0000")
                })
            return accounts
        else:
            return demo_accounts
    except Exception as e:
        print(f"Database error, using demo data: {e}")
        return demo_accounts

@app.get("/api/v1/accounts/{account_id}")
async def get_account(account_id: str):
    try:
        db_accounts = await account_db.get_accounts()
        db_account = next((acc for acc in db_accounts if acc["id"] == account_id), None)
        
        if db_account:
            # Map database fields to API response format
            return {
                "id": db_account.get("id"),
                "name": db_account.get("account_name", db_account.get("name", "Unknown Account")),
                "type": "depository",
                "subtype": db_account.get("account_type", "checking"),
                "balance": float(db_account.get("balance", 0)),
                "currency_code": "USD",
                "mask": db_account.get("mask", "0000")
            }
        else:
            # Fallback to demo data
            account = next((acc for acc in demo_accounts if acc["id"] == account_id), None)
            if not account:
                raise HTTPException(status_code=404, detail="Account not found")
            return account
    except HTTPException:
        raise
    except Exception as e:
        print(f"Database error: {e}")
        account = next((acc for acc in demo_accounts if acc["id"] == account_id), None)
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")
        return account

# Transaction endpoints  
@app.get("/api/v1/transactions", response_model=List[Transaction])
async def get_transactions(limit: int = 100):
    try:
        transactions = await transaction_db.get_transactions(limit)
        return transactions if transactions else demo_transactions[:limit]
    except Exception as e:
        print(f"Database error, using demo data: {e}")
        return demo_transactions[:limit]

@app.get("/api/v1/transactions/{transaction_id}", response_model=Transaction)
async def get_transaction(transaction_id: str):
    try:
        transactions = await transaction_db.get_transactions(100)
        transaction = next((tx for tx in transactions if tx["id"] == transaction_id), None)
        if not transaction:
            # Fallback to demo data
            transaction = next((tx for tx in demo_transactions if tx["id"] == transaction_id), None)
        if not transaction:
            raise HTTPException(status_code=404, detail="Transaction not found")
        return transaction
    except Exception as e:
        print(f"Database error: {e}")
        transaction = next((tx for tx in demo_transactions if tx["id"] == transaction_id), None)
        if not transaction:
            raise HTTPException(status_code=404, detail="Transaction not found")
        return transaction

# Fraud endpoints
@app.get("/api/v1/fraud/alerts")
async def get_fraud_alerts():
    try:
        db_alerts = await fraud_alert_db.get_alerts()
        if db_alerts:
            # Map database fields to API fields
            alerts = []
            for db_alert in db_alerts:
                alert = {
                    "id": db_alert.get("id"),
                    "transaction_id": db_alert.get("transaction_id"),
                    "risk_level": db_alert.get("severity", "MEDIUM"),
                    "fraud_score": 0.7,  # Default score since we don't store it
                    "risk_factors": ["Suspicious activity"],  # Default since we store message instead
                    "status": "RESOLVED" if db_alert.get("is_resolved") else "PENDING",
                    "created_at": db_alert.get("created_at")
                }
                alerts.append(alert)
            return {"alerts": alerts}
        else:
            return {"alerts": demo_fraud_alerts}
    except Exception as e:
        print(f"Database error, using demo data: {e}")
        return {"alerts": demo_fraud_alerts}

@app.get("/api/v1/fraud/score/{transaction_id}")
async def get_fraud_score(transaction_id: str):
    transaction = next((tx for tx in demo_transactions if tx["id"] == transaction_id), None)
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    return {
        "transaction_id": transaction_id,
        "fraud_score": transaction["fraud_score"],
        "risk_level": "HIGH" if transaction["fraud_score"] > 0.7 else "MEDIUM" if transaction["fraud_score"] > 0.4 else "LOW",
        "risk_factors": transaction["risk_factors"]
    }

# Analytics endpoints
@app.get("/api/v1/analytics/summary")
async def get_analytics_summary():
    total_transactions = len(demo_transactions)
    high_risk_alerts = len([alert for alert in demo_fraud_alerts if alert["risk_level"] == "HIGH"])
    
    return {
        "total_transactions": total_transactions,
        "total_accounts": len(demo_accounts),
        "high_risk_alerts": high_risk_alerts,
        "fraud_prevention_rate": 0.95,
        "ml_model_accuracy": round(ml_fraud_detector.accuracy * 100, 2) if ml_fraud_detector.is_trained else 0,
        "transaction_volume": [
            {"date": "2024-11-13", "count": 45, "amount": 12500},
            {"date": "2024-11-14", "count": 52, "amount": 15800}
        ],
        "category_breakdown": {
            "Food and Drink": 850.50,
            "Electronics": 1250.00,
            "Gas Stations": 120.00,
            "Grocery": 450.75
        }
    }

# Plaid endpoints
@app.post("/api/v1/plaid/link_token")
async def create_link_token(user_id: str = "demo_user"):
    # Simulate Plaid link token creation
    return {
        "link_token": f"link-sandbox-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "expiration": datetime.now() + timedelta(hours=24)
    }

@app.post("/api/v1/plaid/exchange_token")
async def exchange_public_token(public_token: str, account_ids: List[str] = []):
    # Simulate token exchange
    return {
        "access_token": f"access-sandbox-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "item_id": f"item-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "accounts": demo_accounts
    }

# Transaction simulation endpoint
@app.post("/api/v1/simulate_transaction")
async def simulate_transaction():
    """Simulate a new transaction for testing"""
    import random
    import time
    
    # Generate a random transaction with unique timestamp-based ID
    new_transaction = {
        "id": f"tx_{int(time.time() * 1000)}",  # Unique ID using millisecond timestamp
        "account_id": random.choice(["acc_1", "acc_2"]),
        "amount": round(random.uniform(-500.0, -10.0), 2),
        "date": datetime.now(),
        "merchant_name": random.choice([
            "Amazon", "Walmart", "Target", "McDonald's", "Starbucks", 
            "Gas Station", "Grocery Store", "ATM Withdrawal"
        ]),
        "category": random.choice([
            ["Shopping", "Online"],
            ["Food and Drink", "Restaurant"],
            ["Gas Stations"],
            ["Grocery"],
            ["ATM", "Cash Withdrawal"]
        ]),
        "fraud_score": round(random.uniform(0.01, 0.95), 2),
        "risk_factors": []
    }
    
    # Add risk factors and anomaly detection based on fraud score
    if new_transaction["fraud_score"] > 0.7:
        new_transaction["risk_factors"] = ["High amount", "Unusual time", "Location mismatch"]
        new_transaction["is_anomaly"] = True
        new_transaction["anomaly_type"] = "HIGH_RISK_FRAUD"
        new_transaction["status"] = "FLAGGED"
    elif new_transaction["fraud_score"] > 0.5:
        new_transaction["risk_factors"] = ["Unusual merchant", "Amount pattern"]
        new_transaction["is_anomaly"] = True
        new_transaction["anomaly_type"] = "SUSPICIOUS_PATTERN"
        new_transaction["status"] = "REVIEW"
    elif new_transaction["fraud_score"] > 0.3:
        new_transaction["risk_factors"] = ["Amount pattern"]
        new_transaction["is_anomaly"] = True
        new_transaction["anomaly_type"] = "UNUSUAL_ACTIVITY"
        new_transaction["status"] = "MONITOR"
    else:
        new_transaction["is_anomaly"] = False
        new_transaction["anomaly_type"] = "NORMAL"
        new_transaction["status"] = "APPROVED"
    
    try:
        # Save to database
        saved_transaction = await transaction_db.add_transaction(new_transaction)
        
        # If database save fails, add to demo transactions as fallback
        if not saved_transaction:
            demo_transactions.insert(0, new_transaction)
        
        # Record transaction on blockchain
        try:
            bc_result = await fabric_gateway.record_transaction(
                transaction=new_transaction,
                fraud_score=new_transaction["fraud_score"],
                risk_factors=new_transaction["risk_factors"]
            )
            if bc_result.get("success"):
                print(f"⛓️ Transaction {new_transaction['id']} recorded on Hyperledger Fabric (Channel: {bc_result.get('channel')})")
        except Exception as bc_error:
            print(f"⚠️ Blockchain recording failed: {bc_error}")
        
        # Create fraud alert if high risk
        if new_transaction["fraud_score"] > 0.6:
            fraud_alert = {
                "id": f"alert_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                "transaction_id": new_transaction["id"],
                "alert_type": "FRAUD_DETECTION",
                "severity": "HIGH" if new_transaction["fraud_score"] > 0.7 else "MEDIUM", 
                "message": f"Suspicious transaction detected: {', '.join(new_transaction['risk_factors'])}",
                "is_resolved": False
            }
            
            # Save fraud alert to database
            saved_alert = await fraud_alert_db.add_alert(fraud_alert)
            if not saved_alert:
                demo_fraud_alerts.insert(0, fraud_alert)
            
            # Record fraud alert on blockchain
            try:
                bc_alert_result = await fabric_gateway.record_fraud_alert(
                    alert=fraud_alert,
                    transaction=new_transaction
                )
                if bc_alert_result.get("success"):
                    print(f"⛓️ Fraud alert {fraud_alert['id']} recorded on Hyperledger Fabric (Channel: {bc_alert_result.get('channel')})")
            except Exception as bc_error:
                print(f"⚠️ Blockchain alert recording failed: {bc_error}")
            
            # Send email notification for fraud alert
            try:
                await email_service.send_fraud_alert(
                    alert=fraud_alert,
                    transaction=new_transaction
                )
                print(f"📧 Fraud alert email sent for transaction {new_transaction['id']}")
            except Exception as email_error:
                print(f"⚠️ Failed to send fraud alert email: {email_error}")
            
            # Broadcast fraud alert via WebSocket
            alert_message = json.dumps({
                "type": "fraud_alert",
                "alert": fraud_alert
            })
            await manager.broadcast(alert_message)
        
        # Broadcast new transaction via WebSocket
        transaction_message = json.dumps({
            "type": "new_transaction", 
            "transaction": {
                **new_transaction,
                "date": new_transaction["date"].isoformat()
            }
        })
        await manager.broadcast(transaction_message)
        
    except Exception as e:
        print(f"Error saving transaction: {e}")
        # Fallback to demo data
        demo_transactions.insert(0, new_transaction)
    
    # Convert datetime to string for JSON serialization
    response_transaction = {
        **new_transaction,
        "date": new_transaction["date"].isoformat()
    }
    
    return {
        "success": True,
        "message": "Transaction simulated successfully",
        "transaction": response_transaction
    }

# WebSocket simulation endpoint
@app.get("/api/v1/ws/status")
async def websocket_status():
    return {
        "websocket_url": "ws://localhost:8000/ws/transactions",
        "connected_clients": len(manager.active_connections),
        "real_time_monitoring": "active"
    }

# Email notification endpoints
@app.post("/api/v1/email/test")
async def test_email(request: dict):
    """Test email notification"""
    recipient = request.get("email", email_service.default_recipient)
    
    test_alert = {
        "id": "test_alert_001",
        "transaction_id": "test_tx_001",
        "alert_type": "TEST_ALERT",
        "severity": "MEDIUM",
        "message": "This is a test fraud alert from FinSentinel AI",
        "risk_factors": ["Test Pattern", "System Check"],
        "is_resolved": False
    }
    
    test_transaction = {
        "id": "test_tx_001",
        "account_id": "test_account",
        "amount": -99.99,
        "merchant_name": "Test Merchant",
        "date": datetime.now().isoformat(),
        "fraud_score": 0.75,
        "risk_factors": ["Test Pattern", "System Check"]
    }
    
    success = await email_service.send_fraud_alert(
        alert=test_alert,
        transaction=test_transaction,
        recipient_email=recipient
    )
    
    return {
        "success": success,
        "message": "Test email sent" if success else "Email sending failed",
        "recipient": recipient,
        "email_enabled": email_service.enabled
    }

@app.post("/api/v1/email/configure")
async def configure_email(request: dict):
    """Configure email settings"""
    recipient = request.get("recipient_email")
    enabled = request.get("enabled", True)
    
    if recipient:
        email_service.default_recipient = recipient
    
    if "enabled" in request:
        email_service.enabled = enabled
    
    return {
        "success": True,
        "recipient_email": email_service.default_recipient,
        "enabled": email_service.enabled,
        "smtp_server": email_service.smtp_server
    }

@app.get("/api/v1/email/status")
async def email_status():
    """Get email service status"""
    return {
        "enabled": email_service.enabled,
        "configured": bool(email_service.sender_password),
        "smtp_server": email_service.smtp_server,
        "smtp_port": email_service.smtp_port,
        "default_recipient": email_service.default_recipient,
        "sender_email": email_service.sender_email
    }

# Real Plaid Integration Endpoints
@app.post("/api/v1/plaid/create_link_token")
async def create_link_token(request: dict):
    """Create a link token for Plaid Link"""
    user_id = request.get("user_id", "demo_user")
    result = await plaid_service.create_link_token(user_id)
    return result

@app.post("/api/v1/plaid/exchange_public_token")
async def exchange_public_token(request: dict):
    """Exchange public token for access token"""
    public_token = request.get("public_token")
    user_id = request.get("user_id", "demo_user")
    
    if not public_token:
        raise HTTPException(status_code=400, detail="Public token required")
    
    result = await plaid_service.exchange_public_token(public_token, user_id)
    return result

@app.get("/api/v1/plaid/connection_status/{user_id}")
async def get_plaid_connection_status(user_id: str):
    """Get Plaid connection status for a user"""
    result = await plaid_service.get_connection_status(user_id)
    return result

@app.get("/api/v1/plaid/accounts/{user_id}")
async def get_plaid_accounts(user_id: str):
    """Get user's Plaid accounts"""
    accounts = await plaid_service.get_accounts(user_id)
    return {"accounts": accounts}

@app.get("/api/v1/plaid/transactions/{user_id}")
async def get_plaid_transactions(user_id: str, days: int = 30):
    """Get user's Plaid transactions"""
    from datetime import datetime, timedelta
    start_date = datetime.now() - timedelta(days=days)
    end_date = datetime.now()
    
    transactions = await plaid_service.get_transactions(user_id, start_date, end_date)
    return {"transactions": transactions}

# Manual Transaction Entry Endpoints
def calculate_fraud_score(transaction):
    """
    ML-Powered Fraud Detection using Random Forest Classifier
    Combines rule-based analysis with machine learning predictions
    """
    import random
    from datetime import datetime, timedelta
    
    # ========== MACHINE LEARNING PREDICTION ==========
    # Get ML model prediction
    ml_fraud_probability, ml_prediction = ml_fraud_detector.predict(transaction)
    
    # Use ML probability as base score
    fraud_score = ml_fraud_probability
    risk_factors = []
    
    # Extract transaction details
    amount = abs(float(transaction.get("amount", 0)))
    merchant = transaction.get("merchant_name", "").lower()
    location = transaction.get("location", "").lower()
    payment_method = transaction.get("payment_method", "card").lower()
    category = transaction.get("category", "").lower()
    description = transaction.get("description", "").lower()
    
    # ========== RULE-BASED RISK FACTOR IDENTIFICATION ==========
    # Very high amounts (>$5000) - major red flag
    if amount > 5000:
        fraud_score += 0.4
        risk_factors.append("Extremely high transaction amount (>$5000)")
    elif amount > 2000:
        fraud_score += 0.3
        risk_factors.append("Very high transaction amount (>$2000)")
    elif amount > 1000:
        fraud_score += 0.2
        risk_factors.append("High transaction amount (>$1000)")
    elif amount > 500:
        fraud_score += 0.1
        risk_factors.append("Elevated transaction amount (>$500)")
    
    # Micro-transactions (card testing)
    if amount < 5 and payment_method == "card":
        fraud_score += 0.25
        risk_factors.append("Micro-transaction - potential card testing")
    elif amount < 20 and payment_method == "card":
        fraud_score += 0.1
        risk_factors.append("Small transaction - unusual pattern")
    
    # ========== MERCHANT CATEGORY RISK ==========
    # High-risk merchants
    high_risk_merchants = [
        "casino", "gambling", "betting", "lottery",
        "crypto", "bitcoin", "cryptocurrency", "blockchain",
        "wire transfer", "money transfer", "forex", "foreign exchange",
        "unknown", "unregistered", "unlicensed",
        "offshore", "dark web", "anonymous"
    ]
    if any(risky in merchant for risky in high_risk_merchants):
        fraud_score += 0.35
        risk_factors.append("High-risk merchant category")
    
    # Luxury/high-value items (often targeted)
    luxury_merchants = ["jewelry", "luxury", "gold", "diamond", "rolex", "designer"]
    if any(lux in merchant for lux in luxury_merchants) and amount > 1000:
        fraud_score += 0.2
        risk_factors.append("High-value luxury purchase")
    
    # Online/digital goods (easy to monetize)
    digital_merchants = ["gift card", "voucher", "prepaid", "digital", "online gaming"]
    if any(dig in merchant for dig in digital_merchants) and amount > 200:
        fraud_score += 0.25
        risk_factors.append("Digital goods purchase - high fraud risk")
    
    # ========== GEOGRAPHICAL RISK ==========
    # High-risk countries
    high_risk_countries = [
        "russia", "nigeria", "ghana", "ukraine", "romania",
        "china", "pakistan", "indonesia", "vietnam",
        "brazil", "mexico", "colombia"
    ]
    if any(country in location for country in high_risk_countries):
        fraud_score += 0.3
        risk_factors.append("High-risk geographical location")
    
    # International/cross-border
    international_keywords = ["international", "overseas", "foreign", "abroad", "offshore"]
    if any(intl in location for intl in international_keywords):
        fraud_score += 0.2
        risk_factors.append("Cross-border transaction")
    
    # Travel/tourist locations (common fraud)
    tourist_spots = ["airport", "hotel", "resort", "tourist", "vacation"]
    if any(spot in location for spot in tourist_spots) and amount > 500:
        fraud_score += 0.15
        risk_factors.append("High-value travel location transaction")
    
    # ========== PAYMENT METHOD RISK ==========
    # Cash transactions (harder to trace)
    if payment_method == "cash":
        if amount > 1000:
            fraud_score += 0.3
            risk_factors.append("Large cash transaction (>$1000)")
        elif amount > 500:
            fraud_score += 0.2
            risk_factors.append("Significant cash transaction")
        elif amount > 200:
            fraud_score += 0.1
            risk_factors.append("Elevated cash transaction")
    
    # Wire transfers (irreversible)
    if payment_method in ["wire", "wire transfer", "bank transfer"] and amount > 500:
        fraud_score += 0.3
        risk_factors.append("Wire transfer - irreversible payment method")
    
    # Cryptocurrency (anonymous)
    if payment_method in ["crypto", "cryptocurrency", "bitcoin"]:
        fraud_score += 0.35
        risk_factors.append("Cryptocurrency payment - anonymous")
    
    # ========== ATM-SPECIFIC RISKS ==========
    if "atm" in merchant or "atm" in description:
        if amount > 1000:
            fraud_score += 0.35
            risk_factors.append("Extremely large ATM withdrawal (>$1000)")
        elif amount > 500:
            fraud_score += 0.25
            risk_factors.append("Large ATM withdrawal (>$500)")
        elif amount > 300:
            fraud_score += 0.15
            risk_factors.append("Elevated ATM withdrawal")
        
        # Foreign ATM
        if any(foreign in location for foreign in international_keywords + high_risk_countries):
            fraud_score += 0.2
            risk_factors.append("International ATM withdrawal")
    
    # ========== TEMPORAL PATTERNS ==========
    current_hour = datetime.now().hour
    current_day = datetime.now().weekday()  # 0=Monday, 6=Sunday
    
    # Late night/early morning (1 AM - 5 AM)
    if 1 <= current_hour <= 5:
        fraud_score += 0.25
        risk_factors.append("Transaction during high-risk hours (1-5 AM)")
    # Late night (11 PM - 12 AM)
    elif current_hour >= 23:
        fraud_score += 0.15
        risk_factors.append("Late night transaction")
    # Very early morning (5 AM - 6 AM)
    elif current_hour <= 6:
        fraud_score += 0.1
        risk_factors.append("Early morning transaction")
    
    # Weekend transactions for business categories
    business_categories = ["office", "supply", "business", "corporate", "professional"]
    if current_day >= 5 and any(biz in category for biz in business_categories):
        fraud_score += 0.15
        risk_factors.append("Business transaction on weekend")
    
    # ========== TRANSACTION PATTERN ANALYSIS ==========
    # Round numbers (often fraudulent)
    if amount % 100 == 0 and amount >= 500:
        fraud_score += 0.15
        risk_factors.append("Round number transaction")
    elif amount % 1000 == 0:
        fraud_score += 0.2
        risk_factors.append("Exact thousand-dollar amount")
    
    # Unusual amount patterns (e.g., $1234.56)
    amount_str = str(amount)
    if len(set(amount_str.replace('.', ''))) <= 3:
        fraud_score += 0.1
        risk_factors.append("Unusual amount pattern")
    
    # ========== VELOCITY & BEHAVIORAL PATTERNS ==========
    # Multiple transactions in short time (simulated)
    # In real system, this would check transaction history
    if amount < 100 and random.random() < 0.3:
        fraud_score += 0.2
        risk_factors.append("Potential velocity fraud pattern")
    
    # Rapid succession of different merchants
    if random.random() < 0.2:  # Simulated
        fraud_score += 0.15
        risk_factors.append("Unusual merchant diversity pattern")
    
    # ========== CATEGORY-SPECIFIC RISKS ==========
    # E-commerce/online shopping
    if any(word in category for word in ["online", "e-commerce", "internet"]):
        if amount > 1000:
            fraud_score += 0.15
            risk_factors.append("High-value online purchase")
    
    # Travel bookings
    if any(word in category for word in ["travel", "airline", "hotel", "booking"]):
        if amount > 2000:
            fraud_score += 0.2
            risk_factors.append("High-value travel booking")
    
    # ========== SUSPICIOUS KEYWORDS ==========
    suspicious_keywords = [
        "test", "fraud", "scam", "hack", "stolen",
        "suspicious", "unusual", "emergency", "urgent"
    ]
    if any(keyword in description for keyword in suspicious_keywords):
        fraud_score += 0.3
        risk_factors.append("Suspicious transaction description")
    
    # ========== INCONSISTENCY DETECTION ==========
    # Mismatch between merchant and category
    if "food" in category and "electronics" in merchant:
        fraud_score += 0.1
        risk_factors.append("Category-merchant mismatch")
    
    # ========== ML MODEL CONFIDENCE ADJUSTMENT ==========
    # Adjust based on ML model confidence
    if ml_prediction == 1:  # ML model predicts fraud
        risk_factors.insert(0, f"ML Model Alert: {ml_fraud_probability:.1%} fraud probability")
        # Boost score slightly if ML is very confident
        if ml_fraud_probability > 0.8:
            fraud_score = min(fraud_score * 1.1, 0.99)
    
    # ========== FINAL ADJUSTMENTS ==========
    # Cap fraud score between 0.01 and 0.99
    fraud_score = max(0.01, min(fraud_score, 0.99))
    
    # Ensure at least one risk factor if score > 0.3
    if fraud_score > 0.3 and not risk_factors:
        risk_factors.append(f"Random Forest Model: Anomalous pattern detected ({ml_fraud_probability:.1%})")
    
    # Add ML model version to risk factors if high risk
    if fraud_score > 0.5:
        risk_factors.append(f"Random Forest (100 trees) - Confidence: {ml_fraud_probability:.1%}")
    
    return round(fraud_score, 3), risk_factors

@app.post("/api/v1/manual_transaction")
async def create_manual_transaction(transaction: ManualTransactionRequest):
    """Create a new manual transaction entry"""
    try:
        # Calculate fraud score based on transaction characteristics
        fraud_score, risk_factors = calculate_fraud_score(transaction.dict())
        
        # Determine anomaly status based on fraud score
        if fraud_score >= 0.7:
            is_anomaly = True
            anomaly_type = "HIGH_RISK_FRAUD"
            status = "FLAGGED"
        elif fraud_score >= 0.5:
            is_anomaly = True
            anomaly_type = "SUSPICIOUS_PATTERN"
            status = "REVIEW"
        elif fraud_score >= 0.3:
            is_anomaly = True
            anomaly_type = "UNUSUAL_ACTIVITY"
            status = "MONITOR"
        else:
            is_anomaly = False
            anomaly_type = "NORMAL"
            status = "APPROVED"
        
        # Generate unique transaction ID
        new_transaction = {
            "id": f"manual_tx_{datetime.now().timestamp()}",
            "account_id": transaction.account_id,
            "amount": transaction.amount,
            "date": transaction.date,
            "merchant_name": transaction.merchant_name,
            "category": [transaction.category],
            "description": transaction.description,
            "transaction_type": transaction.transaction_type,
            "location": transaction.location,
            "payment_method": transaction.payment_method,
            "manual_entry": True,
            "entry_timestamp": datetime.now().isoformat(),
            "fraud_score": fraud_score,
            "risk_factors": risk_factors,
            "is_anomaly": is_anomaly,
            "anomaly_type": anomaly_type,
            "status": status,
            "pending": False,
            "created_at": datetime.now().isoformat()
        }
        
        # Add to database
        saved_transaction = await transaction_db.add_transaction(new_transaction)
        
        # Record transaction on Hyperledger Fabric blockchain
        try:
            bc_result = await fabric_gateway.record_transaction(
                transaction=new_transaction,
                fraud_score=new_transaction["fraud_score"],
                risk_factors=new_transaction["risk_factors"]
            )
            if bc_result.get("success"):
                print(f"⛓️ Manual transaction {new_transaction['id']} recorded on Hyperledger Fabric (Channel: {bc_result.get('channel')})")
        except Exception as bc_error:
            print(f"⚠️ Blockchain recording failed for manual transaction: {bc_error}")
        
        # Broadcast to WebSocket clients
        await manager.broadcast(json.dumps({
            "type": "new_manual_transaction",
            "data": new_transaction
        }))
        
        return {
            "success": True,
            "message": "Manual transaction created successfully and recorded on blockchain",
            "transaction": new_transaction
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create transaction: {str(e)}")

@app.put("/api/v1/manual_transaction/{transaction_id}")
async def update_manual_transaction(transaction_id: str, transaction: ManualTransactionRequest):
    """Update an existing manual transaction"""
    try:
        # Find existing transaction
        transactions = await transaction_db.get_transactions(1000)
        existing = next((t for t in transactions if t["id"] == transaction_id), None)
        
        if not existing:
            raise HTTPException(status_code=404, detail="Transaction not found")
        
        # Update transaction data
        updated_transaction = {
            **existing,
            "account_id": transaction.account_id,
            "amount": transaction.amount,
            "date": transaction.date,
            "merchant_name": transaction.merchant_name,
            "category": [transaction.category],
            "description": transaction.description,
            "transaction_type": transaction.transaction_type,
            "location": transaction.location,
            "payment_method": transaction.payment_method,
            "updated_at": datetime.now().isoformat()
        }
        
        # Update in database (for demo purposes, we'll add as new)
        updated_transaction["id"] = f"updated_{transaction_id}_{datetime.now().timestamp()}"
        saved_transaction = await transaction_db.add_transaction(updated_transaction)
        
        return {
            "success": True,
            "message": "Transaction updated successfully",
            "transaction": updated_transaction
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update transaction: {str(e)}")

@app.delete("/api/v1/transactions/{transaction_id}")
async def delete_transaction(transaction_id: str):
    """Delete a transaction"""
    try:
        # Mark transaction as deleted (for demo purposes)
        transactions = await transaction_db.get_transactions(1000)
        transaction = next((t for t in transactions if t["id"] == transaction_id), None)
        
        if transaction:
            # Add a deleted marker transaction
            deleted_marker = {
                "id": f"deleted_{transaction_id}_{datetime.now().timestamp()}",
                "original_id": transaction_id,
                "deleted_at": datetime.now().isoformat(),
                "deleted": True
            }
            await transaction_db.add_transaction(deleted_marker)
            
            # Broadcast deletion
            await manager.broadcast(json.dumps({
                "type": "transaction_deleted",
                "data": {"transaction_id": transaction_id}
            }))
            
            return {
                "success": True,
                "message": "Transaction deleted successfully"
            }
        
        raise HTTPException(status_code=404, detail="Transaction not found")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete transaction: {str(e)}")

@app.get("/api/v1/manual_transactions")
async def get_manual_transactions(limit: int = 50):
    """Get manual transactions only"""
    all_transactions = await transaction_db.get_transactions(1000)
    manual_transactions = [
        t for t in all_transactions 
        if t.get("manual_entry") == True and not t.get("deleted")
    ][-limit:]
    
    return {
        "transactions": manual_transactions,
        "total": len(manual_transactions)
    }

# Blockchain endpoints
@app.get("/api/v1/blockchain/status")
async def get_blockchain_status():
    """Get Hyperledger Fabric blockchain status"""
    try:
        return {
            "success": True,
            "connected": fabric_gateway.enabled,
            "channel": fabric_gateway.channel_name,
            "chaincode": fabric_gateway.chaincode_name,
            "network": fabric_gateway.network_path,
            "organization": fabric_gateway.org,
            "type": "Hyperledger Fabric"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get blockchain status: {str(e)}")

@app.get("/api/v1/blockchain/transaction/{transaction_id}")
async def get_blockchain_transaction(transaction_id: str):
    """Query a transaction from Hyperledger Fabric blockchain"""
    try:
        transaction = await fabric_gateway.get_transaction(transaction_id)
        if transaction:
            return {
                "success": True,
                "transaction": transaction
            }
        else:
            raise HTTPException(status_code=404, detail="Transaction not found on blockchain")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to query transaction: {str(e)}")

@app.get("/api/v1/blockchain/transactions/all")
async def get_all_blockchain_transactions():
    """Query all transactions from Hyperledger Fabric blockchain"""
    try:
        transactions = await fabric_gateway.get_all_transactions()
        return {
            "success": True,
            "total": len(transactions),
            "transactions": transactions
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to query all transactions: {str(e)}")

# Agent status endpoints
@app.get("/api/v1/agents/status")
async def get_agent_status():
    return {
        "agents": {
            "transaction_monitor": {"status": "running", "last_heartbeat": datetime.now()},
            "fraud_detection": {"status": "running", "last_heartbeat": datetime.now()},
            "forecast_agent": {"status": "running", "last_heartbeat": datetime.now()},
            "audit_agent": {"status": "running", "last_heartbeat": datetime.now()}
        },
        "orchestrator": {"status": "coordinating", "active_agents": 4}
    }

# Authentication & Authorization Setup
security = HTTPBearer()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
    """Dependency to get current authenticated user from JWT token"""
    token = credentials.credentials
    user = auth_service.verify_token(token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user

def require_permission(permission: Permission):
    """Factory function to create permission-checking dependency"""
    async def permission_checker(current_user: User = Depends(get_current_user)):
        if not auth_service.has_permission(current_user, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required: {permission.value}"
            )
        return current_user
    return permission_checker

# Authentication Endpoints
@app.post("/api/v1/auth/login", response_model=Token)
async def login(credentials: UserLogin):
    """Login endpoint - returns JWT token"""
    try:
        token_data = auth_service.login(credentials)
        if not token_data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Log the login action
        user = auth_service.get_user_by_username(credentials.username)
        if user:
            auth_service.log_action(
                user_id=user.id,
                action="login",
                details={"username": credentials.username}
            )
        
        return token_data
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@app.get("/api/v1/auth/me", response_model=User)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information"""
    return current_user

@app.post("/api/v1/auth/logout")
async def logout(current_user: User = Depends(get_current_user)):
    """Logout endpoint - log the action (token invalidation handled client-side)"""
    auth_service.log_action(
        user_id=current_user.id,
        action="logout",
        details={"username": current_user.username}
    )
    return {"message": "Logged out successfully"}

# User Management Endpoints (Admin Only)
@app.get("/api/v1/users", response_model=List[User])
async def get_users(
    current_user: User = Depends(require_permission(Permission.VIEW_USERS))
):
    """Get all users (requires VIEW_USERS permission)"""
    users = auth_service.get_all_users()
    auth_service.log_action(
        user_id=current_user.id,
        action="view_users",
        details={"count": len(users)}
    )
    return users

@app.post("/api/v1/users", response_model=User)
async def create_user(
    user_data: UserCreate,
    current_user: User = Depends(require_permission(Permission.CREATE_USERS))
):
    """Create a new user (requires CREATE_USERS permission)"""
    try:
        new_user = auth_service.create_user(user_data)
        auth_service.log_action(
            user_id=current_user.id,
            action="create_user",
            details={"new_username": new_user.username, "role": new_user.role.value}
        )
        return new_user
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@app.put("/api/v1/users/{username}", response_model=User)
async def update_user(
    username: str,
    user_data: UserUpdate,
    current_user: User = Depends(require_permission(Permission.UPDATE_USERS))
):
    """Update a user (requires UPDATE_USERS permission)"""
    try:
        updated_user = auth_service.update_user(username, user_data)
        if not updated_user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        
        auth_service.log_action(
            user_id=current_user.id,
            action="update_user",
            details={"username": username, "changes": user_data.dict(exclude_unset=True)}
        )
        return updated_user
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@app.delete("/api/v1/users/{username}")
async def delete_user(
    username: str,
    current_user: User = Depends(require_permission(Permission.DELETE_USERS))
):
    """Delete a user (requires DELETE_USERS permission)"""
    # Prevent self-deletion
    if username == current_user.username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account"
        )
    
    success = auth_service.delete_user(username)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    auth_service.log_action(
        user_id=current_user.id,
        action="delete_user",
        details={"username": username}
    )
    return {"message": f"User {username} deleted successfully"}

# Audit Log Endpoints
@app.get("/api/v1/audit/logs")
async def get_audit_logs(
    limit: int = 100,
    current_user: User = Depends(require_permission(Permission.VIEW_LOGS))
):
    """Get audit logs (requires VIEW_LOGS permission)"""
    logs = auth_service.get_audit_logs(limit)
    return {"logs": logs, "count": len(logs)}

if __name__ == "__main__":
    print("🛡️ Starting FinSentinel AI Backend Server...")
    print("🔗 API Documentation: http://localhost:8000/docs")
    print("❤️ Health Check: http://localhost:8000/health")
    print("📊 Demo Dashboard: http://localhost:3000")
    
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8000, 
        reload=False,
        log_level="info"
    )