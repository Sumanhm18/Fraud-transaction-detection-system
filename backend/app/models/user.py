"""
User and Role Models for Authentication and Authorization
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel
from enum import Enum


class UserRole(str, Enum):
    """User roles for role-based access control"""
    ADMIN = "admin"
    ANALYST = "analyst"
    VIEWER = "viewer"
    AUDITOR = "auditor"


class Permission(str, Enum):
    """Granular permissions"""
    # Transaction permissions
    VIEW_TRANSACTIONS = "view_transactions"
    CREATE_TRANSACTIONS = "create_transactions"
    DELETE_TRANSACTIONS = "delete_transactions"
    
    # Fraud detection permissions
    VIEW_FRAUD_ALERTS = "view_fraud_alerts"
    MANAGE_FRAUD_ALERTS = "manage_fraud_alerts"
    CONFIGURE_ML_MODEL = "configure_ml_model"
    
    # Blockchain permissions
    VIEW_BLOCKCHAIN = "view_blockchain"
    QUERY_BLOCKCHAIN = "query_blockchain"
    
    # User management permissions
    VIEW_USERS = "view_users"
    CREATE_USERS = "create_users"
    UPDATE_USERS = "update_users"
    DELETE_USERS = "delete_users"
    
    # System permissions
    VIEW_ANALYTICS = "view_analytics"
    VIEW_LOGS = "view_logs"
    MANAGE_SETTINGS = "manage_settings"
    SEND_NOTIFICATIONS = "send_notifications"


# Role to Permissions mapping
ROLE_PERMISSIONS = {
    UserRole.ADMIN: [
        Permission.VIEW_TRANSACTIONS,
        Permission.CREATE_TRANSACTIONS,
        Permission.DELETE_TRANSACTIONS,
        Permission.VIEW_FRAUD_ALERTS,
        Permission.MANAGE_FRAUD_ALERTS,
        Permission.CONFIGURE_ML_MODEL,
        Permission.VIEW_BLOCKCHAIN,
        Permission.QUERY_BLOCKCHAIN,
        Permission.VIEW_USERS,
        Permission.CREATE_USERS,
        Permission.UPDATE_USERS,
        Permission.DELETE_USERS,
        Permission.VIEW_ANALYTICS,
        Permission.VIEW_LOGS,
        Permission.MANAGE_SETTINGS,
        Permission.SEND_NOTIFICATIONS,
    ],
    UserRole.ANALYST: [
        Permission.VIEW_TRANSACTIONS,
        Permission.CREATE_TRANSACTIONS,
        Permission.VIEW_FRAUD_ALERTS,
        Permission.MANAGE_FRAUD_ALERTS,
        Permission.VIEW_BLOCKCHAIN,
        Permission.QUERY_BLOCKCHAIN,
        Permission.VIEW_ANALYTICS,
    ],
    UserRole.VIEWER: [
        Permission.VIEW_TRANSACTIONS,
        Permission.VIEW_FRAUD_ALERTS,
        Permission.VIEW_BLOCKCHAIN,
        Permission.VIEW_ANALYTICS,
    ],
    UserRole.AUDITOR: [
        Permission.VIEW_TRANSACTIONS,
        Permission.VIEW_FRAUD_ALERTS,
        Permission.VIEW_BLOCKCHAIN,
        Permission.QUERY_BLOCKCHAIN,
        Permission.VIEW_ANALYTICS,
        Permission.VIEW_LOGS,
    ],
}


class User(BaseModel):
    """User model"""
    id: str
    username: str
    email: str
    full_name: str
    role: UserRole
    is_active: bool = True
    created_at: datetime = datetime.now()
    last_login: Optional[datetime] = None


class UserCreate(BaseModel):
    """User creation model"""
    username: str
    email: str
    password: str
    full_name: str
    role: UserRole = UserRole.VIEWER


class UserUpdate(BaseModel):
    """User update model"""
    email: Optional[str] = None
    full_name: Optional[str] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None


class UserLogin(BaseModel):
    """User login model"""
    username: str
    password: str


class Token(BaseModel):
    """JWT Token model"""
    access_token: str
    token_type: str = "bearer"
    user: User


class AuditLog(BaseModel):
    """Audit log model"""
    id: str
    user_id: str
    username: str
    action: str
    resource: str
    details: Optional[dict] = None
    ip_address: Optional[str] = None
    timestamp: datetime = datetime.now()
