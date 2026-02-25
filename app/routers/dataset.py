"""
Dataset router
HTTP endpoints for dataset upload, status, management, and comparison
No DB logic, no ML logic — calls service layer only
"""

from fastapi import APIRouter, Depends, UploadFile, File, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.database.session import get_db
from app.services.dataset_service import DatasetService
from app.services.comparison_service import ComparisonService
from app.schemas.dataset_schema import (
    DatasetResponse,
    DatasetList,
    DatasetUploadResponse,
    DatasetStatusResponse,
)
from app.schemas.comparison_schema import CompareRequest, CompareResponse
from app.schemas.auth_schema import UserResponse
from app.routers.auth import get_current_active_user
from app.core.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/dataset", tags=["Datasets"])


# =============================================================================
# ENDPOINTS (per API contract)
# =============================================================================


@router.post("/upload", response_model=DatasetUploadResponse, status_code=201)
async def upload_dataset(
    file: UploadFile = File(...),
    description: Optional[str] = None,
    current_user: UserResponse = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    POST /dataset/upload
    Request: CSV file (multipart)
    Response: {"job_id": "uuid", "status": "processing"}
    """
    logger.info(f"User {current_user.email} uploading dataset: {file.filename}")

    dataset_service = DatasetService(db)
    return await dataset_service.upload_dataset(
        file=file,
        user_id=current_user.id,
        description=description,
    )


@router.get("/status/{dataset_id}", response_model=DatasetStatusResponse)
async def get_dataset_status(
    dataset_id: int,
    current_user: UserResponse = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    GET /dataset/status/{job_id}
    Response: {"status": "processing" | "completed" | "failed"}
    """
    dataset_service = DatasetService(db)
    return dataset_service.get_dataset_status(
        dataset_id=dataset_id,
        user_id=current_user.id,
    )


@router.post("/compare", response_model=CompareResponse)
async def compare_datasets(
    request: CompareRequest,
    current_user: UserResponse = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    POST /dataset/compare
    Request: {"dataset_1_id": 1, "dataset_2_id": 2}
    Response: {"churn_rate_change": 0.05, "is_improvement": true}
    """
    comparison_service = ComparisonService(db)
    return comparison_service.compare_datasets(
        user_id=current_user.id,
        request=request,
    )


# =============================================================================
# ADDITIONAL DATASET CRUD
# =============================================================================


@router.get("/", response_model=DatasetList)
async def list_datasets(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    current_user: UserResponse = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get paginated list of user's datasets"""
    dataset_service = DatasetService(db)
    return dataset_service.get_user_datasets(
        user_id=current_user.id,
        page=page,
        page_size=page_size,
    )


@router.get("/{dataset_id}", response_model=DatasetResponse)
async def get_dataset(
    dataset_id: int,
    current_user: UserResponse = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get detailed information about a specific dataset"""
    dataset_service = DatasetService(db)
    return dataset_service.get_dataset(
        dataset_id=dataset_id,
        user_id=current_user.id,
    )


@router.delete("/{dataset_id}")
async def delete_dataset(
    dataset_id: int,
    current_user: UserResponse = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Delete a dataset"""
    dataset_service = DatasetService(db)
    success = dataset_service.delete_dataset(
        dataset_id=dataset_id,
        user_id=current_user.id,
    )
    if success:
        return {"message": "Dataset deleted successfully"}
    return {"message": "Failed to delete dataset"}
