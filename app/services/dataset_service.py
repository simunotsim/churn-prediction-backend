"""
Dataset service
Business logic for dataset management and analysis
Dispatches heavy ML work to Celery worker
Must NOT directly manipulate SQLAlchemy session or contain raw SQL
"""

import pandas as pd
import uuid
from typing import Optional
from fastapi import HTTPException, status, UploadFile
from sqlalchemy.orm import Session
import io

from app.repositories.dataset_repository import DatasetRepository
from app.schemas.dataset_schema import (
    DatasetResponse, DatasetSummary, DatasetList,
    DatasetUploadResponse, DatasetStatusResponse,
)
from app.core.config import get_settings
from app.core.logging_config import get_logger

settings = get_settings()
logger = get_logger(__name__)


class DatasetService:
    """Service for dataset operations and churn analysis"""

    def __init__(self, db: Session):
        self.db = db
        self.dataset_repo = DatasetRepository()

    async def upload_dataset(
        self,
        file: UploadFile,
        user_id: int,
        description: Optional[str] = None,
    ) -> DatasetUploadResponse:
        """
        Upload dataset and dispatch to Celery worker for async processing.

        Returns:
            {"job_id": "uuid", "status": "processing"} per API contract
        """
        # Validate file type
        if not file.filename.endswith(".csv"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only CSV files are supported",
            )

        # Validate file size (10MB max)
        contents = await file.read()
        size_mb = len(contents) / (1024 * 1024)
        if size_mb > settings.MAX_CSV_SIZE_MB:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File exceeds {settings.MAX_CSV_SIZE_MB}MB limit",
            )

        # Validate row count
        try:
            df = pd.read_csv(io.BytesIO(contents))
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid CSV file: {e}",
            )

        if len(df) > settings.MAX_ROWS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File exceeds {settings.MAX_ROWS} row limit",
            )

        # Create dataset record with status=processing
        dataset = self.dataset_repo.create(
            self.db,
            user_id=user_id,
            filename=file.filename,
            description=description,
        )

        # Dispatch to Celery worker
        try:
            from worker.tasks import process_dataset_async

            job = process_dataset_async.delay(dataset.id, df.to_dict(orient="list"))
            job_id = job.id
        except Exception as e:
            logger.warning(f"Celery dispatch failed, processing synchronously: {e}")
            # Fallback: process inline (for dev environments without Redis)
            job_id = str(uuid.uuid4())
            try:
                self._process_inline(dataset.id, df)
            except Exception as inner_e:
                self.dataset_repo.update_status(self.db, dataset.id, "failed", str(inner_e))

        logger.info(f"User {user_id} uploaded dataset {dataset.id}, job_id={job_id}")
        return DatasetUploadResponse(job_id=job_id, status="processing")

    def get_dataset_status(self, dataset_id: int, user_id: int) -> DatasetStatusResponse:
        """
        Get processing status of a dataset

        Returns:
            {"status": "processing"|"completed"|"failed"}
        """
        dataset = self.dataset_repo.get_by_id(self.db, dataset_id)
        if not dataset:
            raise HTTPException(status_code=404, detail="Dataset not found")
        if dataset.user_id != user_id:
            raise HTTPException(status_code=403, detail="Not authorized")
        return DatasetStatusResponse(status=dataset.status)

    def get_user_datasets(
        self,
        user_id: int,
        page: int = 1,
        page_size: int = 10,
    ) -> DatasetList:
        """Get paginated list of user's datasets"""
        skip = (page - 1) * page_size
        datasets = self.dataset_repo.get_by_user(self.db, user_id, skip, page_size)
        total = self.dataset_repo.count_by_user(self.db, user_id)

        summaries = [DatasetSummary.model_validate(ds) for ds in datasets]

        return DatasetList(
            datasets=summaries,
            total=total,
            page=page,
            page_size=page_size,
        )

    def get_dataset(self, dataset_id: int, user_id: int) -> DatasetResponse:
        """Get single dataset by ID"""
        dataset = self.dataset_repo.get_by_id(self.db, dataset_id)

        if not dataset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Dataset not found",
            )
        if dataset.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this dataset",
            )
        return DatasetResponse.model_validate(dataset)

    def delete_dataset(self, dataset_id: int, user_id: int) -> bool:
        """Delete a dataset"""
        dataset = self.dataset_repo.get_by_id(self.db, dataset_id)

        if not dataset:
            raise HTTPException(status_code=404, detail="Dataset not found")
        if dataset.user_id != user_id:
            raise HTTPException(status_code=403, detail="Not authorized to delete this dataset")

        return self.dataset_repo.delete(self.db, dataset_id)

    # ------------------------------------------------------------------
    # Inline fallback (for environments without Celery/Redis)
    # ------------------------------------------------------------------

    def _process_inline(self, dataset_id: int, df: pd.DataFrame) -> None:
        """Process dataset synchronously (fallback when Celery unavailable)"""
        import numpy as np
        from app.ml.model_loader import get_model_loader
        from app.ml.preprocess import DataPreprocessor

        self.dataset_repo.update_status(self.db, dataset_id, "processing")

        model_loader = get_model_loader()
        model, scaler, encoders = model_loader.load_artifacts()
        preprocessor = DataPreprocessor(scaler, encoders)

        X = preprocessor.preprocess_batch(df)
        churn_probs = model.predict_proba(X)[:, 1]
        churn_preds = (churn_probs >= settings.CHURN_THRESHOLD).astype(int)

        total_customers = len(df)
        predicted_churners = int(churn_preds.sum())
        churn_rate = float(predicted_churners / total_customers) if total_customers else 0.0
        high_risk_count = int((churn_probs >= settings.HIGH_RISK_THRESHOLD).sum())
        critical_risk_count = int((churn_probs >= settings.CRITICAL_RISK_THRESHOLD).sum())

        if "MonthlyCharges" in df.columns:
            total_revenue = float(df["MonthlyCharges"].sum())
            revenue_at_risk = float(df.loc[churn_preds == 1, "MonthlyCharges"].sum())
        else:
            total_revenue = 0.0
            revenue_at_risk = 0.0

        self.dataset_repo.update_analysis_results(
            self.db,
            dataset_id,
            total_customers=total_customers,
            total_revenue=total_revenue,
            predicted_churners=predicted_churners,
            churn_rate=churn_rate,
            high_risk_count=high_risk_count,
            critical_risk_count=critical_risk_count,
            revenue_at_risk=revenue_at_risk,
        )
