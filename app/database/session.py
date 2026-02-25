"""
Database session management and connection
Handles MySQL connection with proper pooling for production
"""

from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool

from app.core.config import get_settings
from app.core.logging import get_logger
from app.database.base import Base

settings = get_settings()
logger = get_logger(__name__)

# =============================================================================
# DATABASE ENGINE SETUP
# =============================================================================

engine = None
SessionLocal = None

if settings.DATABASE_URL:
    try:
        # Create engine with connection pooling
        engine = create_engine(
            settings.DATABASE_URL,
            pool_size=settings.DB_POOL_SIZE,
            max_overflow=settings.DB_MAX_OVERFLOW,
            pool_pre_ping=True,  # Verify connections before using
            pool_recycle=settings.DB_POOL_RECYCLE,  # Recycle after 5 minutes
            echo=settings.DEBUG,  # Log SQL in debug mode
        )
        
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        logger.info("Database engine created successfully")
        
    except Exception as e:
        logger.error(f"Failed to create database engine: {e}")
        engine = None
        SessionLocal = None
else:
    logger.warning("DATABASE_URL not set. Database features will be unavailable.")


# =============================================================================
# DATABASE DEPENDENCY
# =============================================================================

def get_db() -> Generator[Session, None, None]:
    """
    Database session dependency for FastAPI
    
    Yields:
        Database session
    
    Usage:
        @app.get("/users")
        def get_users(db: Session = Depends(get_db)):
            return db.query(User).all()
    """
    if SessionLocal is None:
        raise RuntimeError("Database not configured. Please set DATABASE_URL.")
    
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# =============================================================================
# DATABASE INITIALIZATION
# =============================================================================

def init_db() -> None:
    """
    Initialize database tables
    Creates all tables defined in models
    """
    if engine is None:
        logger.warning("Cannot initialize database: engine not configured")
        return
    
    try:
        # Import all models here to ensure they're registered
        from app.models import user_model, dataset_model, comparison_model  # noqa: F401
        
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise


def close_db() -> None:
    """Close database connections"""
    if engine:
        engine.dispose()
        logger.info("Database connections closed")
