"""
Security utilities: password hashing (bcrypt) and JWT token management
Production-ready authentication with proper password hashing
Supports legacy SHA-256 salt$hash passwords from the original schema
"""

import hashlib
from datetime import datetime, timedelta
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings

settings = get_settings()

# =============================================================================
# PASSWORD HASHING (bcrypt via passlib)
# =============================================================================

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str, salt: Optional[str] = None) -> str:
    """
    Hash password using bcrypt

    Args:
        password: Plain text password
        salt: Ignored (bcrypt generates its own salt)

    Returns:
        Bcrypt hashed password
    """
    return pwd_context.hash(password)


def _verify_legacy_sha256(plain_password: str, hashed_password: str) -> bool:
    """
    Verify password against legacy salt$sha256hash format
    used by the original auth/utils.py schema.
    """
    parts = hashed_password.split("$")
    if len(parts) != 2:
        return False
    salt, stored_hash = parts
    salted = f"{salt}${plain_password}"
    computed = hashlib.sha256(salted.encode()).hexdigest()
    return computed == stored_hash


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash.
    Supports both bcrypt ($2b$...) and legacy SHA-256 (salt$hash) formats.

    Args:
        plain_password: Plain text password to verify
        hashed_password: Stored hash (bcrypt or legacy SHA-256)

    Returns:
        True if password matches, False otherwise
    """
    try:
        # Bcrypt hashes always start with $2b$ (or $2a$, $2y$)
        if hashed_password.startswith(("$2b$", "$2a$", "$2y$")):
            return pwd_context.verify(plain_password, hashed_password)
        # Otherwise try legacy SHA-256 salt$hash format
        return _verify_legacy_sha256(plain_password, hashed_password)
    except Exception:
        return False


# =============================================================================
# JWT TOKEN MANAGEMENT
# =============================================================================

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token

    Args:
        data: Data to encode in token (user_id, email, etc.)
        expires_delta: Optional custom expiration time

    Returns:
        Encoded JWT token
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Optional[dict]:
    """
    Decode and validate a JWT token

    Args:
        token: JWT token string

    Returns:
        Decoded token payload or None if invalid
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None
