"""
Quick test script to verify email sending functionality
"""
import asyncio
import sys
sys.path.append('/Users/sumanhm/Downloads/finance/backend')

from app.services.email_service import email_service
from datetime import datetime

async def test_fraud_email():
    """Send a test fraud alert email"""
    
    print("=" * 60)
    print("EMAIL SERVICE TEST")
    print("=" * 60)
    print(f"Email Enabled: {email_service.enabled}")
    print(f"SMTP Server: {email_service.smtp_server}:{email_service.smtp_port}")
    print(f"Sender: {email_service.sender_email}")
    print(f"Password Configured: {bool(email_service.sender_password)}")
    print(f"Recipient: {email_service.default_recipient}")
    print("=" * 60)
    
    # Create test fraud alert
    test_alert = {
        "id": "test_alert_001",
        "transaction_id": "test_tx_001",
        "alert_type": "FRAUD_DETECTION",
        "severity": "HIGH",
        "message": "TEST: High-risk transaction detected",
        "client_ip": "192.168.28.162",
        "is_resolved": False,
        "risk_factors": [
            "Unusual merchant",
            "Large transaction amount",
            "Different device IP"
        ]
    }
    
    # Create test transaction
    test_transaction = {
        "id": "test_tx_001",
        "account_id": "acc_demo_001",
        "amount": 9999.99,
        "merchant_name": "Suspicious Overseas Merchant",
        "category": ["transfers"],
        "date": datetime.now().isoformat(),
        "fraud_score": 0.95,
        "risk_factors": test_alert["risk_factors"],
        "client_ip": "192.168.28.162"
    }
    
    print("\n📧 Sending test fraud alert email...")
    print(f"Alert ID: {test_alert['id']}")
    print(f"Transaction: ${test_transaction['amount']:.2f} at {test_transaction['merchant_name']}")
    print(f"Fraud Score: {test_transaction['fraud_score']:.1%}")
    print(f"Device IP: {test_transaction['client_ip']}")
    
    try:
        result = await email_service.send_fraud_alert(
            alert=test_alert,
            transaction=test_transaction
        )
        
        if result:
            print("\n✅ SUCCESS: Email sent successfully!")
            print(f"   Check inbox: {email_service.default_recipient}")
        else:
            print("\n❌ FAILED: Email was not sent")
            print("   Check SMTP configuration and credentials")
            
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
    
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_fraud_email())
