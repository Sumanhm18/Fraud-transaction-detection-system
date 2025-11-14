#!/usr/bin/env python3
"""
Bulk save script to transfer all transactions from API to database
"""

import asyncio
import json
import sys
import requests
from datetime import datetime

# Add the backend directory to path
sys.path.append('/Users/sumanhm/Downloads/finance/backend')

from sqlite_database import transaction_db, fraud_alert_db, init_database

async def bulk_save_transactions():
    """Fetch transactions from API and save to database"""
    try:
        # Initialize database
        await init_database()
        print("✅ Database initialized")
        
        # Fetch all transactions from the API
        response = requests.get("http://localhost:8000/api/v1/transactions?limit=1000")
        if response.status_code != 200:
            print(f"❌ Failed to fetch transactions: {response.status_code}")
            return
        
        transactions = response.json()
        print(f"📥 Fetched {len(transactions)} transactions from API")
        
        saved_count = 0
        failed_count = 0
        
        for transaction in transactions:
            try:
                # Convert API format to database format
                db_transaction = {
                    "id": transaction["id"],
                    "account_id": transaction.get("account_id", "unknown"),
                    "amount": float(transaction["amount"]),
                    "description": f"{transaction.get('merchant_name', 'Unknown Merchant')} - Transaction",
                    "date": transaction.get("date", datetime.now().isoformat()),
                    "category": transaction.get("category", ["general"]),
                    "merchant": transaction.get("merchant_name", "Unknown"),
                    "location": "Unknown",
                    "payment_method": "unknown",
                    "is_flagged": transaction.get("fraud_score", 0) > 0.6,
                    "risk_score": transaction.get("fraud_score", 0.0)
                }
                
                # Save to database
                success = await transaction_db.add_transaction(db_transaction)
                if success:
                    saved_count += 1
                    print(f"✅ Saved: {transaction['id']} - {transaction.get('merchant_name', 'Unknown')}")
                else:
                    failed_count += 1
                    print(f"❌ Failed to save: {transaction['id']}")
                    
            except Exception as e:
                print(f"❌ Error processing transaction {transaction.get('id', 'unknown')}: {e}")
                failed_count += 1
        
        # Fetch and save fraud alerts if available
        try:
            alerts_response = requests.get("http://localhost:8000/api/v1/fraud/alerts")
            if alerts_response.status_code == 200:
                alerts_data = alerts_response.json()
                alerts = alerts_data.get("alerts", [])
                print(f"📥 Fetched {len(alerts)} fraud alerts from API")
                
                alerts_saved = 0
                for alert in alerts:
                    try:
                        db_alert = {
                            "id": alert["id"],
                            "transaction_id": alert["transaction_id"],
                            "alert_type": "FRAUD_DETECTION",
                            "severity": alert.get("risk_level", "MEDIUM"),
                            "message": f"Fraud alert - Score: {alert.get('fraud_score', 0):.2%}",
                            "is_resolved": alert.get("status") == "RESOLVED"
                        }
                        
                        success = await fraud_alert_db.add_alert(db_alert)
                        if success:
                            alerts_saved += 1
                            print(f"✅ Saved alert: {alert['id']}")
                            
                    except Exception as e:
                        print(f"❌ Error processing alert {alert.get('id', 'unknown')}: {e}")
                
                print(f"📊 Fraud alerts saved: {alerts_saved}")
        
        except Exception as e:
            print(f"⚠️ Could not fetch fraud alerts: {e}")
        
        print(f"\n🎉 Bulk save completed!")
        print(f"   ✅ Transactions saved: {saved_count}")
        print(f"   ❌ Transactions failed: {failed_count}")
        print(f"   📊 Total processed: {len(transactions)}")
        
        # Verify saved data
        db_transactions = await transaction_db.get_transactions(1000)
        print(f"   💾 Database now contains: {len(db_transactions)} transactions")
        
        return {
            "success": True,
            "transactions_saved": saved_count,
            "transactions_failed": failed_count,
            "total_processed": len(transactions)
        }
        
    except Exception as e:
        print(f"❌ Bulk save error: {e}")
        return {"success": False, "error": str(e)}

if __name__ == "__main__":
    result = asyncio.run(bulk_save_transactions())
    if result["success"]:
        print("✅ Bulk save successful!")
    else:
        print("❌ Bulk save failed!")
        sys.exit(1)