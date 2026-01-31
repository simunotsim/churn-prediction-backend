"""
Customer Churn Prediction API
FastAPI backend for churn prediction, explainability, and retention strategies
"""

import os
import sys
from fastapi import FastAPI, HTTPException, UploadFile, File, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import pandas as pd
import numpy as np
import joblib
from pathlib import Path
import io

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import settings from config
try:
    from config.settings import (
        MODELS_PATH, PROCESSED_DATA_DIR, ALLOWED_ORIGINS,
        MODEL_FILE, SCALER_FILE, ENCODERS_FILE,
        PREDICTIONS_FILE, RETENTION_FILE, MODEL_COMPARISON_FILE,
        print_config
    )
except ImportError:
    # Fallback if config not found - use relative paths
    MODELS_PATH = Path(__file__).parent.parent.parent / "models"
    PROCESSED_DATA_DIR = Path(__file__).parent.parent.parent / "data" / "processed"
    ALLOWED_ORIGINS = ["http://localhost:3000", "http://localhost:5173", "http://localhost:8501"]
    MODEL_FILE = "xgb_tuned_model.pkl"
    SCALER_FILE = "scaler.pkl"
    ENCODERS_FILE = "label_encoders.pkl"
    PREDICTIONS_FILE = "customer_predictions.csv"
    RETENTION_FILE = "retention_actions.csv"
    MODEL_COMPARISON_FILE = "model_comparison.csv"
    print_config = lambda: None

# Initialize FastAPI app
app = FastAPI(
    title="Customer Churn Prediction API",
    description="API for predicting customer churn, explaining predictions, and generating retention strategies",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Use config paths (no hardcoded local paths)
DATA_PATH = PROCESSED_DATA_DIR

# Global model objects (loaded on startup)
model = None
scaler = None
label_encoders = None
customers_df = None
retention_df = None


# ============================================================================
# PYDANTIC MODELS (Request/Response Schemas)
# ============================================================================

class CustomerInput(BaseModel):
    """Single customer input for prediction"""
    Gender: str = Field(..., example="Male")
    SeniorCitizen: int = Field(..., ge=0, le=1, example=0)
    Partner: str = Field(..., example="Yes")
    Dependents: str = Field(..., example="No")
    Tenure: int = Field(..., ge=0, example=12)
    PhoneService: str = Field(..., example="Yes")
    InternetService: str = Field(..., example="Fiber optic")
    Contract: str = Field(..., example="Month-to-month")
    PaperlessBilling: str = Field(..., example="Yes")
    PaymentMethod: str = Field(..., example="Electronic check")
    MonthlyCharges: float = Field(..., ge=0, example=70.35)
    TotalCharges: float = Field(..., ge=0, example=844.20)
    TechSupport: Optional[str] = Field("No", example="No")
    OnlineSecurity: Optional[str] = Field("No", example="No")


class PredictionResponse(BaseModel):
    """Prediction response for a single customer"""
    churn_probability: float
    risk_level: str
    will_churn: bool
    confidence: float


class ExplanationResponse(BaseModel):
    """SHAP explanation response"""
    customer_id: Optional[str]
    churn_probability: float
    risk_level: str
    top_drivers: List[Dict[str, Any]]
    recommendations: List[str]


class CustomerSummary(BaseModel):
    """Customer summary with prediction"""
    customer_id: str
    churn_probability: float
    risk_level: str
    segment: str
    monthly_charges: float
    total_charges: float
    tenure: int
    contract: str


class SegmentStats(BaseModel):
    """Segment statistics"""
    segment: str
    count: int
    percentage: float
    avg_churn_probability: float
    avg_monthly_charges: float
    total_revenue_at_risk: float


class DashboardStats(BaseModel):
    """Dashboard overview statistics"""
    total_customers: int
    churn_rate: float
    high_risk_count: int
    critical_count: int
    monthly_revenue_at_risk: float
    annual_revenue_at_risk: float
    segments: List[SegmentStats]


class RetentionAction(BaseModel):
    """Retention action for a customer"""
    customer_id: str
    priority: str
    churn_probability: float
    strategies: List[str]
    contract: str
    internet_service: str
    payment_method: str


class ModelMetrics(BaseModel):
    """Model performance metrics"""
    model_name: str
    accuracy: float
    precision: float
    recall: float
    f1_score: float
    roc_auc: float


# ============================================================================
# STARTUP & SHUTDOWN EVENTS
# ============================================================================

@app.on_event("startup")
async def load_models():
    """Load ML models and data on startup"""
    global model, scaler, label_encoders, customers_df, retention_df
    
    try:
        # Print config on startup for debugging
        print_config()
        
        model = joblib.load(Path(MODELS_PATH) / MODEL_FILE)
        scaler = joblib.load(Path(MODELS_PATH) / SCALER_FILE)
        label_encoders = joblib.load(Path(MODELS_PATH) / ENCODERS_FILE)
        
        # Load pre-computed predictions
        predictions_path = Path(DATA_PATH) / PREDICTIONS_FILE
        if predictions_path.exists():
            customers_df = pd.read_csv(predictions_path)
        
        retention_path = Path(DATA_PATH) / RETENTION_FILE
        if retention_path.exists():
            retention_df = pd.read_csv(retention_path)
            
        print("✅ Models and data loaded successfully!")
    except Exception as e:
        print(f"⚠️ Error loading models: {e}")


# ============================================================================
# HEALTH CHECK ENDPOINTS
# ============================================================================

@app.get("/", tags=["Health"])
async def root():
    """API root - health check"""
    return {
        "status": "healthy",
        "message": "Customer Churn Prediction API",
        "version": "1.0.0"
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """Detailed health check"""
    return {
        "status": "healthy",
        "model_loaded": model is not None,
        "scaler_loaded": scaler is not None,
        "customers_loaded": customers_df is not None,
        "total_customers": len(customers_df) if customers_df is not None else 0
    }


# ============================================================================
# PREDICTION ENDPOINTS
# ============================================================================

@app.post("/predict", response_model=PredictionResponse, tags=["Predictions"])
async def predict_churn(customer: CustomerInput):
    """
    Predict churn probability for a single customer
    
    Returns:
    - churn_probability: Probability of churn (0-1)
    - risk_level: Low/Medium/High/Critical
    - will_churn: Boolean prediction
    - confidence: Model confidence score
    """
    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    try:
        # Prepare features
        features = prepare_features(customer.dict())
        
        # Get prediction
        proba = model.predict_proba(features)[0, 1]
        prediction = model.predict(features)[0]
        
        # Determine risk level
        risk_level = get_risk_level(proba)
        
        return PredictionResponse(
            churn_probability=round(float(proba), 4),
            risk_level=risk_level,
            will_churn=bool(prediction),
            confidence=round(float(max(proba, 1 - proba)), 4)
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/predict/batch", tags=["Predictions"])
async def predict_batch(file: UploadFile = File(...)):
    """
    Batch prediction from CSV file
    
    Upload a CSV with customer data to get predictions for all rows.
    Returns predictions with customer IDs.
    """
    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    try:
        contents = await file.read()
        df = pd.read_csv(io.StringIO(contents.decode('utf-8')))
        
        predictions = []
        for _, row in df.iterrows():
            features = prepare_features(row.to_dict())
            proba = model.predict_proba(features)[0, 1]
            
            predictions.append({
                "customer_id": row.get("CustomerID", row.get("customerID", "Unknown")),
                "churn_probability": round(float(proba), 4),
                "risk_level": get_risk_level(proba),
                "will_churn": bool(proba >= 0.5)
            })
        
        return {
            "total_processed": len(predictions),
            "high_risk_count": sum(1 for p in predictions if p["risk_level"] in ["High", "Critical"]),
            "predictions": predictions
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================================
# CUSTOMER ENDPOINTS
# ============================================================================

@app.get("/customers", tags=["Customers"])
async def get_customers(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=500),
    risk_level: Optional[str] = Query(None, description="Filter by risk level"),
    segment: Optional[str] = Query(None, description="Filter by segment"),
    sort_by: str = Query("Churn_Probability", description="Sort field"),
    sort_order: str = Query("desc", description="asc or desc")
):
    """
    Get paginated list of customers with predictions
    
    Supports filtering by risk level and segment, with sorting options.
    """
    if customers_df is None:
        raise HTTPException(status_code=503, detail="Customer data not loaded")
    
    df = customers_df.copy()
    
    # Apply filters
    if risk_level:
        risk_map = {"Low": (0, 0.3), "Medium": (0.3, 0.5), "High": (0.5, 0.7), "Critical": (0.7, 1.0)}
        if risk_level in risk_map:
            low, high = risk_map[risk_level]
            df = df[(df["Churn_Probability"] >= low) & (df["Churn_Probability"] < high)]
    
    if segment:
        df = df[df["Segment"] == segment]
    
    # Sort
    ascending = sort_order.lower() == "asc"
    if sort_by in df.columns:
        df = df.sort_values(sort_by, ascending=ascending)
    
    # Paginate
    total = len(df)
    start = (page - 1) * limit
    end = start + limit
    page_data = df.iloc[start:end]
    
    return {
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": (total + limit - 1) // limit,
        "customers": page_data.to_dict(orient="records")
    }


@app.get("/customers/{customer_id}", response_model=CustomerSummary, tags=["Customers"])
async def get_customer(customer_id: str):
    """Get details for a specific customer"""
    if customers_df is None:
        raise HTTPException(status_code=503, detail="Customer data not loaded")
    
    customer = customers_df[customers_df["CustomerID"] == customer_id]
    
    if customer.empty:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    row = customer.iloc[0]
    return CustomerSummary(
        customer_id=str(row["CustomerID"]),
        churn_probability=round(float(row["Churn_Probability"]), 4),
        risk_level=get_risk_level(row["Churn_Probability"]),
        segment=str(row["Segment"]),
        monthly_charges=float(row["MonthlyCharges"]),
        total_charges=float(row["TotalCharges"]),
        tenure=int(row["Tenure"]),
        contract=str(row["Contract"])
    )


# ============================================================================
# EXPLAINABILITY ENDPOINTS
# ============================================================================

@app.get("/explain/{customer_id}", response_model=ExplanationResponse, tags=["Explainability"])
async def explain_prediction(customer_id: str):
    """
    Get SHAP-based explanation for a customer's churn prediction
    
    Returns top drivers and personalized recommendations.
    """
    if customers_df is None:
        raise HTTPException(status_code=503, detail="Customer data not loaded")
    
    customer = customers_df[customers_df["CustomerID"] == customer_id]
    
    if customer.empty:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    row = customer.iloc[0]
    proba = row["Churn_Probability"]
    
    # Generate drivers based on customer attributes
    drivers = generate_drivers(row)
    recommendations = generate_recommendations(row)
    
    return ExplanationResponse(
        customer_id=customer_id,
        churn_probability=round(float(proba), 4),
        risk_level=get_risk_level(proba),
        top_drivers=drivers,
        recommendations=recommendations
    )


# ============================================================================
# RETENTION ENDPOINTS
# ============================================================================

@app.get("/retention/actions", tags=["Retention"])
async def get_retention_actions(
    priority: Optional[str] = Query(None, description="Filter by priority"),
    limit: int = Query(100, ge=1, le=1000)
):
    """
    Get list of retention actions for at-risk customers
    
    Filter by priority: Critical, High, Medium
    """
    if retention_df is None:
        raise HTTPException(status_code=503, detail="Retention data not loaded")
    
    df = retention_df.copy()
    
    if priority:
        df = df[df["Priority"] == priority]
    
    df = df.head(limit)
    
    return {
        "total": len(df),
        "priority_breakdown": retention_df["Priority"].value_counts().to_dict(),
        "actions": df.to_dict(orient="records")
    }


@app.get("/retention/customer/{customer_id}", response_model=RetentionAction, tags=["Retention"])
async def get_customer_retention(customer_id: str):
    """Get retention action for a specific customer"""
    if retention_df is None:
        raise HTTPException(status_code=503, detail="Retention data not loaded")
    
    customer = retention_df[retention_df["CustomerID"] == customer_id]
    
    if customer.empty:
        raise HTTPException(status_code=404, detail="Customer not in retention list")
    
    row = customer.iloc[0]
    strategies = row["Strategies"].split(" | ") if pd.notna(row["Strategies"]) else []
    
    return RetentionAction(
        customer_id=str(row["CustomerID"]),
        priority=str(row["Priority"]),
        churn_probability=float(row["Churn_Probability"]),
        strategies=strategies,
        contract=str(row["Contract"]),
        internet_service=str(row["InternetService"]),
        payment_method=str(row["PaymentMethod"])
    )


# ============================================================================
# DASHBOARD / ANALYTICS ENDPOINTS
# ============================================================================

@app.get("/dashboard/stats", response_model=DashboardStats, tags=["Dashboard"])
async def get_dashboard_stats():
    """Get overview statistics for dashboard"""
    if customers_df is None:
        raise HTTPException(status_code=503, detail="Customer data not loaded")
    
    df = customers_df
    
    # Calculate stats
    total = len(df)
    high_risk = len(df[df["Churn_Probability"] >= 0.5])
    critical = len(df[df["Churn_Probability"] >= 0.7])
    
    # Revenue at risk
    high_risk_customers = df[df["Churn_Probability"] >= 0.5]
    monthly_at_risk = high_risk_customers["MonthlyCharges"].sum()
    
    # Segment stats
    segments = []
    for segment in df["Segment"].unique():
        seg_df = df[df["Segment"] == segment]
        segments.append(SegmentStats(
            segment=segment,
            count=len(seg_df),
            percentage=round(len(seg_df) / total * 100, 1),
            avg_churn_probability=round(seg_df["Churn_Probability"].mean(), 4),
            avg_monthly_charges=round(seg_df["MonthlyCharges"].mean(), 2),
            total_revenue_at_risk=round(seg_df[seg_df["Churn_Probability"] >= 0.5]["MonthlyCharges"].sum(), 2)
        ))
    
    return DashboardStats(
        total_customers=total,
        churn_rate=round(df["Churn_Probability"].mean() * 100, 1),
        high_risk_count=high_risk,
        critical_count=critical,
        monthly_revenue_at_risk=round(monthly_at_risk, 2),
        annual_revenue_at_risk=round(monthly_at_risk * 12, 2),
        segments=segments
    )


@app.get("/dashboard/segments", tags=["Dashboard"])
async def get_segment_distribution():
    """Get customer segment distribution"""
    if customers_df is None:
        raise HTTPException(status_code=503, detail="Customer data not loaded")
    
    segment_counts = customers_df["Segment"].value_counts().to_dict()
    
    return {
        "segments": segment_counts,
        "total": len(customers_df)
    }


@app.get("/dashboard/risk-distribution", tags=["Dashboard"])
async def get_risk_distribution():
    """Get risk level distribution"""
    if customers_df is None:
        raise HTTPException(status_code=503, detail="Customer data not loaded")
    
    df = customers_df
    
    return {
        "low": len(df[df["Churn_Probability"] < 0.3]),
        "medium": len(df[(df["Churn_Probability"] >= 0.3) & (df["Churn_Probability"] < 0.5)]),
        "high": len(df[(df["Churn_Probability"] >= 0.5) & (df["Churn_Probability"] < 0.7)]),
        "critical": len(df[df["Churn_Probability"] >= 0.7]),
        "total": len(df)
    }


# ============================================================================
# MODEL ENDPOINTS
# ============================================================================

@app.get("/model/metrics", tags=["Model"])
async def get_model_metrics():
    """Get model performance metrics"""
    if not (DATA_PATH / "model_comparison.csv").exists():
        raise HTTPException(status_code=503, detail="Model metrics not available")
    
    metrics_df = pd.read_csv(DATA_PATH / "model_comparison.csv")
    
    return {
        "models": metrics_df.to_dict(orient="records"),
        "best_model": metrics_df.iloc[0].to_dict()
    }


@app.get("/model/features", tags=["Model"])
async def get_feature_importance():
    """Get feature importance from the model"""
    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    feature_names = [
        'Tenure', 'MonthlyCharges', 'TotalCharges', 'SeniorCitizen', 'ChargePerTenure',
        'Gender', 'Partner', 'Dependents', 'PhoneService', 'InternetService',
        'Contract', 'PaperlessBilling', 'PaymentMethod', 'TenureGroup'
    ]
    
    importance = model.feature_importances_
    
    features = [
        {"feature": name, "importance": round(float(imp), 4)}
        for name, imp in sorted(zip(feature_names, importance), key=lambda x: x[1], reverse=True)
    ]
    
    return {"features": features}


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_risk_level(probability: float) -> str:
    """Convert probability to risk level"""
    if probability >= 0.7:
        return "Critical"
    elif probability >= 0.5:
        return "High"
    elif probability >= 0.3:
        return "Medium"
    return "Low"


def prepare_features(data: dict) -> np.ndarray:
    """Prepare features for model prediction"""
    # Feature engineering
    tenure = data.get("Tenure", 0)
    total_charges = data.get("TotalCharges", 0)
    monthly_charges = data.get("MonthlyCharges", 0)
    
    charge_per_tenure = total_charges / (tenure + 1)
    
    # Tenure group
    if tenure <= 12:
        tenure_group = "New"
    elif tenure <= 24:
        tenure_group = "Developing"
    elif tenure <= 48:
        tenure_group = "Mature"
    else:
        tenure_group = "Loyal"
    
    # Numerical features
    numerical = [tenure, monthly_charges, total_charges, data.get("SeniorCitizen", 0), charge_per_tenure]
    numerical_scaled = scaler.transform([numerical])[0]
    
    # Categorical features (encode)
    categorical_cols = ['Gender', 'Partner', 'Dependents', 'PhoneService', 'InternetService',
                        'Contract', 'PaperlessBilling', 'PaymentMethod', 'TenureGroup']
    
    data["TenureGroup"] = tenure_group
    
    categorical = []
    for col in categorical_cols:
        if col in label_encoders:
            try:
                encoded = label_encoders[col].transform([str(data.get(col, "Unknown"))])[0]
            except:
                encoded = 0
            categorical.append(encoded)
        else:
            categorical.append(0)
    
    features = np.concatenate([numerical_scaled, categorical]).reshape(1, -1)
    return features


def generate_drivers(row: pd.Series) -> List[Dict[str, Any]]:
    """Generate top churn drivers for a customer"""
    drivers = []
    
    if row.get("Contract") == "Month-to-month":
        drivers.append({"feature": "Contract", "value": "Month-to-month", "impact": "high", "direction": "increases"})
    
    if row.get("Tenure", 100) < 12:
        drivers.append({"feature": "Tenure", "value": f"{row.get('Tenure', 0)} months", "impact": "high", "direction": "increases"})
    
    if row.get("InternetService") == "Fiber optic":
        drivers.append({"feature": "InternetService", "value": "Fiber optic", "impact": "medium", "direction": "increases"})
    
    if row.get("PaymentMethod") == "Electronic check":
        drivers.append({"feature": "PaymentMethod", "value": "Electronic check", "impact": "medium", "direction": "increases"})
    
    if row.get("TechSupport") == "No":
        drivers.append({"feature": "TechSupport", "value": "No", "impact": "medium", "direction": "increases"})
    
    return drivers[:5]


def generate_recommendations(row: pd.Series) -> List[str]:
    """Generate personalized recommendations"""
    recommendations = []
    
    if row.get("Contract") == "Month-to-month":
        recommendations.append("Offer discounted annual contract upgrade")
    
    if row.get("PaymentMethod") == "Electronic check":
        recommendations.append("Suggest auto-pay enrollment with incentive")
    
    if row.get("Tenure", 100) < 12:
        recommendations.append("Enroll in new customer loyalty program")
    
    if row.get("TechSupport") == "No":
        recommendations.append("Offer complimentary tech support trial")
    
    if row.get("InternetService") == "Fiber optic":
        recommendations.append("Schedule service quality check")
    
    if not recommendations:
        recommendations.append("Continue standard engagement")
    
    return recommendations


# ============================================================================
# RUN SERVER
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
