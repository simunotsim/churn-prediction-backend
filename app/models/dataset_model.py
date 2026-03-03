"""
Dataset model for uploaded customer data and analysis results
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship

from app.database.base import Base


class Dataset(Base):
    """Dataset upload with churn analysis results"""

    __tablename__ = "dataset_uploads"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Dataset metadata
    filename = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # Dataset statistics
    total_customers = Column(Integer, default=0)
    total_revenue = Column(Float, default=0.0)

    # Churn analysis results
    churn_rate = Column(Float, default=0.0)
    revenue_at_risk = Column(Float, default=0.0)
    predicted_churners = Column(Integer, default=0)
    high_risk_count = Column(Integer, default=0)
    critical_risk_count = Column(Integer, default=0)
    segment_stats = Column(JSON, nullable=True)
    predictions_summary = Column(JSON, nullable=True)

    # Processing status: processing / completed / failed
    status = Column(String(50), default="processing")
    error_message = Column(Text, nullable=True)

    # Timestamps
    upload_date = Column(DateTime, default=datetime.utcnow)
    processed_date = Column(DateTime, nullable=True)

    # Relationships
    owner = relationship("User", back_populates="datasets")

    def __repr__(self):
        return f"<Dataset(id={self.id}, filename='{self.filename}', status='{self.status}')>"
