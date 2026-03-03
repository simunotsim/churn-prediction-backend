"""
Authentication service
Business logic for user authentication and authorization
Must NOT directly manipulate SQLAlchemy session or contain raw SQL
"""

from datetime import timedelta, datetime
from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.repositories.user_repository import UserRepository
from app.schemas.auth_schema import UserRegister, UserLogin, UserResponse, Token, RegisterResponse
from app.core.security import verify_password, create_access_token, hash_password
from app.core.config import get_settings
from app.core.logging_config import get_logger

settings = get_settings()
logger = get_logger(__name__)


class AuthService:
    """Authentication service for user management"""

    def __init__(self, db: Session):
        self.db = db
        self.user_repo = UserRepository()

    def register_user(self, user_data: UserRegister) -> RegisterResponse:
        """
        Register a new user

        Returns:
            {"message": "User created"} per API contract
        """
        # Check if email exists
        if self.user_repo.get_by_email(self.db, user_data.email):
            logger.warning(f"Registration attempt with existing email: {user_data.email}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )

        # Check if username exists
        if self.user_repo.get_by_username(self.db, user_data.username):
            logger.warning(f"Registration attempt with existing username: {user_data.username}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken",
            )

        # Create user
        try:
            hashed_pw = hash_password(user_data.password)
            self.user_repo.create(
                self.db,
                email=user_data.email,
                username=user_data.username,
                hashed_password=hashed_pw,
                full_name=user_data.full_name,
                company=user_data.company,
            )
            logger.info(f"New user registered: {user_data.email}")
            return RegisterResponse(message="User created")
        except Exception as e:
            logger.error(f"Failed to register user: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create user",
            )

    def authenticate_user(self, login_data: UserLogin) -> Token:
        """
        Authenticate user and generate access token
        Implements account lock after MAX_FAILED_LOGIN_ATTEMPTS
        """
        user = self.user_repo.get_by_email(self.db, login_data.email)

        if not user:
            logger.warning(f"Login attempt with non-existent email: {login_data.email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Check account lock
        if user.locked_until and user.locked_until > datetime.utcnow():
            logger.warning(f"Login attempt on locked account: {user.email}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is locked. Try again later.",
            )

        # Verify password
        if not verify_password(login_data.password, user.hashed_password):
            logger.warning(f"Failed login attempt for user: {user.email}")
            self.user_repo.increment_failed_login(self.db, user.id)

            # Lock account after N failed attempts
            if (user.failed_login_attempts or 0) + 1 >= settings.MAX_FAILED_LOGIN_ATTEMPTS:
                lock_until = datetime.utcnow() + timedelta(minutes=settings.ACCOUNT_LOCK_MINUTES)
                self.user_repo.lock_account(self.db, user.id, lock_until)
                logger.warning(f"Account locked due to failed attempts: {user.email}")

            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Check if user is active
        if not user.is_active:
            logger.warning(f"Login attempt by inactive user: {user.email}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is inactive",
            )

        # Reset failed login attempts on success
        self.user_repo.reset_failed_login(self.db, user.id)

        # Create access token (60-minute expiry per spec)
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={
                "user_id": user.id,
                "email": user.email,
                "username": user.username,
            },
            expires_delta=access_token_expires,
        )

        logger.info(f"User logged in: {user.email}")
        return Token(access_token=access_token, token_type="bearer")

    def get_current_user(self, user_id: int) -> Optional[UserResponse]:
        """Get current user by ID"""
        user = self.user_repo.get_by_id(self.db, user_id)
        if user:
            return UserResponse.model_validate(user)
        return None
