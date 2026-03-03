"""
Comparison repository for database operations
Handles all comparison-related database queries
No business logic - only DB access
"""

from typing import Optional, List
from sqlalchemy.orm import Session

from app.models.comparison_model import Comparison


class ComparisonRepository:
    """Repository for comparison database operations"""

    @staticmethod
    def create(
        db: Session,
        user_id: int,
        dataset_1_id: int,
        dataset_2_id: int,
        churn_rate_change: float,
        revenue_change: float,
        is_improvement: bool,
    ) -> Comparison:
        """Create a new comparison record"""
        db_comparison = Comparison(
            user_id=user_id,
            dataset_1_id=dataset_1_id,
            dataset_2_id=dataset_2_id,
            churn_rate_change=churn_rate_change,
            revenue_change=revenue_change,
            is_improvement=is_improvement,
        )
        db.add(db_comparison)
        db.commit()
        db.refresh(db_comparison)
        return db_comparison

    @staticmethod
    def get_by_id(db: Session, comparison_id: int) -> Optional[Comparison]:
        """Get comparison by ID"""
        return db.query(Comparison).filter(Comparison.id == comparison_id).first()

    @staticmethod
    def get_by_user(db: Session, user_id: int, limit: int = 100) -> List[Comparison]:
        """Get all comparisons for a user"""
        return (
            db.query(Comparison)
            .filter(Comparison.user_id == user_id)
            .order_by(Comparison.comparison_date.desc())
            .limit(limit)
            .all()
        )
