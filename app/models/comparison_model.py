"""
Comparison model for dataset comparisons
Matches architecture contract: user_id, dataset_1_id, dataset_2_id,
churn_rate_change, revenue_change, is_improvement
"""

from datetime import datetime
from sqlalchemy import Column, Integer, Float, DateTime, Boolean, ForeignKey

from app.database.base import Base


class Comparison(Base):
    """Dataset comparison model for tracking changes between two datasets"""

    __tablename__ = "dataset_comparisons"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    dataset_1_id = Column(Integer, ForeignKey("dataset_uploads.id"), nullable=False)
    dataset_2_id = Column(Integer, ForeignKey("dataset_uploads.id"), nullable=False)

    # Comparison results
    churn_rate_change = Column(Float, nullable=True)
    revenue_change = Column(Float, nullable=True)
    is_improvement = Column(Boolean, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return (
            f"<Comparison(id={self.id}, ds1={self.dataset_1_id}, "
            f"ds2={self.dataset_2_id}, improvement={self.is_improvement})>"
        )
