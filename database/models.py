"""
Database Models for Churn Prediction Application
SQLAlchemy models for users, datasets, and analysis results
Connects to MySQL (AWS RDS via MySQL Workbench)
"""

from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, ForeignKey, Boolean, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import os
from pathlib import Path

# Load .env file
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    pass  # python-dotenv not installed

# =============================================================================
# DATABASE CONFIGURATION - MySQL (AWS RDS)
# =============================================================================

# Get database URL from environment (REQUIRED)
# Format: mysql+pymysql://user:password@rds-endpoint:3306/database_name
DATABASE_URL = os.getenv("DATABASE_URL")

# Check if database is configured
if DATABASE_URL:
    # MySQL with connection pooling for RDS
    engine = create_engine(
        DATABASE_URL,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,  # Check connection before use
        pool_recycle=300     # Recycle connections every 5 minutes
    )
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
else:
    # No database configured - will be set up later with RDS
    engine = None
    SessionLocal = None
    print("[INFO] DATABASE_URL not set. Configure AWS RDS connection in .env file.")

Base = declarative_base()


# =============================================================================
# USER MODEL
# =============================================================================

class User(Base):
    """User account for authentication"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    company = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)
    
    # Relationship to datasets
    datasets = relationship("DatasetUpload", back_populates="owner", cascade="all, delete-orphan")


# =============================================================================
# DATASET UPLOAD MODEL
# =============================================================================

class DatasetUpload(Base):
    """Uploaded dataset with analysis results"""
    __tablename__ = "dataset_uploads"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Dataset metadata
    filename = Column(String(255), nullable=False)
    upload_date = Column(DateTime, default=datetime.utcnow)
    description = Column(Text, nullable=True)
    
    # Dataset statistics
    total_customers = Column(Integer, default=0)
    total_revenue = Column(Float, default=0.0)
    
    # Churn analysis results
    predicted_churners = Column(Integer, default=0)
    churn_rate = Column(Float, default=0.0)
    high_risk_count = Column(Integer, default=0)
    critical_risk_count = Column(Integer, default=0)
    revenue_at_risk = Column(Float, default=0.0)
    
    # Segment breakdown (stored as JSON)
    segment_stats = Column(JSON, nullable=True)
    
    # Raw predictions (stored as JSON for comparison)
    predictions_summary = Column(JSON, nullable=True)
    
    # Relationship to user
    owner = relationship("User", back_populates="datasets")


# =============================================================================
# COMPARISON RECORD MODEL
# =============================================================================

class DatasetComparison(Base):
    """Comparison between two datasets"""
    __tablename__ = "dataset_comparisons"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Dataset references
    dataset_1_id = Column(Integer, ForeignKey("dataset_uploads.id"), nullable=False)
    dataset_2_id = Column(Integer, ForeignKey("dataset_uploads.id"), nullable=False)
    
    # Comparison date
    comparison_date = Column(DateTime, default=datetime.utcnow)
    
    # Comparison metrics
    customer_change = Column(Integer, default=0)  # +/- customers
    revenue_change = Column(Float, default=0.0)  # +/- revenue
    churn_rate_change = Column(Float, default=0.0)  # +/- percentage points
    risk_change = Column(Float, default=0.0)  # +/- revenue at risk
    
    # Profit/Loss indicator
    is_improvement = Column(Boolean, default=False)
    profit_loss_amount = Column(Float, default=0.0)
    
    # Detailed analysis (JSON)
    detailed_comparison = Column(JSON, nullable=True)
    
    # Relationships
    dataset_1 = relationship("DatasetUpload", foreign_keys=[dataset_1_id])
    dataset_2 = relationship("DatasetUpload", foreign_keys=[dataset_2_id])


# =============================================================================
# DATABASE INITIALIZATION
# =============================================================================

def init_db():
    """Create all tables in MySQL database"""
    if engine is None:
        print("[WARNING] Database not configured. Set DATABASE_URL in .env")
        print("         Format: mysql+pymysql://user:password@rds-endpoint:3306/database")
        return False
    
    Base.metadata.create_all(bind=engine)
    print("[OK] Database tables created successfully!")
    return True


def get_db():
    """Get database session"""
    if SessionLocal is None:
        raise Exception("Database not configured. Set DATABASE_URL environment variable.")
    
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Initialize on import
if __name__ == "__main__":
    init_db()
