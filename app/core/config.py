"""
Application configuration using Pydantic Settings
Environment-based configuration for production deployment
"""

import os
from pathlib import Path
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field, validator


class Settings(BaseSettings):
    """Application settings with environment variable support"""

    # Application Info
    APP_NAME: str = "Churn Prediction API"
    APP_VERSION: str = "2.0.0"
    DEBUG: bool = Field(False, env="DEBUG")
    ENV: str = Field("production", env="ENV")

    # API Configuration
    API_HOST: str = Field("0.0.0.0", env="API_HOST")
    API_PORT: int = Field(8000, env="API_PORT")
    API_PREFIX: str = Field("", env="API_PREFIX")

    # CORS Settings
    ALLOWED_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:5173", "http://localhost:8501"],
        env="ALLOWED_ORIGINS",
    )

    # Security
    SECRET_KEY: str = Field(..., env="SECRET_KEY")
    ALGORITHM: str = Field("HS256", env="ALGORITHM")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(60, env="ACCESS_TOKEN_EXPIRE_MINUTES")

    # Rate Limiting & Account Lock
    RATE_LIMIT_PER_MINUTE: int = Field(100, env="RATE_LIMIT_PER_MINUTE")
    MAX_FAILED_LOGIN_ATTEMPTS: int = Field(5, env="MAX_FAILED_LOGIN_ATTEMPTS")
    ACCOUNT_LOCK_MINUTES: int = Field(30, env="ACCOUNT_LOCK_MINUTES")

    # Database
    DATABASE_URL: Optional[str] = Field(None, env="DATABASE_URL")
    DB_POOL_SIZE: int = Field(10, env="DB_POOL_SIZE")
    DB_MAX_OVERFLOW: int = Field(10, env="DB_MAX_OVERFLOW")
    DB_POOL_RECYCLE: int = Field(300, env="DB_POOL_RECYCLE")

    # Redis (for Celery)
    REDIS_URL: str = Field("redis://localhost:6379/0", env="REDIS_URL")
    CELERY_BROKER_URL: str = Field("redis://localhost:6379/0", env="CELERY_BROKER_URL")
    CELERY_RESULT_BACKEND: str = Field("redis://localhost:6379/0", env="CELERY_RESULT_BACKEND")

    # Paths
    PROJECT_ROOT: Path = Field(default_factory=lambda: Path(__file__).resolve().parent.parent.parent.parent)
    MODELS_PATH: Optional[Path] = Field(None, env="MODELS_PATH")
    MODEL_PATH: Optional[str] = Field(None, env="MODEL_PATH")
    DATA_PATH: Optional[Path] = Field(None, env="DATA_PATH")

    # Model Files
    MODEL_FILE: str = Field("xgb_tuned_model.pkl", env="MODEL_FILE")
    SCALER_FILE: str = Field("scaler.pkl", env="SCALER_FILE")
    ENCODERS_FILE: str = Field("label_encoders.pkl", env="ENCODERS_FILE")

    # ML Parameters
    CHURN_THRESHOLD: float = Field(0.5, env="CHURN_THRESHOLD")
    HIGH_RISK_THRESHOLD: float = Field(0.7, env="HIGH_RISK_THRESHOLD")
    CRITICAL_RISK_THRESHOLD: float = Field(0.85, env="CRITICAL_RISK_THRESHOLD")

    # Upload Limits
    MAX_CSV_SIZE_MB: int = Field(10, env="MAX_CSV_SIZE_MB")
    MAX_ROWS: int = Field(10000, env="MAX_ROWS")

    # Logging
    LOG_LEVEL: str = Field("INFO", env="LOG_LEVEL")
    LOG_FILE: Optional[str] = Field(None, env="LOG_FILE")

    @validator("ALLOWED_ORIGINS", pre=True)
    def parse_cors_origins(cls, v):
        """Parse comma-separated CORS origins"""
        if isinstance(v, str):
            if v == "*":
                return ["*"]
            return [origin.strip() for origin in v.split(",")]
        return v

    @validator("MODELS_PATH", pre=True, always=True)
    def set_models_path(cls, v, values):
        """Set models path relative to project root"""
        if v is None:
            model_path = values.get("MODEL_PATH")
            if model_path:
                return Path(model_path)
            return values.get("PROJECT_ROOT") / "models"
        return Path(v) if not isinstance(v, Path) else v

    @validator("DATA_PATH", pre=True, always=True)
    def set_data_path(cls, v, values):
        """Set data path relative to project root"""
        if v is None:
            return values.get("PROJECT_ROOT") / "data" / "processed"
        return Path(v) if not isinstance(v, Path) else v

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"


# Global settings instance
try:
    settings = Settings()
except Exception as e:
    # Fallback for missing SECRET_KEY
    import secrets
    os.environ.setdefault("SECRET_KEY", secrets.token_urlsafe(32))
    settings = Settings()


def get_settings() -> Settings:
    """Get application settings (dependency injection)"""
    return settings
