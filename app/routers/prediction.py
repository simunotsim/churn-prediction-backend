"""
Prediction router
HTTP endpoints for churn predictions and retention strategies
"""

from fastapi import APIRouter, Depends, HTTPException

from app.services.prediction_service import PredictionService
from app.schemas.prediction_schema import (
    CustomerInput, PredictionResult,
    BatchCustomerInput, BatchPredictionResult,
    RetentionStrategy
)
from app.schemas.auth_schema import UserResponse
from app.routers.auth import get_current_active_user
from app.core.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/predictions", tags=["Predictions"])


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.post("/predict", response_model=PredictionResult)
async def predict_single_customer(
    customer: CustomerInput,
    current_user: UserResponse = Depends(get_current_active_user)
):
    """
    Predict churn probability for a single customer
    
    Returns:
    - Churn probability (0-1)
    - Risk level (Low, Medium, High, Critical)
    - Top risk factors
    - Recommended retention actions
    """
    logger.info(f"User {current_user.email} requesting single prediction")
    
    prediction_service = PredictionService()
    return prediction_service.predict_single(customer)


@router.post("/predict/batch", response_model=BatchPredictionResult)
async def predict_batch_customers(
    batch: BatchCustomerInput,
    current_user: UserResponse = Depends(get_current_active_user)
):
    """
    Predict churn for multiple customers in batch
    
    Returns predictions for all customers with summary statistics
    """
    logger.info(f"User {current_user.email} requesting batch prediction for {len(batch.customers)} customers")
    
    prediction_service = PredictionService()
    return prediction_service.predict_batch(batch)


@router.post("/retention-strategy", response_model=RetentionStrategy)
async def get_retention_strategy(
    customer: CustomerInput,
    current_user: UserResponse = Depends(get_current_active_user)
):
    """
    Generate personalized retention strategy for a customer
    
    Returns:
    - Detailed retention actions with priorities
    - Expected impact and cost estimates
    - Revenue saving projections
    """
    logger.info(f"User {current_user.email} requesting retention strategy")
    
    prediction_service = PredictionService()
    return prediction_service.generate_retention_strategy(customer)


@router.get("/health")
async def health_check():
    """Health check endpoint for prediction service"""
    return {"status": "healthy", "service": "predictions"}
