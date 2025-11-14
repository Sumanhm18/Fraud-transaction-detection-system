"""
Transaction API Endpoints

Handles transaction management, analysis, and real-time monitoring.
"""

from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from app.core.database import get_db
from app.models.transaction import Transaction, TransactionResponse
from app.services.orchestrator import orchestrator

router = APIRouter()


@router.get("/", response_model=List[TransactionResponse])
async def get_transactions(
    db: Session = Depends(get_db),
    account_id: Optional[str] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    limit: int = Query(100, le=1000),
    offset: int = Query(0, ge=0)
):
    """
    Retrieve transactions with optional filtering
    """
    query = db.query(Transaction)
    
    if account_id:
        query = query.filter(Transaction.account_id == account_id)
    
    if start_date:
        query = query.filter(Transaction.date >= start_date)
    
    if end_date:
        query = query.filter(Transaction.date <= end_date)
    
    transactions = query.order_by(desc(Transaction.created_at)).offset(offset).limit(limit).all()
    return transactions


@router.get("/{transaction_id}", response_model=TransactionResponse)
async def get_transaction(transaction_id: str, db: Session = Depends(get_db)):
    """
    Get specific transaction details
    """
    transaction = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return transaction


@router.get("/analysis/velocity")
async def get_velocity_analysis(
    account_id: Optional[str] = Query(None),
    hours: int = Query(24, ge=1, le=168),  # 1 hour to 1 week
    db: Session = Depends(get_db)
):
    """
    Get transaction velocity analysis
    """
    since = datetime.utcnow() - timedelta(hours=hours)
    query = db.query(
        func.count(Transaction.id).label('count'),
        func.sum(Transaction.amount).label('total_amount'),
        func.avg(Transaction.amount).label('avg_amount')
    ).filter(Transaction.created_at >= since)
    
    if account_id:
        query = query.filter(Transaction.account_id == account_id)
    
    result = query.first()
    
    return {
        "period_hours": hours,
        "transaction_count": result.count or 0,
        "total_amount": float(result.total_amount or 0),
        "average_amount": float(result.avg_amount or 0),
        "velocity_per_hour": (result.count or 0) / hours
    }


@router.get("/analysis/patterns")
async def get_transaction_patterns(
    account_id: Optional[str] = Query(None),
    days: int = Query(30, ge=7, le=365),
    db: Session = Depends(get_db)
):
    """
    Get transaction pattern analysis
    """
    since = datetime.utcnow() - timedelta(days=days)
    query = db.query(Transaction).filter(Transaction.created_at >= since)
    
    if account_id:
        query = query.filter(Transaction.account_id == account_id)
    
    transactions = query.all()
    
    # Analyze patterns
    patterns = {
        "total_transactions": len(transactions),
        "merchant_frequency": {},
        "category_distribution": {},
        "hourly_distribution": {},
        "daily_distribution": {},
        "amount_ranges": {
            "small": 0,    # < $50
            "medium": 0,   # $50-$500
            "large": 0,    # $500-$5000
            "very_large": 0 # > $5000
        }
    }
    
    for tx in transactions:
        # Merchant frequency
        merchant = tx.merchant_name or "Unknown"
        patterns["merchant_frequency"][merchant] = patterns["merchant_frequency"].get(merchant, 0) + 1
        
        # Category distribution
        categories = tx.category or []
        for category in categories:
            patterns["category_distribution"][category] = patterns["category_distribution"].get(category, 0) + 1
        
        # Time patterns
        hour = tx.date.hour
        day = tx.date.strftime('%A')
        patterns["hourly_distribution"][hour] = patterns["hourly_distribution"].get(hour, 0) + 1
        patterns["daily_distribution"][day] = patterns["daily_distribution"].get(day, 0) + 1
        
        # Amount ranges
        amount = abs(tx.amount)
        if amount < 50:
            patterns["amount_ranges"]["small"] += 1
        elif amount < 500:
            patterns["amount_ranges"]["medium"] += 1
        elif amount < 5000:
            patterns["amount_ranges"]["large"] += 1
        else:
            patterns["amount_ranges"]["very_large"] += 1
    
    # Sort by frequency
    patterns["merchant_frequency"] = dict(sorted(
        patterns["merchant_frequency"].items(), 
        key=lambda x: x[1], 
        reverse=True
    )[:10])  # Top 10 merchants
    
    return patterns


@router.post("/{transaction_id}/reanalyze")
async def reanalyze_transaction(transaction_id: str, db: Session = Depends(get_db)):
    """
    Trigger re-analysis of a specific transaction
    """
    transaction = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    # Trigger re-analysis through orchestrator
    result = await orchestrator.analyze_transaction(transaction)
    
    return {
        "transaction_id": transaction_id,
        "reanalysis_triggered": True,
        "fraud_score": result.get("fraud_score"),
        "risk_factors": result.get("risk_factors", [])
    }