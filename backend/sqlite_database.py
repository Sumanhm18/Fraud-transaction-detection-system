"""
Simplified database configuration for FinSentinel AI
Using SQLite for local development (no external dependencies)
"""

import sqlite3
import asyncio
import aiosqlite
import json
import os
from datetime import datetime
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

# SQLite database path
DB_PATH = os.path.join(os.path.dirname(__file__), "finsentinel.db")

class TransactionDB:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
    
    async def init_database(self):
        """Initialize SQLite database and create tables"""
        async with aiosqlite.connect(self.db_path) as db:
            # Create transactions table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS transactions (
                    id TEXT PRIMARY KEY,
                    account_id TEXT NOT NULL,
                    amount REAL NOT NULL,
                    description TEXT,
                    date TEXT NOT NULL,
                    category TEXT,
                    merchant TEXT,
                    location TEXT,
                    payment_method TEXT,
                    is_flagged INTEGER DEFAULT 0,
                    risk_score REAL DEFAULT 0.0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create fraud_alerts table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS fraud_alerts (
                    id TEXT PRIMARY KEY,
                    transaction_id TEXT,
                    alert_type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    message TEXT NOT NULL,
                    is_resolved INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (transaction_id) REFERENCES transactions (id)
                )
            """)
            
            # Create accounts table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS accounts (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    account_type TEXT NOT NULL,
                    balance REAL DEFAULT 0.0,
                    institution_name TEXT,
                    account_name TEXT,
                    is_active INTEGER DEFAULT 1,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            await db.commit()
            logger.info("SQLite database initialized successfully")
    
    async def add_transaction(self, transaction_data: Dict[str, Any]) -> bool:
        """Add a new transaction to the database"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT OR IGNORE INTO transactions (
                        id, account_id, amount, description, date, category,
                        merchant, location, payment_method, is_flagged, risk_score
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    transaction_data.get('id'),
                    transaction_data.get('account_id'),
                    transaction_data.get('amount'),
                    transaction_data.get('description'),
                    transaction_data.get('date'),
                    json.dumps(transaction_data.get('category', [])) if isinstance(transaction_data.get('category'), list) else transaction_data.get('category'),
                    transaction_data.get('merchant'),
                    transaction_data.get('location'),
                    transaction_data.get('payment_method'),
                    1 if transaction_data.get('is_flagged') else 0,
                    transaction_data.get('risk_score', 0.0)
                ))
                await db.commit()
                return True
        except Exception as e:
            logger.error(f"Failed to add transaction: {e}")
            return False
    
    async def get_transactions(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get transactions from database"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute("""
                    SELECT * FROM transactions 
                    ORDER BY created_at DESC 
                    LIMIT ?
                """, (limit,)) as cursor:
                    rows = await cursor.fetchall()
                    transactions = []
                    for row in rows:
                        transaction = dict(row)
                        # Deserialize category JSON back to list
                        try:
                            if transaction.get('category'):
                                transaction['category'] = json.loads(transaction['category'])
                        except (json.JSONDecodeError, TypeError):
                            transaction['category'] = [transaction['category']] if transaction.get('category') else []
                        transactions.append(transaction)
                    return transactions
        except Exception as e:
            logger.error(f"Failed to get transactions: {e}")
            return []
    
    async def update_transaction_status(self, transaction_id: str, is_flagged: bool, risk_score: float = None) -> bool:
        """Update transaction flag status"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                if risk_score is not None:
                    await db.execute("""
                        UPDATE transactions 
                        SET is_flagged = ?, risk_score = ? 
                        WHERE id = ?
                    """, (1 if is_flagged else 0, risk_score, transaction_id))
                else:
                    await db.execute("""
                        UPDATE transactions 
                        SET is_flagged = ? 
                        WHERE id = ?
                    """, (1 if is_flagged else 0, transaction_id))
                await db.commit()
                return True
        except Exception as e:
            logger.error(f"Failed to update transaction: {e}")
            return False

class FraudAlertDB:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
    
    async def add_alert(self, alert_data: Dict[str, Any]) -> bool:
        """Add a new fraud alert"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT OR IGNORE INTO fraud_alerts (
                        id, transaction_id, alert_type, severity, message, is_resolved
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    alert_data.get('id'),
                    alert_data.get('transaction_id'),
                    alert_data.get('alert_type'),
                    alert_data.get('severity'),
                    alert_data.get('message'),
                    1 if alert_data.get('is_resolved') else 0
                ))
                await db.commit()
                return True
        except Exception as e:
            logger.error(f"Failed to add fraud alert: {e}")
            return False
    
    async def get_alerts(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get fraud alerts from database"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute("""
                    SELECT * FROM fraud_alerts 
                    ORDER BY created_at DESC 
                    LIMIT ?
                """, (limit,)) as cursor:
                    rows = await cursor.fetchall()
                    return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Failed to get fraud alerts: {e}")
            return []
    
    async def resolve_alert(self, alert_id: str) -> bool:
        """Mark fraud alert as resolved"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    UPDATE fraud_alerts 
                    SET is_resolved = 1 
                    WHERE id = ?
                """, (alert_id,))
                await db.commit()
                return True
        except Exception as e:
            logger.error(f"Failed to resolve alert: {e}")
            return False

class AccountDB:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
    
    async def add_account(self, account_data: Dict[str, Any]) -> bool:
        """Add a new account"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT OR IGNORE INTO accounts (
                        id, user_id, account_type, balance, institution_name, account_name
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    account_data.get('id'),
                    account_data.get('user_id'),
                    account_data.get('account_type'),
                    account_data.get('balance', 0.0),
                    account_data.get('institution_name'),
                    account_data.get('account_name')
                ))
                await db.commit()
                return True
        except Exception as e:
            logger.error(f"Failed to add account: {e}")
            return False
    
    async def get_accounts(self, user_id: str = None) -> List[Dict[str, Any]]:
        """Get accounts from database"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                if user_id:
                    async with db.execute("""
                        SELECT * FROM accounts 
                        WHERE user_id = ? AND is_active = 1
                        ORDER BY created_at DESC
                    """, (user_id,)) as cursor:
                        rows = await cursor.fetchall()
                else:
                    async with db.execute("""
                        SELECT * FROM accounts 
                        WHERE is_active = 1
                        ORDER BY created_at DESC
                    """) as cursor:
                        rows = await cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Failed to get accounts: {e}")
            return []
    
    async def update_balance(self, account_id: str, new_balance: float) -> bool:
        """Update account balance"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    UPDATE accounts 
                    SET balance = ? 
                    WHERE id = ?
                """, (new_balance, account_id))
                await db.commit()
                return True
        except Exception as e:
            logger.error(f"Failed to update account balance: {e}")
            return False

# Initialize database instances
transaction_db = TransactionDB()
fraud_alert_db = FraudAlertDB()
account_db = AccountDB()

async def init_database():
    """Initialize the database and create tables"""
    await transaction_db.init_database()

async def seed_demo_data():
    """Add some demo data to the database"""
    try:
        # Add demo accounts
        demo_accounts = [
            {
                "id": "acc_demo_1",
                "user_id": "user_demo",
                "account_type": "checking",
                "balance": 5000.00,
                "institution_name": "Demo Bank",
                "account_name": "Primary Checking"
            },
            {
                "id": "acc_demo_2", 
                "user_id": "user_demo",
                "account_type": "savings",
                "balance": 15000.00,
                "institution_name": "Demo Bank",
                "account_name": "Savings Account"
            }
        ]
        
        for account in demo_accounts:
            await account_db.add_account(account)
        
        # Add demo transactions
        demo_transactions = [
            {
                "id": "txn_demo_1",
                "account_id": "acc_demo_1",
                "amount": -45.50,
                "description": "Grocery Store Purchase",
                "date": datetime.now().isoformat(),
                "category": ["groceries", "food"],
                "merchant": "Fresh Market",
                "location": "San Francisco, CA",
                "payment_method": "debit_card",
                "is_flagged": False,
                "risk_score": 0.1
            },
            {
                "id": "txn_demo_2",
                "account_id": "acc_demo_1", 
                "amount": -1200.00,
                "description": "Unusual Large Purchase",
                "date": datetime.now().isoformat(),
                "category": ["electronics", "shopping"],
                "merchant": "Electronics Store",
                "location": "Unknown Location",
                "payment_method": "credit_card",
                "is_flagged": True,
                "risk_score": 0.85
            }
        ]
        
        for transaction in demo_transactions:
            await transaction_db.add_transaction(transaction)
        
        logger.info("Demo data seeded successfully")
        
    except Exception as e:
        logger.error(f"Failed to seed demo data: {e}")