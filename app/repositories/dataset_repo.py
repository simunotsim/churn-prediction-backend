"""
Backward-compatible re-export from dataset_repository.py
"""

from app.repositories.dataset_repository import DatasetRepository

__all__ = ["DatasetRepository"]


# Below kept only for import compatibility. New code should import from dataset_repository.py.
class _Stub:
    pass
    
    @staticmethod
    def get_by_id(db: Session, dataset_id: int) -> Optional[Dataset]:
        """Get dataset by ID"""
        return db.query(Dataset).filter(Dataset.id == dataset_id).first()
    
    @staticmethod
    def get_by_user(db: Session, user_id: int, skip: int = 0, limit: int = 100) -> List[Dataset]:
        """Get all datasets for a user with pagination"""
        return (
            db.query(Dataset)
            .filter(Dataset.user_id == user_id)
            .order_by(Dataset.upload_date.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    @staticmethod
    def get_recent(db: Session, user_id: int, limit: int = 10) -> List[Dataset]:
        """Get recent datasets for a user"""
        return (
            db.query(Dataset)
            .filter(Dataset.user_id == user_id)
            .order_by(Dataset.upload_date.desc())
            .limit(limit)
            .all()
        )
    
    @staticmethod
    def count_by_user(db: Session, user_id: int) -> int:
        """Count total datasets for a user"""
        return db.query(Dataset).filter(Dataset.user_id == user_id).count()
    
    @staticmethod
    def create(db: Session, user_id: int, dataset_data: DatasetCreate) -> Dataset:
        """Create a new dataset record"""
        db_dataset = Dataset(
            user_id=user_id,
            filename=dataset_data.filename,
            description=dataset_data.description,
            status="pending"
        )
        
        db.add(db_dataset)
        db.commit()
        db.refresh(db_dataset)
        return db_dataset
    
    @staticmethod
    def update(db: Session, dataset_id: int, dataset_data: DatasetUpdate) -> Optional[Dataset]:
        """Update dataset metadata"""
        db_dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
        
        if not db_dataset:
            return None
        
        update_data = dataset_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_dataset, field, value)
        
        db.commit()
        db.refresh(db_dataset)
        return db_dataset
    
    @staticmethod
    def update_analysis_results(
        db: Session,
        dataset_id: int,
        total_customers: int,
        total_revenue: float,
        predicted_churners: int,
        churn_rate: float,
        high_risk_count: int,
        critical_risk_count: int,
        revenue_at_risk: float,
        segment_stats: dict = None
    ) -> Optional[Dataset]:
        """Update dataset with analysis results"""
        db_dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
        
        if not db_dataset:
            return None
        
        db_dataset.total_customers = total_customers
        db_dataset.total_revenue = total_revenue
        db_dataset.predicted_churners = predicted_churners
        db_dataset.churn_rate = churn_rate
        db_dataset.high_risk_count = high_risk_count
        db_dataset.critical_risk_count = critical_risk_count
        db_dataset.revenue_at_risk = revenue_at_risk
        db_dataset.segment_stats = segment_stats
        db_dataset.processed_date = datetime.utcnow()
        db_dataset.status = "completed"
        
        db.commit()
        db.refresh(db_dataset)
        return db_dataset
    
    @staticmethod
    def update_status(db: Session, dataset_id: int, status: str, error_message: str = None) -> Optional[Dataset]:
        """Update dataset processing status"""
        db_dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
        
        if not db_dataset:
            return None
        
        db_dataset.status = status
        if error_message:
            db_dataset.error_message = error_message
        
        db.commit()
        db.refresh(db_dataset)
        return db_dataset
    
    @staticmethod
    def delete(db: Session, dataset_id: int) -> bool:
        """Delete a dataset"""
        db_dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
        
        if not db_dataset:
            return False
        
        db.delete(db_dataset)
        db.commit()
        return True
    
    @staticmethod
    def get_by_status(db: Session, status: str, limit: int = 100) -> List[Dataset]:
        """Get datasets by status (for processing queue)"""
        return (
            db.query(Dataset)
            .filter(Dataset.status == status)
            .order_by(Dataset.upload_date.asc())
            .limit(limit)
            .all()
        )
