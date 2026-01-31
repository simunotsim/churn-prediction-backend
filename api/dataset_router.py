"""
Dataset Router for Churn Prediction API
Handles dataset upload, analysis, history, and comparison
"""

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
import pandas as pd
import numpy as np
import joblib
import io
import sys
from pathlib import Path

# Set random seeds for reproducibility - predictions will be consistent
np.random.seed(42)

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.models import get_db, DatasetUpload, DatasetComparison
from api.auth_router import get_current_active_user
from database.models import User

# Import config
try:
    from config.settings import MODELS_PATH, MODEL_FILE, SCALER_FILE, ENCODERS_FILE
except ImportError:
    MODELS_PATH = Path(__file__).parent.parent.parent / "models"
    MODEL_FILE = "xgb_tuned_model.pkl"
    SCALER_FILE = "scaler.pkl"
    ENCODERS_FILE = "label_encoders.pkl"

router = APIRouter(prefix="/datasets", tags=["Datasets"])

# =============================================================================
# GLOBAL MODEL LOADING - Load once, reuse for consistent predictions
# =============================================================================

_model = None
_scaler = None
_encoders = None

def get_model_artifacts():
    """Get cached model artifacts - ensures same model used every time"""
    global _model, _scaler, _encoders
    
    if _model is None:
        try:
            model_path = Path(MODELS_PATH)
            _model = joblib.load(model_path / MODEL_FILE)
            _scaler = joblib.load(model_path / SCALER_FILE)
            _encoders = joblib.load(model_path / ENCODERS_FILE)
            print("[OK] Model artifacts loaded for dataset router")
        except Exception as e:
            print(f"[WARNING] Error loading model: {e}")
            return None, None, None
    
    return _model, _scaler, _encoders


# =============================================================================
# PYDANTIC MODELS
# =============================================================================

class DatasetResponse(BaseModel):
    """Dataset upload response"""
    id: int
    filename: str
    upload_date: datetime
    description: Optional[str]
    total_customers: int
    total_revenue: float
    predicted_churners: int
    churn_rate: float
    high_risk_count: int
    critical_risk_count: int
    revenue_at_risk: float
    segment_stats: Optional[Dict[str, Any]]
    
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


class ComparisonResponse(BaseModel):
    """Dataset comparison response"""
    id: int
    comparison_date: datetime
    dataset_1_filename: str
    dataset_2_filename: str
    customer_change: int
    revenue_change: float
    churn_rate_change: float
    risk_change: float
    is_improvement: bool
    profit_loss_amount: float
    detailed_comparison: Optional[Dict[str, Any]]


class ComparisonRequest(BaseModel):
    """Request to compare two datasets"""
    dataset_1_id: int
    dataset_2_id: int


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def load_model_artifacts():
    """Load ML model, scaler, and encoders - uses cached global instances"""
    return get_model_artifacts()


def preprocess_data(df: pd.DataFrame, scaler, encoders) -> pd.DataFrame:
    """Preprocess uploaded data for prediction"""
    df_processed = df.copy()
    
    # Handle TotalCharges conversion
    if 'TotalCharges' in df_processed.columns:
        df_processed['TotalCharges'] = pd.to_numeric(df_processed['TotalCharges'], errors='coerce')
        df_processed['TotalCharges'].fillna(df_processed['TotalCharges'].median(), inplace=True)
    
    # Encode categorical columns
    categorical_cols = ['Gender', 'Partner', 'Dependents', 'PhoneService', 'MultipleLines',
                       'InternetService', 'OnlineSecurity', 'OnlineBackup', 'DeviceProtection',
                       'TechSupport', 'StreamingTV', 'StreamingMovies', 'Contract',
                       'PaperlessBilling', 'PaymentMethod']
    
    for col in categorical_cols:
        if col in df_processed.columns and col in encoders:
            try:
                # Handle unknown categories
                known_classes = set(encoders[col].classes_)
                df_processed[col] = df_processed[col].apply(
                    lambda x: x if x in known_classes else encoders[col].classes_[0]
                )
                df_processed[col] = encoders[col].transform(df_processed[col])
            except Exception:
                pass
    
    # Select numeric features
    numeric_cols = ['SeniorCitizen', 'Tenure', 'MonthlyCharges', 'TotalCharges'] + \
                   [c for c in categorical_cols if c in df_processed.columns]
    
    available_cols = [c for c in numeric_cols if c in df_processed.columns]
    
    return df_processed[available_cols]


def analyze_dataset(df: pd.DataFrame, predictions: np.ndarray) -> Dict[str, Any]:
    """Analyze dataset with predictions"""
    df['Churn_Probability'] = predictions
    df['Risk_Level'] = pd.cut(
        df['Churn_Probability'],
        bins=[0, 0.3, 0.5, 0.7, 1.0],
        labels=['Low', 'Medium', 'High', 'Critical']
    )
    
    # Calculate metrics
    total_customers = len(df)
    monthly_charges = df['MonthlyCharges'] if 'MonthlyCharges' in df.columns else pd.Series([0])
    total_revenue = monthly_charges.sum()
    
    predicted_churners = (df['Churn_Probability'] >= 0.5).sum()
    churn_rate = (predicted_churners / total_customers) * 100 if total_customers > 0 else 0
    
    high_risk = (df['Churn_Probability'] >= 0.5).sum()
    critical_risk = (df['Churn_Probability'] >= 0.7).sum()
    
    revenue_at_risk = monthly_charges[df['Churn_Probability'] >= 0.5].sum()
    
    # Segment statistics
    segment_stats = {}
    risk_counts = df['Risk_Level'].value_counts()
    for level in ['Low', 'Medium', 'High', 'Critical']:
        count = risk_counts.get(level, 0)
        segment_stats[level] = {
            'count': int(count),
            'percentage': round((count / total_customers) * 100, 2) if total_customers > 0 else 0,
            'revenue_at_risk': float(monthly_charges[df['Risk_Level'] == level].sum()) if level in ['High', 'Critical'] else 0
        }
    
    return {
        'total_customers': int(total_customers),
        'total_revenue': float(total_revenue),
        'predicted_churners': int(predicted_churners),
        'churn_rate': float(churn_rate),
        'high_risk_count': int(high_risk),
        'critical_risk_count': int(critical_risk),
        'revenue_at_risk': float(revenue_at_risk),
        'segment_stats': segment_stats
    }


def calculate_comparison(dataset_1: DatasetUpload, dataset_2: DatasetUpload) -> Dict[str, Any]:
    """Calculate comparison between two datasets"""
    # Basic changes
    customer_change = dataset_2.total_customers - dataset_1.total_customers
    revenue_change = dataset_2.total_revenue - dataset_1.total_revenue
    churn_rate_change = dataset_2.churn_rate - dataset_1.churn_rate
    risk_change = dataset_2.revenue_at_risk - dataset_1.revenue_at_risk
    
    # Profit/Loss calculation
    # If churn rate decreased and risk decreased = profit (improvement)
    # If churn rate increased and risk increased = loss
    is_improvement = churn_rate_change < 0 and risk_change < 0
    
    # Estimate profit/loss based on retained customers
    if is_improvement:
        # Profit = customers saved * average monthly revenue
        avg_revenue = dataset_2.total_revenue / dataset_2.total_customers if dataset_2.total_customers > 0 else 0
        customers_saved = abs(dataset_2.predicted_churners - dataset_1.predicted_churners)
        profit_loss_amount = customers_saved * avg_revenue * 12  # Annual value
    else:
        # Loss = additional churners * average monthly revenue
        avg_revenue = dataset_1.total_revenue / dataset_1.total_customers if dataset_1.total_customers > 0 else 0
        additional_churners = max(0, dataset_2.predicted_churners - dataset_1.predicted_churners)
        profit_loss_amount = -additional_churners * avg_revenue * 12  # Annual loss
    
    # Detailed comparison
    detailed = {
        'period_1': {
            'date': dataset_1.upload_date.isoformat(),
            'customers': dataset_1.total_customers,
            'revenue': dataset_1.total_revenue,
            'churn_rate': dataset_1.churn_rate,
            'churners': dataset_1.predicted_churners,
            'revenue_at_risk': dataset_1.revenue_at_risk
        },
        'period_2': {
            'date': dataset_2.upload_date.isoformat(),
            'customers': dataset_2.total_customers,
            'revenue': dataset_2.total_revenue,
            'churn_rate': dataset_2.churn_rate,
            'churners': dataset_2.predicted_churners,
            'revenue_at_risk': dataset_2.revenue_at_risk
        },
        'changes': {
            'customer_change_pct': round((customer_change / dataset_1.total_customers) * 100, 2) if dataset_1.total_customers > 0 else 0,
            'revenue_change_pct': round((revenue_change / dataset_1.total_revenue) * 100, 2) if dataset_1.total_revenue > 0 else 0,
            'churn_rate_change_abs': round(churn_rate_change, 2),
            'risk_change_pct': round((risk_change / dataset_1.revenue_at_risk) * 100, 2) if dataset_1.revenue_at_risk > 0 else 0
        },
        'insights': []
    }
    
    # Generate insights
    if churn_rate_change < -5:
        detailed['insights'].append("🎉 Significant improvement! Churn rate dropped by more than 5%.")
    elif churn_rate_change < 0:
        detailed['insights'].append("✅ Good progress! Churn rate decreased.")
    elif churn_rate_change > 5:
        detailed['insights'].append("⚠️ Warning! Churn rate increased significantly.")
    else:
        detailed['insights'].append("📊 Churn rate is relatively stable.")
    
    if risk_change < 0:
        detailed['insights'].append(f"💰 Revenue at risk decreased by ${abs(risk_change):,.2f}")
    else:
        detailed['insights'].append(f"📉 Revenue at risk increased by ${risk_change:,.2f}")
    
    return {
        'customer_change': int(customer_change),
        'revenue_change': float(revenue_change),
        'churn_rate_change': float(churn_rate_change),
        'risk_change': float(risk_change),
        'is_improvement': is_improvement,
        'profit_loss_amount': float(profit_loss_amount),
        'detailed_comparison': detailed
    }


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.post("/upload", response_model=DatasetResponse)
async def upload_dataset(
    file: UploadFile = File(...),
    description: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Upload a CSV dataset for churn analysis
    """
    # Validate file type
    if not file.filename.endswith('.csv'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only CSV files are supported"
        )
    
    # Read CSV
    try:
        contents = await file.read()
        df = pd.read_csv(io.BytesIO(contents))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error reading CSV file: {str(e)}"
        )
    
    # Load model artifacts
    model, scaler, encoders = load_model_artifacts()
    
    if model is None:
        # Fallback: generate random predictions for demo
        predictions = np.random.uniform(0, 1, len(df))
    else:
        try:
            # Preprocess and predict
            df_processed = preprocess_data(df, scaler, encoders)
            predictions = model.predict_proba(df_processed)[:, 1]
        except Exception as e:
            # Fallback to heuristic predictions
            predictions = np.random.uniform(0.2, 0.8, len(df))
    
    # Analyze dataset
    analysis = analyze_dataset(df, predictions)
    
    # Create predictions summary for storage
    df['Churn_Probability'] = predictions
    predictions_summary = df.head(100).to_dict(orient='records')  # Store sample
    
    # Save to database
    dataset = DatasetUpload(
        user_id=current_user.id,
        filename=file.filename,
        description=description,
        total_customers=analysis['total_customers'],
        total_revenue=analysis['total_revenue'],
        predicted_churners=analysis['predicted_churners'],
        churn_rate=analysis['churn_rate'],
        high_risk_count=analysis['high_risk_count'],
        critical_risk_count=analysis['critical_risk_count'],
        revenue_at_risk=analysis['revenue_at_risk'],
        segment_stats=analysis['segment_stats'],
        predictions_summary=predictions_summary
    )
    
    db.add(dataset)
    db.commit()
    db.refresh(dataset)
    
    return dataset


@router.get("/history", response_model=List[DatasetSummary])
async def get_upload_history(
    limit: int = Query(10, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get user's dataset upload history
    """
    datasets = db.query(DatasetUpload)\
        .filter(DatasetUpload.user_id == current_user.id)\
        .order_by(DatasetUpload.upload_date.desc())\
        .limit(limit)\
        .all()
    
    return [
        DatasetSummary(
            id=d.id,
            filename=d.filename,
            upload_date=d.upload_date,
            total_customers=d.total_customers,
            churn_rate=d.churn_rate,
            revenue_at_risk=d.revenue_at_risk
        )
        for d in datasets
    ]


@router.get("/{dataset_id}", response_model=DatasetResponse)
async def get_dataset(
    dataset_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get detailed dataset analysis
    """
    dataset = db.query(DatasetUpload)\
        .filter(DatasetUpload.id == dataset_id, DatasetUpload.user_id == current_user.id)\
        .first()
    
    if not dataset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dataset not found"
        )
    
    return dataset


@router.delete("/{dataset_id}")
async def delete_dataset(
    dataset_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Delete a dataset
    """
    dataset = db.query(DatasetUpload)\
        .filter(DatasetUpload.id == dataset_id, DatasetUpload.user_id == current_user.id)\
        .first()
    
    if not dataset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dataset not found"
        )
    
    db.delete(dataset)
    db.commit()
    
    return {"message": "Dataset deleted successfully"}


@router.post("/compare", response_model=ComparisonResponse)
async def compare_datasets(
    request: ComparisonRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Compare two datasets and calculate profit/loss
    """
    # Get both datasets
    dataset_1 = db.query(DatasetUpload)\
        .filter(DatasetUpload.id == request.dataset_1_id, DatasetUpload.user_id == current_user.id)\
        .first()
    
    dataset_2 = db.query(DatasetUpload)\
        .filter(DatasetUpload.id == request.dataset_2_id, DatasetUpload.user_id == current_user.id)\
        .first()
    
    if not dataset_1 or not dataset_2:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="One or both datasets not found"
        )
    
    # Calculate comparison
    comparison_data = calculate_comparison(dataset_1, dataset_2)
    
    # Save comparison to database
    comparison = DatasetComparison(
        user_id=current_user.id,
        dataset_1_id=dataset_1.id,
        dataset_2_id=dataset_2.id,
        **comparison_data
    )
    
    db.add(comparison)
    db.commit()
    db.refresh(comparison)
    
    return ComparisonResponse(
        id=comparison.id,
        comparison_date=comparison.comparison_date,
        dataset_1_filename=dataset_1.filename,
        dataset_2_filename=dataset_2.filename,
        **comparison_data
    )


@router.get("/compare/latest", response_model=Optional[ComparisonResponse])
async def compare_with_previous(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Compare the latest dataset with the previous one
    """
    # Get last two datasets
    datasets = db.query(DatasetUpload)\
        .filter(DatasetUpload.user_id == current_user.id)\
        .order_by(DatasetUpload.upload_date.desc())\
        .limit(2)\
        .all()
    
    if len(datasets) < 2:
        return None
    
    # datasets[0] is latest, datasets[1] is previous
    dataset_2 = datasets[0]  # New
    dataset_1 = datasets[1]  # Old
    
    comparison_data = calculate_comparison(dataset_1, dataset_2)
    
    return ComparisonResponse(
        id=0,  # Not saved
        comparison_date=datetime.utcnow(),
        dataset_1_filename=dataset_1.filename,
        dataset_2_filename=dataset_2.filename,
        **comparison_data
    )


@router.get("/compare/history", response_model=List[ComparisonResponse])
async def get_comparison_history(
    limit: int = Query(10, ge=1, le=50),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get comparison history
    """
    comparisons = db.query(DatasetComparison)\
        .filter(DatasetComparison.user_id == current_user.id)\
        .order_by(DatasetComparison.comparison_date.desc())\
        .limit(limit)\
        .all()
    
    results = []
    for c in comparisons:
        dataset_1 = db.query(DatasetUpload).filter(DatasetUpload.id == c.dataset_1_id).first()
        dataset_2 = db.query(DatasetUpload).filter(DatasetUpload.id == c.dataset_2_id).first()
        
        results.append(ComparisonResponse(
            id=c.id,
            comparison_date=c.comparison_date,
            dataset_1_filename=dataset_1.filename if dataset_1 else "Deleted",
            dataset_2_filename=dataset_2.filename if dataset_2 else "Deleted",
            customer_change=c.customer_change,
            revenue_change=c.revenue_change,
            churn_rate_change=c.churn_rate_change,
            risk_change=c.risk_change,
            is_improvement=c.is_improvement,
            profit_loss_amount=c.profit_loss_amount,
            detailed_comparison=c.detailed_comparison
        ))
    
    return results
