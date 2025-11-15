"""
Authentication and Authorization Service
"""
import os
import jwt
import hashlib
from datetime import datetime, timedelta
from typing import Optional, List
from app.models.user import User, UserRole, Permission, ROLE_PERMISSIONS, UserLogin, Token, AuditLog
import uuid


# Secret key for JWT (in production, use environment variable)
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "finsentinel-super-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 480  # 8 hours


class AuthService:
    """Authentication and Authorization Service"""
    
    def __init__(self):
        # In-memory user storage (replace with database in production)
        self.users = {}
        self.audit_logs = []
        self._init_default_users()
    
    def _init_default_users(self):
        """Initialize default users"""
        default_users = [
            {
                "id": "user_1",
                "username": "admin",
                "email": "admin@finsentinel.ai",
                "password": self._hash_password("admin123"),
                "full_name": "System Administrator",
                "role": UserRole.ADMIN,
                "is_active": True,
                "created_at": datetime.now(),
            },
            {
                "id": "user_2",
                "username": "analyst",
                "email": "analyst@finsentinel.ai",
                "password": self._hash_password("analyst123"),
                "full_name": "Fraud Analyst",
                "role": UserRole.ANALYST,
                "is_active": True,
                "created_at": datetime.now(),
            },
            {
                "id": "user_3",
                "username": "viewer",
                "email": "viewer@finsentinel.ai",
                "password": self._hash_password("viewer123"),
                "full_name": "Dashboard Viewer",
                "role": UserRole.VIEWER,
                "is_active": True,
                "created_at": datetime.now(),
            },
        ]
        
        for user_data in default_users:
            self.users[user_data["username"]] = user_data
    
    def _hash_password(self, password: str) -> str:
        """Hash password using SHA256"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def _verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify password"""
        return self._hash_password(plain_password) == hashed_password
    
    def create_access_token(self, user: User) -> str:
        """Create JWT access token"""
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        to_encode = {
            "sub": user.username,
            "user_id": user.id,
            "role": user.role.value,
            "exp": expire
        }
        return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    
    def verify_token(self, token: str) -> Optional[dict]:
        """Verify JWT token"""
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.JWTError:
            return None
    
    def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """Authenticate user"""
        user_data = self.users.get(username)
        if not user_data:
            return None
        
        if not self._verify_password(password, user_data["password"]):
            return None
        
        if not user_data["is_active"]:
            return None
        
        # Update last login
        user_data["last_login"] = datetime.now()
        
        return User(**{k: v for k, v in user_data.items() if k != "password"})
    
    def login(self, login_data: UserLogin) -> Optional[Token]:
        """User login"""
        user = self.authenticate_user(login_data.username, login_data.password)
        if not user:
            return None
        
        access_token = self.create_access_token(user)
        
        # Log authentication
        self.log_action(
            user_id=user.id,
            username=user.username,
            action="LOGIN",
            resource="auth",
            details={"success": True}
        )
        
        return Token(access_token=access_token, user=user)
    
    def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username"""
        user_data = self.users.get(username)
        if not user_data:
            return None
        return User(**{k: v for k, v in user_data.items() if k != "password"})
    
    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID"""
        for user_data in self.users.values():
            if user_data["id"] == user_id:
                return User(**{k: v for k, v in user_data.items() if k != "password"})
        return None
    
    def get_all_users(self) -> List[User]:
        """Get all users"""
        return [
            User(**{k: v for k, v in user_data.items() if k != "password"})
            for user_data in self.users.values()
        ]
    
    def create_user(self, username: str, email: str, password: str, full_name: str, role: UserRole) -> User:
        """Create new user"""
        if username in self.users:
            raise ValueError("Username already exists")
        
        user_id = f"user_{len(self.users) + 1}"
        user_data = {
            "id": user_id,
            "username": username,
            "email": email,
            "password": self._hash_password(password),
            "full_name": full_name,
            "role": role,
            "is_active": True,
            "created_at": datetime.now(),
        }
        
        self.users[username] = user_data
        return User(**{k: v for k, v in user_data.items() if k != "password"})
    
    def update_user(self, username: str, **updates) -> Optional[User]:
        """Update user"""
        user_data = self.users.get(username)
        if not user_data:
            return None
        
        # Update allowed fields
        allowed_fields = ["email", "full_name", "role", "is_active"]
        for field, value in updates.items():
            if field in allowed_fields and value is not None:
                user_data[field] = value
        
        return User(**{k: v for k, v in user_data.items() if k != "password"})
    
    def delete_user(self, username: str) -> bool:
        """Delete user"""
        if username in self.users:
            del self.users[username]
            return True
        return False
    
    def has_permission(self, user: User, permission: Permission) -> bool:
        """Check if user has specific permission"""
        role_permissions = ROLE_PERMISSIONS.get(user.role, [])
        return permission in role_permissions
    
    def get_user_permissions(self, user: User) -> List[Permission]:
        """Get all permissions for user"""
        return ROLE_PERMISSIONS.get(user.role, [])
    
    def log_action(self, user_id: str, username: str, action: str, resource: str, details: dict = None, ip_address: str = None):
        """Log user action for audit trail"""
        log = AuditLog(
            id=f"log_{uuid.uuid4().hex[:8]}",
            user_id=user_id,
            username=username,
            action=action,
            resource=resource,
            details=details,
            ip_address=ip_address,
            timestamp=datetime.now()
        )
        self.audit_logs.append(log)
        
        # Keep only last 1000 logs
        if len(self.audit_logs) > 1000:
            self.audit_logs = self.audit_logs[-1000:]
    
    def get_audit_logs(self, user_id: Optional[str] = None, limit: int = 100) -> List[AuditLog]:
        """Get audit logs"""
        logs = self.audit_logs
        
        if user_id:
            logs = [log for log in logs if log.user_id == user_id]
        
        return logs[-limit:]


# Global auth service instance
auth_service = AuthService()
