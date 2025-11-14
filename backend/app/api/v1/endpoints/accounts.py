"""
Accounts API Endpoints

Handles account management and information retrieval.
"""

from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.database import get_db
from app.models.transaction import Account, AccountResponse, Transaction

router = APIRouter()


@router.get("/", response_model=List[AccountResponse])
async def get_accounts(db: Session = Depends(get_db)):
    """
    Get all connected accounts
    """
    accounts = db.query(Account).all()
    return accounts


@router.get("/{account_id}", response_model=AccountResponse)
async def get_account(account_id: str, db: Session = Depends(get_db)):
    """
    Get specific account details
    """
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    return account


@router.get("/{account_id}/balance")
async def get_account_balance(account_id: str, db: Session = Depends(get_db)):
    """
    Get current account balance with recent activity
    """
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    # Get recent transaction summary
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    recent_activity = db.query(
        func.count(Transaction.id).label('transaction_count'),
        func.sum(Transaction.amount).label('net_change'),
        func.sum(Transaction.amount).filter(Transaction.amount > 0).label('credits'),
        func.sum(Transaction.amount).filter(Transaction.amount < 0).label('debits')
    ).filter(
        Transaction.account_id == account_id,
        Transaction.created_at >= seven_days_ago
    ).first()
    
    return {
        "account_id": account_id,
        "current_balance": account.balance,
        "available_balance": account.available_balance,
        "currency": account.currency_code,
        "recent_activity": {
            "period_days": 7,
            "transaction_count": recent_activity.transaction_count or 0,
            "net_change": float(recent_activity.net_change or 0),
            "total_credits": float(recent_activity.credits or 0),
            "total_debits": float(abs(recent_activity.debits or 0))
        }
    }


@router.get("/{account_id}/summary")
async def get_account_summary(
    account_id: str,
    days: int = 30,
    db: Session = Depends(get_db)
):
    """
    Get comprehensive account summary and analytics
    """
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    since = datetime.utcnow() - timedelta(days=days)
    
    # Transaction statistics
    transactions = db.query(Transaction).filter(
        Transaction.account_id == account_id,
        Transaction.created_at >= since
    ).all()
    
    # Calculate summary metrics
    total_transactions = len(transactions)
    credits = [tx.amount for tx in transactions if tx.amount > 0]
    debits = [abs(tx.amount) for tx in transactions if tx.amount < 0]
    
    summary = {
        "account_info": {
            "id": account.id,
            "name": account.name,
            "type": account.type,
            "subtype": account.subtype,
            "current_balance": account.balance,
            "available_balance": account.available_balance,
            "currency": account.currency_code
        },
        "period_analysis": {
            "period_days": days,
            "total_transactions": total_transactions,
            "transaction_frequency": total_transactions / days if days > 0 else 0,
            "credits": {
                "count": len(credits),
                "total": sum(credits),
                "average": sum(credits) / len(credits) if credits else 0,
                "largest": max(credits) if credits else 0
            },
            "debits": {
                "count": len(debits),
                "total": sum(debits),
                "average": sum(debits) / len(debits) if debits else 0,
                "largest": max(debits) if debits else 0
            },
            "net_change": sum(tx.amount for tx in transactions)
        },
        "spending_categories": {},
        "merchant_analysis": {}
    }
    
    # Category and merchant analysis
    for tx in transactions:
        if tx.amount < 0:  # Spending transactions
            categories = tx.category or ["Other"]
            for category in categories:
                summary["spending_categories"][category] = summary["spending_categories"].get(category, 0) + abs(tx.amount)
            
            merchant = tx.merchant_name or "Unknown"
            summary["merchant_analysis"][merchant] = summary["merchant_analysis"].get(merchant, 0) + abs(tx.amount)
    
    # Sort by spending amount
    summary["spending_categories"] = dict(sorted(
        summary["spending_categories"].items(),
        key=lambda x: x[1],
        reverse=True
    ))
    
    summary["merchant_analysis"] = dict(sorted(
        summary["merchant_analysis"].items(),
        key=lambda x: x[1],
        reverse=True
    )[:10])  # Top 10 merchants
    
    return summary