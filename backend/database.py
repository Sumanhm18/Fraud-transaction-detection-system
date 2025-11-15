"""
Database configuration and models for FinSentinel AI
PostgreSQL integration for transaction storage
"""

import os
import asyncio
from datetime import datetime
from typing import List, Optional
import asyncpg
from pydantic import BaseModel
import json

# Database configuration
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql://finsentinel:finsentinel123@localhost:5432/finsentinel_db"
)

# Connection pool
_pool = None

async def init_database():
    """Initialize database connection pool and create tables"""
    global _pool
    
    try:
        # Create connection pool
        _pool = await asyncpg.create_pool(
            DATABASE_URL,
            min_size=1,
            max_size=10,
            command_timeout=60
        )
        
        # Create tables if they don't exist
        await create_tables()
        print("✅ Database initialized successfully")
        
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        # Fallback to demo data if database is not available
        print("📝 Using demo data (database not available)")

async def get_pool():
    """Get database connection pool"""
    global _pool
    if not _pool:
        await init_database()
    return _pool

async def create_tables():
    """Create database tables"""
    pool = await get_pool()
    
    async with pool.acquire() as conn:
        # Create transactions table
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id SERIAL PRIMARY KEY,
                transaction_id VARCHAR(50) UNIQUE NOT NULL,
                account_id VARCHAR(50) NOT NULL,
                amount DECIMAL(12,2) NOT NULL,
                merchant_name VARCHAR(255),
                category JSONB DEFAULT '[]',
                fraud_score DECIMAL(3,2) DEFAULT 0.0,
                risk_factors JSONB DEFAULT '[]',
                status VARCHAR(20) DEFAULT 'PENDING',
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create fraud_alerts table
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS fraud_alerts (
                id SERIAL PRIMARY KEY,
                alert_id VARCHAR(50) UNIQUE NOT NULL,
                transaction_id VARCHAR(50) NOT NULL,
                risk_level VARCHAR(20) NOT NULL,
                fraud_score DECIMAL(3,2) NOT NULL,
                risk_factors JSONB DEFAULT '[]',
                status VARCHAR(20) DEFAULT 'PENDING',
                assigned_to VARCHAR(100),
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (transaction_id) REFERENCES transactions(transaction_id)
            )
        ''')
        
        # Create accounts table
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS accounts (
                id SERIAL PRIMARY KEY,
                account_id VARCHAR(50) UNIQUE NOT NULL,
                name VARCHAR(255) NOT NULL,
                type VARCHAR(50) NOT NULL,
                subtype VARCHAR(50),
                balance DECIMAL(12,2) DEFAULT 0.0,
                currency_code VARCHAR(3) DEFAULT 'USD',
                mask VARCHAR(10),
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Create indexes for better performance
        await conn.execute('''
            CREATE INDEX IF NOT EXISTS idx_transactions_account_id ON transactions(account_id);
        ''')
        await conn.execute('''
            CREATE INDEX IF NOT EXISTS idx_transactions_created_at ON transactions(created_at);
        ''')
        await conn.execute('''
            CREATE INDEX IF NOT EXISTS idx_fraud_alerts_status ON fraud_alerts(status);
        ''')

# Database operations for transactions
class TransactionDB:
    
    @staticmethod
    async def create_transaction(transaction_data: dict) -> dict:
        """Create a new transaction"""
        pool = await get_pool()
        if not pool:
            return None
            
        async with pool.acquire() as conn:
            try:
                result = await conn.fetchrow('''
                    INSERT INTO transactions (
                        transaction_id, account_id, amount, merchant_name,
                        category, fraud_score, risk_factors, status
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                    RETURNING *
                ''', 
                    transaction_data['id'],
                    transaction_data['account_id'],
                    float(transaction_data['amount']),
                    transaction_data.get('merchant_name'),
                    json.dumps(transaction_data.get('category', [])),
                    float(transaction_data.get('fraud_score', 0.0)),
                    json.dumps(transaction_data.get('risk_factors', [])),
                    'PENDING'
                )
                
                return dict(result) if result else None
                
            except Exception as e:
                print(f"Error creating transaction: {e}")
                return None

    @staticmethod
    async def get_all_transactions(limit: int = 100) -> List[dict]:
        """Get all transactions"""
        pool = await get_pool()
        if not pool:
            return []
            
        async with pool.acquire() as conn:
            try:
                rows = await conn.fetch('''
                    SELECT 
                        transaction_id as id,
                        account_id,
                        amount,
                        merchant_name,
                        category,
                        fraud_score,
                        risk_factors,
                        status,
                        created_at as date
                    FROM transactions 
                    ORDER BY created_at DESC 
                    LIMIT $1
                ''', limit)
                
                transactions = []
                for row in rows:
                    tx = dict(row)
                    # Parse JSON fields
                    tx['category'] = json.loads(tx['category']) if tx['category'] else []
                    tx['risk_factors'] = json.loads(tx['risk_factors']) if tx['risk_factors'] else []
                    transactions.append(tx)
                
                return transactions
                
            except Exception as e:
                print(f"Error fetching transactions: {e}")
                return []

    @staticmethod
    async def get_transaction_by_id(transaction_id: str) -> Optional[dict]:
        """Get transaction by ID"""
        pool = await get_pool()
        if not pool:
            return None
            
        async with pool.acquire() as conn:
            try:
                row = await conn.fetchrow('''
                    SELECT 
                        transaction_id as id,
                        account_id,
                        amount,
                        merchant_name,
                        category,
                        fraud_score,
                        risk_factors,
                        status,
                        created_at as date
                    FROM transactions 
                    WHERE transaction_id = $1
                ''', transaction_id)
                
                if row:
                    tx = dict(row)
                    tx['category'] = json.loads(tx['category']) if tx['category'] else []
                    tx['risk_factors'] = json.loads(tx['risk_factors']) if tx['risk_factors'] else []
                    return tx
                
                return None
                
            except Exception as e:
                print(f"Error fetching transaction: {e}")
                return None

# Database operations for fraud alerts
class FraudAlertDB:
    
    @staticmethod
    async def create_alert(alert_data: dict) -> dict:
        """Create a new fraud alert"""
        pool = await get_pool()
        if not pool:
            return None
            
        async with pool.acquire() as conn:
            try:
                result = await conn.fetchrow('''
                    INSERT INTO fraud_alerts (
                        alert_id, transaction_id, risk_level, fraud_score,
                        risk_factors, status
                    ) VALUES ($1, $2, $3, $4, $5, $6)
                    RETURNING *
                ''', 
                    alert_data['id'],
                    alert_data['transaction_id'],
                    alert_data['risk_level'],
                    float(alert_data['fraud_score']),
                    json.dumps(alert_data.get('risk_factors', [])),
                    alert_data.get('status', 'PENDING')
                )
                
                return dict(result) if result else None
                
            except Exception as e:
                print(f"Error creating fraud alert: {e}")
                return None

    @staticmethod
    async def get_all_alerts() -> List[dict]:
        """Get all fraud alerts"""
        pool = await get_pool()
        if not pool:
            return []
            
        async with pool.acquire() as conn:
            try:
                rows = await conn.fetch('''
                    SELECT 
                        alert_id as id,
                        transaction_id,
                        risk_level,
                        fraud_score,
                        risk_factors,
                        status,
                        assigned_to,
                        created_at
                    FROM fraud_alerts 
                    ORDER BY created_at DESC
                ''')
                
                alerts = []
                for row in rows:
                    alert = dict(row)
                    alert['risk_factors'] = json.loads(alert['risk_factors']) if alert['risk_factors'] else []
                    alerts.append(alert)
                
                return alerts
                
            except Exception as e:
                print(f"Error fetching fraud alerts: {e}")
                return []

# Database operations for accounts
class AccountDB:
    
    @staticmethod
    async def get_all_accounts() -> List[dict]:
        """Get all accounts"""
        pool = await get_pool()
        if not pool:
            return []
            
        async with pool.acquire() as conn:
            try:
                rows = await conn.fetch('''
                    SELECT 
                        account_id as id,
                        name,
                        type,
                        subtype,
                        balance,
                        currency_code,
                        mask
                    FROM accounts 
                    ORDER BY created_at DESC
                ''')
                
                return [dict(row) for row in rows]
                
            except Exception as e:
                print(f"Error fetching accounts: {e}")
                return []

    @staticmethod
    async def create_account(account_data: dict) -> dict:
        """Create a new account"""
        pool = await get_pool()
        if not pool:
            return None
            
        async with pool.acquire() as conn:
            try:
                result = await conn.fetchrow('''
                    INSERT INTO accounts (
                        account_id, name, type, subtype, balance, currency_code, mask
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                    ON CONFLICT (account_id) DO UPDATE SET
                        name = EXCLUDED.name,
                        balance = EXCLUDED.balance,
                        updated_at = CURRENT_TIMESTAMP
                    RETURNING *
                ''', 
                    account_data['id'],
                    account_data['name'],
                    account_data['type'],
                    account_data.get('subtype'),
                    float(account_data.get('balance', 0.0)),
                    account_data.get('currency_code', 'USD'),
                    account_data.get('mask')
                )
                
                return dict(result) if result else None
                
            except Exception as e:
                print(f"Error creating account: {e}")
                return None

async def seed_demo_data():
    """Seed database with demo data if empty"""
    try:
        # Check if we have any transactions
        transactions = await TransactionDB.get_all_transactions(1)
        if transactions:
            return  # Already have data
        
        # Create demo accounts
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
        
        for account in demo_accounts:
            await AccountDB.create_account(account)
        
        # Create demo transactions
        demo_transactions = [
            {
                "id": "tx_1",
                "account_id": "acc_1",
                "amount": -85.50,
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
                "merchant_name": "Payroll Deposit",
                "category": ["Deposit", "Payroll"],
                "fraud_score": 0.01,
                "risk_factors": [],
                "is_anomaly": False,
                "anomaly_type": "NORMAL",
                "status": "APPROVED"
            }
        ]
        
        for tx in demo_transactions:
            await TransactionDB.create_transaction(tx)
        
        # Create demo fraud alert
        await FraudAlertDB.create_alert({
            "id": "alert_1",
            "transaction_id": "tx_2",
            "risk_level": "HIGH",
            "fraud_score": 0.75,
            "risk_factors": ["High amount", "Unusual merchant"],
            "status": "PENDING"
        })
        
        print("✅ Demo data seeded successfully")
        
    except Exception as e:
        print(f"❌ Error seeding demo data: {e}")