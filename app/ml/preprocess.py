"""
Data preprocessing for ML predictions
Handles feature engineering and data transformation
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, List

from app.core.logging import get_logger

logger = get_logger(__name__)


class DataPreprocessor:
    """Data preprocessing for churn prediction"""
    
    def __init__(self, scaler, encoders):
        """
        Initialize preprocessor with fitted scaler and encoders
        
        Args:
            scaler: Fitted StandardScaler or similar
            encoders: Dict of fitted LabelEncoders
        """
        self.scaler = scaler
        self.encoders = encoders
    
    def preprocess_single(self, customer_data: Dict[str, Any]) -> np.ndarray:
        """
        Preprocess a single customer record
        
        Args:
            customer_data: Dictionary of customer features
        
        Returns:
            Preprocessed feature array ready for prediction
        """
        # Convert to DataFrame for easier processing
        df = pd.DataFrame([customer_data])
        return self.preprocess_batch(df)
    
    def preprocess_batch(self, df: pd.DataFrame) -> np.ndarray:
        """
        Preprocess a batch of customer records
        
        Args:
            df: DataFrame with customer features
        
        Returns:
            Preprocessed feature array ready for prediction
        """
        try:
            # Make a copy to avoid modifying original
            df_processed = df.copy()
            
            # Encode categorical variables
            categorical_cols = [
                'Gender', 'Partner', 'Dependents', 'PhoneService',
                'MultipleLines', 'InternetService', 'OnlineSecurity',
                'OnlineBackup', 'DeviceProtection', 'TechSupport',
                'StreamingTV', 'StreamingMovies', 'Contract',
                'PaperlessBilling', 'PaymentMethod'
            ]
            
            for col in categorical_cols:
                if col in df_processed.columns and col in self.encoders:
                    # Handle unseen labels
                    encoder = self.encoders[col]
                    df_processed[col] = df_processed[col].apply(
                        lambda x: encoder.transform([x])[0] 
                        if x in encoder.classes_ 
                        else encoder.transform([encoder.classes_[0]])[0]
                    )
            
            # Ensure numeric types
            numeric_cols = ['tenure', 'MonthlyCharges', 'TotalCharges', 'SeniorCitizen']
            for col in numeric_cols:
                if col in df_processed.columns:
                    df_processed[col] = pd.to_numeric(df_processed[col], errors='coerce').fillna(0)
            
            # Define feature order (must match training)
            expected_features = [
                'Gender', 'SeniorCitizen', 'Partner', 'Dependents', 'tenure',
                'PhoneService', 'MultipleLines', 'InternetService', 'OnlineSecurity',
                'OnlineBackup', 'DeviceProtection', 'TechSupport', 'StreamingTV',
                'StreamingMovies', 'Contract', 'PaperlessBilling', 'PaymentMethod',
                'MonthlyCharges', 'TotalCharges'
            ]
            
            # Reorder columns
            df_processed = df_processed[expected_features]
            
            # Scale features
            X_scaled = self.scaler.transform(df_processed)
            
            return X_scaled
            
        except Exception as e:
            logger.error(f"Preprocessing error: {e}")
            raise ValueError(f"Failed to preprocess data: {e}")
    
    def validate_input(self, customer_data: Dict[str, Any]) -> List[str]:
        """
        Validate customer input data
        
        Args:
            customer_data: Dictionary of customer features
        
        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        
        # Required fields
        required_fields = [
            'Gender', 'SeniorCitizen', 'Partner', 'Dependents', 'tenure',
            'PhoneService', 'MultipleLines', 'InternetService', 'OnlineSecurity',
            'OnlineBackup', 'DeviceProtection', 'TechSupport', 'StreamingTV',
            'StreamingMovies', 'Contract', 'PaperlessBilling', 'PaymentMethod',
            'MonthlyCharges', 'TotalCharges'
        ]
        
        for field in required_fields:
            if field not in customer_data:
                errors.append(f"Missing required field: {field}")
        
        # Value ranges
        if 'SeniorCitizen' in customer_data:
            if customer_data['SeniorCitizen'] not in [0, 1]:
                errors.append("SeniorCitizen must be 0 or 1")
        
        if 'tenure' in customer_data:
            if customer_data['tenure'] < 0:
                errors.append("tenure must be >= 0")
        
        if 'MonthlyCharges' in customer_data:
            if customer_data['MonthlyCharges'] <= 0:
                errors.append("MonthlyCharges must be > 0")
        
        if 'TotalCharges' in customer_data:
            if customer_data['TotalCharges'] < 0:
                errors.append("TotalCharges must be >= 0")
        
        return errors
    
    def create_feature_importance_map(
        self, 
        customer_data: Dict[str, Any], 
        feature_importances: np.ndarray
    ) -> List[Dict[str, Any]]:
        """
        Create feature importance map for explainability
        
        Args:
            customer_data: Original customer data
            feature_importances: Feature importances from model
        
        Returns:
            List of features with their importance scores
        """
        features = [
            'Gender', 'SeniorCitizen', 'Partner', 'Dependents', 'tenure',
            'PhoneService', 'MultipleLines', 'InternetService', 'OnlineSecurity',
            'OnlineBackup', 'DeviceProtection', 'TechSupport', 'StreamingTV',
            'StreamingMovies', 'Contract', 'PaperlessBilling', 'PaymentMethod',
            'MonthlyCharges', 'TotalCharges'
        ]
        
        importance_list = []
        for feature, importance in zip(features, feature_importances):
            importance_list.append({
                "feature": feature,
                "value": customer_data.get(feature),
                "importance": float(importance)
            })
        
        # Sort by importance
        importance_list.sort(key=lambda x: abs(x["importance"]), reverse=True)
        
        return importance_list
