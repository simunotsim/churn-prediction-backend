"""
User repository for database operations
Handles all user-related database queries
No business logic - only DB access
"""

from typing import Optional, List
from sqlalchemy.orm import Session
from datetime import datetime

from app.models.user_model import User
from app.core.security import hash_password


class UserRepository:
    """Repository for user database operations"""

    @staticmethod
    def get_by_id(db: Session, user_id: int) -> Optional[User]:
        """Get user by ID"""
        return db.query(User).filter(User.id == user_id).first()

    @staticmethod
    def get_by_email(db: Session, email: str) -> Optional[User]:
        """Get user by email"""
        return db.query(User).filter(User.email == email).first()

    @staticmethod
    def get_by_username(db: Session, username: str) -> Optional[User]:
        """Get user by username"""
        return db.query(User).filter(User.username == username).first()

    @staticmethod
    def create(
        db: Session,
        email: str,
        username: str,
        hashed_password: str,
        full_name: Optional[str] = None,
        company: Optional[str] = None,
    ) -> User:
        """Create a new user"""
        db_user = User(
            email=email,
            username=username,
            hashed_password=hashed_password,
            full_name=full_name,
            company=company,
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return db_user

    @staticmethod
    def increment_failed_login(db: Session, user_id: int) -> None:
        """Increment failed login attempt counter"""
        db_user = db.query(User).filter(User.id == user_id).first()
        if db_user:
            db_user.failed_login_attempts = (db_user.failed_login_attempts or 0) + 1
            db.commit()

    @staticmethod
    def reset_failed_login(db: Session, user_id: int) -> None:
        """Reset failed login attempts on successful login"""
        db_user = db.query(User).filter(User.id == user_id).first()
        if db_user:
            db_user.failed_login_attempts = 0
            db_user.locked_until = None
            db.commit()

    @staticmethod
    def lock_account(db: Session, user_id: int, locked_until: datetime) -> None:
        """Lock user account until specified time"""
        db_user = db.query(User).filter(User.id == user_id).first()
        if db_user:
            db_user.locked_until = locked_until
            db.commit()

    @staticmethod
    def delete(db: Session, user_id: int) -> bool:
        """Delete a user"""
        db_user = db.query(User).filter(User.id == user_id).first()
        if not db_user:
            return False
        db.delete(db_user)
        db.commit()
        return True
