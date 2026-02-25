"""
Comparison schemas for request/response validation
Per API contract: POST /dataset/compare
"""

from typing import Optional
from pydantic import BaseModel


class CompareRequest(BaseModel):
    """Comparison request per API contract"""
    dataset_1_id: int
    dataset_2_id: int


class CompareResponse(BaseModel):
    """Comparison response per API contract"""
    churn_rate_change: float
    is_improvement: bool


class ComparisonDetail(BaseModel):
    """Detailed comparison response (extended)"""
    id: int
    dataset_1_id: int
    dataset_2_id: int
    churn_rate_change: Optional[float] = None
    revenue_change: Optional[float] = None
    is_improvement: Optional[bool] = None

    class Config:
        from_attributes = True
