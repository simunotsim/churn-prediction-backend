"""
Prediction service
Business logic for churn predictions and explainability
"""

import numpy as np
from typing import List, Dict, Any
from fastapi import HTTPException, status

from app.schemas.prediction_schema import (
    CustomerInput, PredictionResult, BatchPredictionResult,
    BatchCustomerInput, RetentionAction, RetentionStrategy
)
from app.ml.model_loader import get_model_loader
from app.ml.preprocess import DataPreprocessor
from app.core.config import get_settings
from app.core.logging_config import get_logger

settings = get_settings()
logger = get_logger(__name__)


class PredictionService:
    """Service for churn prediction operations"""
    
    def __init__(self):
        self.model_loader = get_model_loader()
    
    def predict_single(self, customer: CustomerInput) -> PredictionResult:
        """
        Predict churn for a single customer
        
        Args:
            customer: Customer data
        
        Returns:
            Prediction result with risk level and recommendations
        """
        try:
            # Load model artifacts
            model, scaler, encoders = self.model_loader.load_artifacts()
            preprocessor = DataPreprocessor(scaler, encoders)
            
            # Validate input
            errors = preprocessor.validate_input(customer.dict())
            if errors:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid input: {', '.join(errors)}"
                )
            
            # Preprocess
            X = preprocessor.preprocess_single(customer.dict())
            
            # Predict
            churn_prob = float(model.predict_proba(X)[0, 1])
            churn_pred = int(churn_prob >= settings.CHURN_THRESHOLD)
            
            # Determine risk level
            risk_level = self._get_risk_level(churn_prob)
            
            # Get feature importance
            if hasattr(model, 'feature_importances_'):
                feature_importances = model.feature_importances_
                top_factors = preprocessor.create_feature_importance_map(
                    customer.dict(), 
                    feature_importances
                )[:5]  # Top 5 factors
            else:
                top_factors = None
            
            # Generate recommendations
            recommendations = self._generate_recommendations(
                churn_prob, 
                customer.dict()
            )
            
            return PredictionResult(
                churn_probability=churn_prob,
                churn_prediction=churn_pred,
                risk_level=risk_level,
                confidence=abs(churn_prob - 0.5) * 2,  # 0 to 1 scale
                top_risk_factors=top_factors,
                recommended_actions=recommendations,
                retention_score=1.0 - churn_prob
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Prediction failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Prediction failed: {str(e)}"
            )
    
    def predict_batch(self, batch: BatchCustomerInput) -> BatchPredictionResult:
        """
        Predict churn for multiple customers
        
        Args:
            batch: Batch of customer data
        
        Returns:
            Batch prediction results with summary
        """
        try:
            predictions = []
            
            for i, customer in enumerate(batch.customers):
                result = self.predict_single(customer)
                result.customer_id = f"customer_{i+1}"
                predictions.append(result)
            
            # Calculate summary
            total = len(predictions)
            predicted_churners = sum(1 for p in predictions if p.churn_prediction == 1)
            high_risk = sum(
                1 for p in predictions 
                if p.churn_probability >= settings.HIGH_RISK_THRESHOLD
            )
            
            summary = {
                "total_customers": total,
                "predicted_churners": predicted_churners,
                "churn_rate": predicted_churners / total if total > 0 else 0,
                "high_risk_count": high_risk,
                "avg_churn_probability": float(np.mean([p.churn_probability for p in predictions]))
            }
            
            return BatchPredictionResult(
                predictions=predictions,
                summary=summary,
                total_customers=total,
                high_risk_count=high_risk,
                predicted_churners=predicted_churners
            )
            
        except Exception as e:
            logger.error(f"Batch prediction failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Batch prediction failed: {str(e)}"
            )
    
    def generate_retention_strategy(self, customer: CustomerInput) -> RetentionStrategy:
        """
        Generate personalized retention strategy
        
        Args:
            customer: Customer data
        
        Returns:
            Retention strategy with recommended actions
        """
        # Get prediction
        prediction = self.predict_single(customer)
        
        # Generate detailed retention actions
        actions = self._generate_detailed_actions(
            prediction.churn_probability,
            customer.dict()
        )
        
        # Calculate expected impact
        retention_lift = min(0.3, prediction.churn_probability * 0.5)
        revenue_saved = customer.MonthlyCharges * 12 * retention_lift
        
        return RetentionStrategy(
            risk_level=prediction.risk_level,
            churn_probability=prediction.churn_probability,
            actions=actions,
            estimated_retention_lift=retention_lift,
            estimated_revenue_saved=revenue_saved,
            action_priority=1 if prediction.risk_level == "Critical" else 2
        )
    
    def _get_risk_level(self, churn_prob: float) -> str:
        """Determine risk level from probability"""
        if churn_prob >= settings.CRITICAL_RISK_THRESHOLD:
            return "Critical"
        elif churn_prob >= settings.HIGH_RISK_THRESHOLD:
            return "High"
        elif churn_prob >= settings.CHURN_THRESHOLD:
            return "Medium"
        else:
            return "Low"
    
    def _generate_recommendations(self, churn_prob: float, customer_data: dict) -> List[str]:
        """Generate simple retention recommendations"""
        recommendations = []
        
        if churn_prob >= 0.7:
            recommendations.append("Urgent: Schedule immediate retention call")
            recommendations.append("Offer premium service upgrade at 50% discount")
        
        if customer_data.get('Contract') == 'Month-to-month':
            recommendations.append("Incentivize longer contract term")
        
        if customer_data.get('tenure', 0) < 12:
            recommendations.append("Provide new customer onboarding support")
        
        if customer_data.get('MonthlyCharges', 0) > 70:
            recommendations.append("Review pricing and offer loyalty discount")
        
        if customer_data.get('TechSupport') == 'No':
            recommendations.append("Offer complimentary tech support trial")
        
        return recommendations[:5]  # Top 5 recommendations
    
    def _generate_detailed_actions(
        self, 
        churn_prob: float, 
        customer_data: dict
    ) -> List[RetentionAction]:
        """Generate detailed retention actions"""
        actions = []
        
        if churn_prob >= 0.8:
            actions.append(RetentionAction(
                action_type="immediate_outreach",
                priority="High",
                description="Schedule urgent retention call within 24 hours",
                expected_impact=0.3,
                estimated_cost=50.0
            ))
        
        if customer_data.get('Contract') == 'Month-to-month':
            actions.append(RetentionAction(
                action_type="contract_upgrade",
                priority="High",
                description="Offer 20% discount for 1-year contract",
                expected_impact=0.25,
                estimated_cost=customer_data.get('MonthlyCharges', 70) * 12 * 0.2
            ))
        
        if customer_data.get('tenure', 0) < 12:
            actions.append(RetentionAction(
                action_type="onboarding_support",
                priority="Medium",
                description="Provide personalized onboarding and product training",
                expected_impact=0.15,
                estimated_cost=30.0
            ))
        
        if customer_data.get('TechSupport') == 'No':
            actions.append(RetentionAction(
                action_type="service_upgrade",
                priority="Medium",
                description="Offer 3-month free tech support",
                expected_impact=0.12,
                estimated_cost=45.0
            ))
        
        return actions
