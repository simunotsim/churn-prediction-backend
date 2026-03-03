"""
Dataset schemas for request/response validation
Per API contract specification
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


# =============================================================================
# DATASET UPLOAD SCHEMAS (API CONTRACT)
# =============================================================================

class DatasetUploadResponse(BaseModel):
    """Response after uploading a dataset (async processing)"""
    job_id: str
    status: str = "processing"


class DatasetStatusResponse(BaseModel):
    """Response for GET /dataset/status/{job_id}"""
    status: str  # "processing" | "completed" | "failed"


# =============================================================================
# DATASET DETAIL SCHEMAS
# =============================================================================

class DatasetBase(BaseModel):
    """Base dataset fields"""
    filename: str
    description: Optional[str] = None


class DatasetCreate(DatasetBase):
    """Dataset upload internal creation"""
    pass


class DatasetUpdate(BaseModel):
    """Dataset update request"""
    description: Optional[str] = None
    status: Optional[str] = None


class DatasetResponse(BaseModel):
    """Full dataset response with analysis results"""
    id: int
    filename: str
    upload_date: datetime
    processed_date: Optional[datetime] = None
    description: Optional[str] = None

    # Statistics
    total_customers: int
    total_revenue: float

    # Churn analysis
    predicted_churners: int
    churn_rate: float
    high_risk_count: int
    critical_risk_count: int
    revenue_at_risk: float

    # Segments
    segment_stats: Optional[Dict[str, Any]] = None

    # Status
    status: str
    error_message: Optional[str] = None

    class Config:
        from_attributes = True


class DatasetSummary(BaseModel):
    """Brief dataset summary for list view"""
    id: int
    filename: str
    upload_date: datetime
    total_customers: int
    churn_rate: float
    revenue_at_risk: float
    status: str

    class Config:
        from_attributes = True


class DatasetList(BaseModel):
    """List of datasets with pagination"""
    datasets: List[DatasetSummary]
    total: int
    page: int
    page_size: int
