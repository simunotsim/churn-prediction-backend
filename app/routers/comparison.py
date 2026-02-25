"""
Comparison router
Dedicated router for dataset comparisons per directory structure contract
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.services.comparison_service import ComparisonService
from app.schemas.comparison_schema import CompareRequest, CompareResponse
from app.schemas.auth_schema import UserResponse
from app.routers.auth import get_current_active_user

router = APIRouter(prefix="/comparison", tags=["Comparisons"])


@router.post("/compare", response_model=CompareResponse)
async def compare_datasets(
    request: CompareRequest,
    current_user: UserResponse = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Compare two datasets

    Request: {"dataset_1_id": 1, "dataset_2_id": 2}
    Response: {"churn_rate_change": 0.05, "is_improvement": true}
    """
    comparison_service = ComparisonService(db)
    return comparison_service.compare_datasets(
        user_id=current_user.id,
        request=request,
    )
