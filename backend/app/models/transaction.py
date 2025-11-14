"""
Database models for transactions, accounts, and Plaid items
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from uuid import uuid4

from sqlalchemy import Column, String, Float, DateTime, Boolean, JSON, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from pydantic import BaseModel

from app.core.database import Base


class PlaidItem(Base):
    """Plaid item representing a financial institution connection"""
    __tablename__ = "plaid_items"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    item_id = Column(String(255), unique=True, nullable=False, index=True)
    access_token = Column(String(255), nullable=False)
    user_id = Column(String(255), nullable=False, index=True)
    institution_id = Column(String(255), nullable=True)
    institution_name = Column(String(255), nullable=True)
    webhook_url = Column(String(500), nullable=True)
    error_code = Column(String(50), nullable=True)
    available_products = Column(JSON, nullable=True)
    billed_products = Column(JSON, nullable=True)
    consent_expiration_time = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    accounts = relationship("Account", back_populates="plaid_item", cascade="all, delete-orphan")
    transactions = relationship("Transaction", back_populates="plaid_item", cascade="all, delete-orphan")


class Account(Base):
    """Bank account information from Plaid"""
    __tablename__ = "accounts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    account_id = Column(String(255), unique=True, nullable=False, index=True)
    plaid_item_id = Column(UUID(as_uuid=True), ForeignKey("plaid_items.id"), nullable=False)
    name = Column(String(255), nullable=False)
    official_name = Column(String(255), nullable=True)
    type = Column(String(50), nullable=False)  # depository, credit, loan, investment
    subtype = Column(String(50), nullable=False)  # checking, savings, credit card, etc.
    mask = Column(String(10), nullable=True)
    
    # Balance information
    current_balance = Column(Float, nullable=True)
    available_balance = Column(Float, nullable=True)
    credit_limit = Column(Float, nullable=True)
    iso_currency_code = Column(String(3), default="USD")
    
    # Account metadata
    verification_status = Column(String(50), nullable=True)
    persistent_account_id = Column(String(255), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    plaid_item = relationship("PlaidItem", back_populates="accounts")
    transactions = relationship("Transaction", back_populates="account", cascade="all, delete-orphan")


class Transaction(Base):
    """Individual transaction from Plaid"""
    __tablename__ = "transactions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    transaction_id = Column(String(255), unique=True, nullable=False, index=True)
    account_id = Column(String(255), ForeignKey("accounts.account_id"), nullable=False, index=True)
    plaid_item_id = Column(UUID(as_uuid=True), ForeignKey("plaid_items.id"), nullable=False)
    
    # Transaction details
    amount = Column(Float, nullable=False)  # Positive for debits, negative for credits
    iso_currency_code = Column(String(3), default="USD")
    date = Column(DateTime, nullable=False, index=True)
    authorized_date = Column(DateTime, nullable=True)
    
    # Transaction description
    name = Column(String(500), nullable=False)
    merchant_name = Column(String(255), nullable=True)
    original_description = Column(Text, nullable=True)
    
    # Categorization
    category = Column(JSON, nullable=True)  # Array of category strings
    category_id = Column(String(50), nullable=True)
    detailed_category = Column(String(100), nullable=True)
    
    # Location data
    location_data = Column(JSON, nullable=True)  # Complete location object
    
    # Transaction metadata
    payment_channel = Column(String(50), nullable=True)  # online, in store, other
    account_owner = Column(String(255), nullable=True)
    transaction_code = Column(String(50), nullable=True)
    transaction_type = Column(String(50), nullable=True)
    pending = Column(Boolean, default=False)
    pending_transaction_id = Column(String(255), nullable=True)
    
    # FinSentinel AI analysis
    fraud_score = Column(Float, nullable=True)  # 0.0 to 1.0
    anomaly_score = Column(Float, nullable=True)  # 0.0 to 1.0
    risk_factors = Column(JSON, nullable=True)  # Array of detected risk factors
    ml_prediction = Column(JSON, nullable=True)  # ML model predictions
    
    # Blockchain verification
    blockchain_hash = Column(String(66), nullable=True)  # Ethereum transaction hash
    blockchain_verified = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    plaid_item = relationship("PlaidItem", back_populates="transactions")
    account = relationship("Account", back_populates="transactions")


class FraudAlert(Base):
    """Fraud detection alerts"""
    __tablename__ = "fraud_alerts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    transaction_id = Column(String(255), ForeignKey("transactions.transaction_id"), nullable=False)
    alert_type = Column(String(50), nullable=False)  # velocity, location, amount, pattern
    severity = Column(String(20), nullable=False)  # low, medium, high, critical
    confidence = Column(Float, nullable=False)  # 0.0 to 1.0
    
    # Alert details
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    risk_factors = Column(JSON, nullable=False)
    recommended_actions = Column(JSON, nullable=True)
    
    # Status tracking
    status = Column(String(20), default="active")  # active, reviewed, resolved, false_positive
    reviewed_by = Column(String(255), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    resolution_notes = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AuditLog(Base):
    """Comprehensive audit log for all system activities"""
    __tablename__ = "audit_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(String(255), nullable=True, index=True)
    action = Column(String(100), nullable=False)
    resource_type = Column(String(50), nullable=False)  # transaction, account, user, system
    resource_id = Column(String(255), nullable=True)
    
    # Action details
    description = Column(Text, nullable=False)
    metadata = Column(JSON, nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    
    # Blockchain verification
    blockchain_hash = Column(String(66), nullable=True)
    blockchain_verified = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


# Pydantic models for API serialization
class TransactionResponse(BaseModel):
    """Transaction API response model"""
    transaction_id: str
    account_id: str
    amount: float
    iso_currency_code: str
    date: datetime
    name: str
    merchant_name: Optional[str]
    category: Optional[List[str]]
    payment_channel: Optional[str]
    pending: bool
    fraud_score: Optional[float]
    anomaly_score: Optional[float]
    location_data: Optional[Dict[str, Any]]
    
    class Config:
        from_attributes = True


class AccountResponse(BaseModel):
    """Account API response model"""
    account_id: str
    name: str
    official_name: Optional[str]
    type: str
    subtype: str
    mask: Optional[str]
    current_balance: Optional[float]
    available_balance: Optional[float]
    credit_limit: Optional[float]
    iso_currency_code: str
    
    class Config:
        from_attributes = True


class FraudAlertResponse(BaseModel):
    """Fraud alert API response model"""
    id: str
    transaction_id: str
    alert_type: str
    severity: str
    confidence: float
    title: str
    description: str
    status: str
    created_at: datetime
    
    class Config:
        from_attributes = True