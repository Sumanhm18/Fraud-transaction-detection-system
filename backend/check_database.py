#!/usr/bin/env python3
"""
Database verification script
"""

import asyncio
import sys
sys.path.append('/Users/sumanhm/Downloads/finance/backend')

from sqlite_database import transaction_db, fraud_alert_db, account_db

async def check_database():
    """Check database contents"""
    try:
        # Get transactions
        transactions = await transaction_db.get_transactions(100)
        alerts = await fraud_alert_db.get_alerts(100)
        accounts = await account_db.get_accounts()
        
        print("📊 Database Status Report")
        print("=" * 40)
        print(f"💳 Transactions: {len(transactions)}")
        print(f"🚨 Fraud Alerts: {len(alerts)}")
        print(f"🏦 Accounts: {len(accounts)}")
        print("=" * 40)
        
        if transactions:
            print("\n🔍 Sample Transactions:")
            for i, tx in enumerate(transactions[:3]):
                print(f"  {i+1}. {tx['id']} - {tx['merchant']} - ${tx['amount']}")
        
        if alerts:
            print(f"\n🚨 Sample Fraud Alerts:")
            for i, alert in enumerate(alerts[:3]):
                print(f"  {i+1}. {alert['id']} - {alert['severity']} - {alert['message'][:50]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ Database check error: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(check_database())
    if not success:
        sys.exit(1)