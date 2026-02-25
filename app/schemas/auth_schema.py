"""
Authentication schemas for request/response validation
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, validator


# =============================================================================
# TOKEN SCHEMAS
# =============================================================================

class Token(BaseModel):
    """JWT Token response"""
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Data encoded in JWT token"""
    user_id: Optional[int] = None
    email: Optional[str] = None
    username: Optional[str] = None


# =============================================================================
# USER SCHEMAS
# =============================================================================

class UserRegister(BaseModel):
    """User registration request per API contract"""
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=100)
    password: str = Field(..., min_length=8, max_length=100)

    @validator("password")
    def validate_password(cls, v):
        """Ensure password meets security requirements"""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class UserLogin(BaseModel):
    """User login request"""
    email: EmailStr
    password: str


class RegisterResponse(BaseModel):
    """Registration response per API contract"""
    message: str = "User created"


class UserResponse(BaseModel):
    """User response (no password)"""
    id: int
    email: str
    username: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# Backward compatibility aliases
UserBase = UserRegister
UserCreate = UserRegister
