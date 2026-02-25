"""
Comparison service
Business logic for dataset comparisons
Must NOT directly manipulate SQLAlchemy session or contain raw SQL
"""

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.repositories.dataset_repository import DatasetRepository
from app.repositories.comparison_repository import ComparisonRepository
from app.schemas.comparison_schema import CompareRequest, CompareResponse
from app.core.logging_config import get_logger

logger = get_logger(__name__)


class ComparisonService:
    """Service for dataset comparison operations"""

    def __init__(self, db: Session):
        self.db = db
        self.dataset_repo = DatasetRepository()
        self.comparison_repo = ComparisonRepository()

    def compare_datasets(
        self, user_id: int, request: CompareRequest
    ) -> CompareResponse:
        """
        Compare two datasets per API contract.

        POST /dataset/compare
        Request: {"dataset_1_id": 1, "dataset_2_id": 2}
        Response: {"churn_rate_change": 0.05, "is_improvement": true}
        """
        ds1 = self.dataset_repo.get_by_id(self.db, request.dataset_1_id)
        ds2 = self.dataset_repo.get_by_id(self.db, request.dataset_2_id)

        if not ds1 or not ds2:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="One or both datasets not found",
            )

        # Authorization check
        if ds1.user_id != user_id or ds2.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access one or both datasets",
            )

        # Both must be completed
        if ds1.status != "completed" or ds2.status != "completed":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Both datasets must be in completed status",
            )

        # Calculate comparison metrics
        churn_rate_change = round((ds2.churn_rate or 0) - (ds1.churn_rate or 0), 6)
        revenue_change = round((ds2.revenue_at_risk or 0) - (ds1.revenue_at_risk or 0), 2)
        is_improvement = churn_rate_change < 0  # Lower churn = improvement

        # Store comparison in DB
        self.comparison_repo.create(
            self.db,
            user_id=user_id,
            dataset_1_id=request.dataset_1_id,
            dataset_2_id=request.dataset_2_id,
            churn_rate_change=churn_rate_change,
            revenue_change=revenue_change,
            is_improvement=is_improvement,
        )

        logger.info(
            f"Comparison created: ds1={request.dataset_1_id}, ds2={request.dataset_2_id}, "
            f"change={churn_rate_change}, improvement={is_improvement}"
        )

        return CompareResponse(
            churn_rate_change=churn_rate_change,
            is_improvement=is_improvement,
        )
