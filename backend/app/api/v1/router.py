"""
API Router for FinSentinel AI v1 endpoints
"""

from fastapi import APIRouter

from .endpoints import plaid, transactions, accounts, fraud, analytics, audit

api_router = APIRouter()

# Plaid integration endpoints
api_router.include_router(
    plaid.router, 
    prefix="/plaid", 
    tags=["plaid"]
)

# Transaction endpoints
api_router.include_router(
    transactions.router, 
    prefix="/transactions", 
    tags=["transactions"]
)

# Account endpoints  
api_router.include_router(
    accounts.router, 
    prefix="/accounts", 
    tags=["accounts"]
)

# Fraud detection endpoints
api_router.include_router(
    fraud.router, 
    prefix="/fraud", 
    tags=["fraud"]
)

# Analytics and forecasting endpoints
api_router.include_router(
    analytics.router, 
    prefix="/analytics", 
    tags=["analytics"]
)

# Audit and compliance endpoints
api_router.include_router(
    audit.router, 
    prefix="/audit", 
    tags=["audit"]
)