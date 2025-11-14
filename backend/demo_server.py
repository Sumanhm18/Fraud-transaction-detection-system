"""
Simplified FastAPI server for testing FinSentinel AI
"""

import os
import json
import asyncio
from typing import List, Dict, Any, Set
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
from pydantic import BaseModel

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
        "risk_factors": []
    },
    {
        "id": "tx_2",
        "account_id": "acc_1", 
        "amount": -1250.00,
        "date": datetime.now() - timedelta(hours=5),
        "merchant_name": "Best Buy",
        "category": ["Electronics"],
        "fraud_score": 0.75,
        "risk_factors": ["High amount", "Unusual merchant"]
    },
    {
        "id": "tx_3",
        "account_id": "acc_2",
        "amount": 2500.00,
        "date": datetime.now() - timedelta(days=1),
        "merchant_name": "Payroll Deposit",
        "category": ["Deposit", "Payroll"],
        "fraud_score": 0.01,
        "risk_factors": []
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
@app.get("/api/v1/accounts", response_model=List[Account])
async def get_accounts():
    try:
        accounts = await account_db.get_accounts()
        return accounts if accounts else demo_accounts
    except Exception as e:
        print(f"Database error, using demo data: {e}")
        return demo_accounts

@app.get("/api/v1/accounts/{account_id}", response_model=Account)
async def get_account(account_id: str):
    try:
        accounts = await account_db.get_accounts()
        account = next((acc for acc in accounts if acc["id"] == account_id), None)
        if not account:
            # Fallback to demo data
            account = next((acc for acc in demo_accounts if acc["id"] == account_id), None)
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")
        return account
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
    
    # Generate a random transaction
    new_transaction = {
        "id": f"tx_{len(demo_transactions) + 1}",
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
    
    # Add risk factors based on fraud score
    if new_transaction["fraud_score"] > 0.7:
        new_transaction["risk_factors"] = ["High amount", "Unusual time", "Location mismatch"]
    elif new_transaction["fraud_score"] > 0.4:
        new_transaction["risk_factors"] = ["Unusual merchant", "Amount pattern"]
    
    try:
        # Save to database
        saved_transaction = await transaction_db.add_transaction(new_transaction)
        
        # If database save fails, add to demo transactions as fallback
        if not saved_transaction:
            demo_transactions.insert(0, new_transaction)
        
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
    
    return {
        "success": True,
        "message": "Transaction simulated successfully",
        "transaction": new_transaction
    }

# WebSocket simulation endpoint
@app.get("/api/v1/ws/status")
async def websocket_status():
    return {
        "websocket_url": "ws://localhost:8000/ws/transactions",
        "connected_clients": len(manager.active_connections),
        "real_time_monitoring": "active"
    }

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