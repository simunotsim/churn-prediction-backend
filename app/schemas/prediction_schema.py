"""
Prediction schemas for request/response validation
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator


# =============================================================================
# CUSTOMER INPUT SCHEMAS
# =============================================================================

class CustomerInput(BaseModel):
    """Single customer input for prediction"""
    Gender: str = Field(..., example="Male")
    SeniorCitizen: int = Field(..., ge=0, le=1, example=0)
    Partner: str = Field(..., example="Yes")
    Dependents: str = Field(..., example="No")
    tenure: int = Field(..., ge=0, example=12)
    PhoneService: str = Field(..., example="Yes")
    MultipleLines: str = Field(..., example="No")
    InternetService: str = Field(..., example="Fiber optic")
    OnlineSecurity: str = Field(..., example="No")
    OnlineBackup: str = Field(..., example="No")
    DeviceProtection: str = Field(..., example="No")
    TechSupport: str = Field(..., example="No")
    StreamingTV: str = Field(..., example="No")
    StreamingMovies: str = Field(..., example="No")
    Contract: str = Field(..., example="Month-to-month")
    PaperlessBilling: str = Field(..., example="Yes")
    PaymentMethod: str = Field(..., example="Electronic check")
    MonthlyCharges: float = Field(..., gt=0, example=70.35)
    TotalCharges: float = Field(..., ge=0, example=843.50)
    
    @validator("Gender")
    def validate_gender(cls, v):
        if v not in ["Male", "Female"]:
            raise ValueError("Gender must be 'Male' or 'Female'")
        return v
    
    @validator("Partner", "Dependents", "PhoneService", "PaperlessBilling")
    def validate_yes_no(cls, v):
        if v not in ["Yes", "No"]:
            raise ValueError(f"Must be 'Yes' or 'No'")
        return v
    
    @validator("Contract")
    def validate_contract(cls, v):
        if v not in ["Month-to-month", "One year", "Two year"]:
            raise ValueError("Invalid contract type")
        return v


class BatchCustomerInput(BaseModel):
    """Multiple customers for batch prediction"""
    customers: List[CustomerInput]


# =============================================================================
# PREDICTION RESPONSE SCHEMAS
# =============================================================================

class PredictionResult(BaseModel):
    """Single prediction result"""
    customer_id: Optional[str] = None
    churn_probability: float = Field(..., ge=0, le=1)
    churn_prediction: int = Field(..., ge=0, le=1)
    risk_level: str  # Low, Medium, High, Critical
    confidence: float = Field(..., ge=0, le=1)
    
    # Feature importance for explainability
    top_risk_factors: Optional[List[Dict[str, Any]]] = None
    
    # Retention recommendations
    recommended_actions: Optional[List[str]] = None
    retention_score: Optional[float] = None


class BatchPredictionResult(BaseModel):
    """Batch prediction results"""
    predictions: List[PredictionResult]
    summary: Dict[str, Any]
    total_customers: int
    high_risk_count: int
    predicted_churners: int


# =============================================================================
# EXPLAINABILITY SCHEMAS
# =============================================================================

class FeatureContribution(BaseModel):
    """Feature contribution to prediction"""
    feature: str
    value: Any
    contribution: float
    importance: float


class ExplainabilityResult(BaseModel):
    """Detailed explanation of a prediction"""
    customer_input: Dict[str, Any]
    churn_probability: float
    risk_level: str
    
    # Feature contributions
    feature_contributions: List[FeatureContribution]
    
    # SHAP values (if available)
    shap_values: Optional[Dict[str, float]] = None
    
    # Natural language explanation
    explanation: str


# =============================================================================
# RETENTION SCHEMAS
# =============================================================================

class RetentionAction(BaseModel):
    """Recommended retention action"""
    action_type: str
    priority: str  # High, Medium, Low
    description: str
    expected_impact: Optional[float] = None
    estimated_cost: Optional[float] = None


class RetentionStrategy(BaseModel):
    """Complete retention strategy for a customer"""
    customer_id: Optional[str] = None
    risk_level: str
    churn_probability: float
    
    # Recommended actions
    actions: List[RetentionAction]
    
    # Expected outcomes
    estimated_retention_lift: Optional[float] = None
    estimated_revenue_saved: Optional[float] = None
    
    # Priority ranking
    action_priority: int = Field(..., ge=1)
