"""
Celery application for background tasks
Handles asynchronous ML predictions and dataset processing
"""

from celery import Celery
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import get_settings
from app.core.logging_config import setup_logging, get_logger

settings = get_settings()
setup_logging()
logger = get_logger(__name__)

# Create Celery app
celery_app = Celery(
    "churn_prediction_worker",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["worker.tasks"]
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
)

logger.info("Celery app configured successfully")

if __name__ == "__main__":
    celery_app.start()
