"""
Authentication router
HTTP endpoints for user registration and login
No DB logic, no ML logic — calls service layer only
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.services.auth_service import AuthService
from app.schemas.auth_schema import (
    UserRegister,
    UserLogin,
    UserResponse,
    Token,
    RegisterResponse,
)
from app.core.security import decode_access_token
from app.core.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])

# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


# =============================================================================
# DEPENDENCIES
# =============================================================================


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> UserResponse:
    """
    Get current authenticated user from JWT token
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception

    user_id: int = payload.get("user_id")
    if user_id is None:
        raise credentials_exception

    auth_service = AuthService(db)
    user = auth_service.get_current_user(user_id)

    if user is None:
        raise credentials_exception

    return user


async def get_current_active_user(
    current_user: UserResponse = Depends(get_current_user),
) -> UserResponse:
    """Ensure user is active"""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )
    return current_user


# =============================================================================
# ENDPOINTS (per API contract)
# =============================================================================


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserRegister, db: Session = Depends(get_db)):
    """
    POST /auth/register
    Request: {"email": "", "username": "", "password": ""}
    Response: {"message": "User created"}
    """
    auth_service = AuthService(db)
    return auth_service.register_user(user_data)


@router.post("/login", response_model=Token)
async def login(login_data: UserLogin, db: Session = Depends(get_db)):
    """
    POST /auth/login
    Response: {"access_token": "", "token_type": "bearer"}
    """
    auth_service = AuthService(db)
    return auth_service.authenticate_user(login_data)


@router.post("/login-json", response_model=Token)
async def login_json(login_data: UserLogin, db: Session = Depends(get_db)):
    """
    POST /auth/login-json (alias for /login)
    Response: {"access_token": "", "token_type": "bearer"}
    """
    auth_service = AuthService(db)
    return auth_service.authenticate_user(login_data)


@router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """
    OAuth2 compatible token login (for swagger UI)
    """
    login_data = UserLogin(email=form_data.username, password=form_data.password)
    auth_service = AuthService(db)
    return auth_service.authenticate_user(login_data)


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: UserResponse = Depends(get_current_active_user),
):
    """Get current user information (requires JWT)"""
    return current_user
