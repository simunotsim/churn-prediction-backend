"""
Celery tasks for background processing
Async tasks for ML predictions and dataset analysis

Worker task must:
- Read CSV
- Validate required columns
- Preprocess features
- Run model.predict_proba
- Calculate: churn_rate, high_risk_count, revenue_at_risk
- Store results in DB
- Update status = completed
- On error: Log error, set status = failed
"""

import pandas as pd
import numpy as np
from typing import Dict, Any
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from worker.celery_app import celery_app
from app.ml.model_loader import get_model_loader
from app.ml.preprocess import DataPreprocessor
from app.core.config import get_settings
from app.core.logging_config import get_logger
from app.database.session import SessionLocal
from app.repositories.dataset_repository import DatasetRepository

settings = get_settings()
logger = get_logger(__name__)


@celery_app.task(bind=True, name="worker.tasks.process_dataset_async")
def process_dataset_async(self, dataset_id: int, data_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process dataset asynchronously
    
    Args:
        dataset_id: Database ID of the dataset
        data_dict: Dictionary representation of the dataset
    
    Returns:
        Analysis results
    """
    logger.info(f"Task {self.request.id}: Processing dataset {dataset_id}")
    
    db = SessionLocal()
    dataset_repo = DatasetRepository()
    
    try:
        # Update status to processing
        dataset_repo.update_status(db, dataset_id, "processing")
        
        # Convert dict to DataFrame
        df = pd.DataFrame(data_dict)
        
        # Load model artifacts
        model_loader = get_model_loader()
        model, scaler, encoders = model_loader.load_artifacts()
        preprocessor = DataPreprocessor(scaler, encoders)
        
        # Preprocess data
        X = preprocessor.preprocess_batch(df)
        
        # Predict churn probabilities
        churn_probs = model.predict_proba(X)[:, 1]
        churn_preds = (churn_probs >= settings.CHURN_THRESHOLD).astype(int)
        
        # Calculate metrics
        total_customers = len(df)
        predicted_churners = int(churn_preds.sum())
        churn_rate = float(predicted_churners / total_customers)
        
        # Risk levels
        high_risk_count = int((churn_probs >= settings.HIGH_RISK_THRESHOLD).sum())
        critical_risk_count = int((churn_probs >= settings.CRITICAL_RISK_THRESHOLD).sum())
        
        # Revenue calculations
        if 'MonthlyCharges' in df.columns:
            total_revenue = float(df['MonthlyCharges'].sum())
            revenue_at_risk = float(df.loc[churn_preds == 1, 'MonthlyCharges'].sum())
        else:
            total_revenue = 0.0
            revenue_at_risk = 0.0
        
        # Segment analysis
        segment_stats = _calculate_segment_stats(df, churn_preds, churn_probs)
        
        # Update dataset with results
        dataset_repo.update_analysis_results(
            db,
            dataset_id,
            total_customers=total_customers,
            total_revenue=total_revenue,
            predicted_churners=predicted_churners,
            churn_rate=churn_rate,
            high_risk_count=high_risk_count,
            critical_risk_count=critical_risk_count,
            revenue_at_risk=revenue_at_risk,
            segment_stats=segment_stats
        )
        
        logger.info(f"Task {self.request.id}: Dataset {dataset_id} processed successfully")
        
        return {
            "status": "completed",
            "dataset_id": dataset_id,
            "total_customers": total_customers,
            "churn_rate": churn_rate
        }
        
    except Exception as e:
        logger.error(f"Task {self.request.id}: Failed to process dataset {dataset_id}: {e}")
        dataset_repo.update_status(db, dataset_id, "failed", str(e))
        raise
    
    finally:
        db.close()


@celery_app.task(bind=True, name="worker.tasks.batch_predict_async")
def batch_predict_async(self, customers_data: list) -> Dict[str, Any]:
    """
    Perform batch predictions asynchronously
    
    Args:
        customers_data: List of customer dictionaries
    
    Returns:
        Prediction results
    """
    logger.info(f"Task {self.request.id}: Batch predicting {len(customers_data)} customers")
    
    try:
        # Convert to DataFrame
        df = pd.DataFrame(customers_data)
        
        # Load model artifacts
        model_loader = get_model_loader()
        model, scaler, encoders = model_loader.load_artifacts()
        preprocessor = DataPreprocessor(scaler, encoders)
        
        # Preprocess
        X = preprocessor.preprocess_batch(df)
        
        # Predict
        churn_probs = model.predict_proba(X)[:, 1]
        churn_preds = (churn_probs >= settings.CHURN_THRESHOLD).astype(int)
        
        # Format results
        predictions = []
        for i, (prob, pred) in enumerate(zip(churn_probs, churn_preds)):
            predictions.append({
                "customer_id": f"customer_{i+1}",
                "churn_probability": float(prob),
                "churn_prediction": int(pred),
                "risk_level": _get_risk_level(prob)
            })
        
        summary = {
            "total": len(predictions),
            "predicted_churners": int(churn_preds.sum()),
            "churn_rate": float(churn_preds.mean()),
            "avg_churn_probability": float(churn_probs.mean())
        }
        
        logger.info(f"Task {self.request.id}: Batch prediction completed")
        
        return {
            "status": "completed",
            "predictions": predictions,
            "summary": summary
        }
        
    except Exception as e:
        logger.error(f"Task {self.request.id}: Batch prediction failed: {e}")
        raise


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _get_risk_level(churn_prob: float) -> str:
    """Determine risk level from probability"""
    if churn_prob >= settings.CRITICAL_RISK_THRESHOLD:
        return "Critical"
    elif churn_prob >= settings.HIGH_RISK_THRESHOLD:
        return "High"
    elif churn_prob >= settings.CHURN_THRESHOLD:
        return "Medium"
    else:
        return "Low"


def _calculate_segment_stats(
    df: pd.DataFrame, 
    churn_preds: np.ndarray,
    churn_probs: np.ndarray
) -> dict:
    """Calculate churn statistics by segments"""
    stats = {}
    
    # By contract type
    if 'Contract' in df.columns:
        stats['by_contract'] = {}
        for contract in df['Contract'].unique():
            mask = df['Contract'] == contract
            stats['by_contract'][str(contract)] = {
                'total': int(mask.sum()),
                'churners': int(churn_preds[mask].sum()),
                'churn_rate': float(churn_preds[mask].mean())
            }
    
    # By tenure groups
    if 'tenure' in df.columns:
        stats['by_tenure'] = {}
        tenure_bins = [0, 12, 24, 48, 100]
        tenure_labels = ['0-12', '12-24', '24-48', '48+']
        df_copy = df.copy()
        df_copy['tenure_group'] = pd.cut(df_copy['tenure'], bins=tenure_bins, labels=tenure_labels)
        
        for group in tenure_labels:
            mask = df_copy['tenure_group'] == group
            if mask.sum() > 0:
                stats['by_tenure'][group] = {
                    'total': int(mask.sum()),
                    'churners': int(churn_preds[mask].sum()),
                    'churn_rate': float(churn_preds[mask].mean())
                }
    
    return stats
