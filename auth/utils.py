"""
Authentication utilities for the Churn Prediction API
Password hashing and JWT token management
"""

import os
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from pydantic import BaseModel

# =============================================================================
# CONFIGURATION
# =============================================================================

# Secret key for JWT (in production, use a strong secret from environment)
SECRET_KEY = os.getenv("SECRET_KEY", "your-super-secret-key-change-in-production-12345")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))  # 24 hours


# =============================================================================
# PYDANTIC MODELS
# =============================================================================

class Token(BaseModel):
    """JWT Token response"""
    access_token: str
    token_type: str


class TokenData(BaseModel):
    """Data encoded in JWT token"""
    user_id: Optional[int] = None
    email: Optional[str] = None
    username: Optional[str] = None


class UserCreate(BaseModel):
    """User registration request"""
    email: str
    username: str
    password: str
    full_name: Optional[str] = None
    company: Optional[str] = None


class UserLogin(BaseModel):
    """User login request"""
    email: str
    password: str


class UserResponse(BaseModel):
    """User response (no password)"""
    id: int
    email: str
    username: str
    full_name: Optional[str] = None
    company: Optional[str] = None
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


# =============================================================================
# PASSWORD UTILITIES (Using SHA-256 with salt - simpler, no bcrypt dependency issues)
# =============================================================================

def _hash_password_sha256(password: str, salt: str = None) -> str:
    """Hash password using SHA-256 with salt"""
    if salt is None:
        salt = secrets.token_hex(16)
    
    # Combine password and salt, then hash
    salted = f"{salt}${password}"
    hashed = hashlib.sha256(salted.encode()).hexdigest()
    
    # Return salt$hash format
    return f"{salt}${hashed}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    try:
        # Extract salt from stored hash
        parts = hashed_password.split("$")
        if len(parts) != 2:
            return False
        
        salt = parts[0]
        # Rehash with same salt and compare
        rehashed = _hash_password_sha256(plain_password, salt)
        return rehashed == hashed_password
    except Exception:
        return False


def get_password_hash(password: str) -> str:
    """Hash a password"""
    return _hash_password_sha256(password)


# =============================================================================
# JWT TOKEN UTILITIES
# =============================================================================

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token"""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> Optional[TokenData]:
    """Decode and validate a JWT token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("user_id")
        email: str = payload.get("email")
        username: str = payload.get("username")
        
        if email is None:
            return None
        
        return TokenData(user_id=user_id, email=email, username=username)
    except JWTError:
        return None
