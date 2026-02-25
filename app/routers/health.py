"""
Health check and metrics router
System health, readiness, and Prometheus-compatible metrics
"""

import time
from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime

from app.database.session import get_db
from app.ml.model_loader import get_model_loader
from app.core.config import get_settings
from app.core.logging_config import get_logger

settings = get_settings()
logger = get_logger(__name__)

router = APIRouter(tags=["Health"])

# Simple in-memory counters for Prometheus metrics
_request_count = 0
_error_count = 0
_start_time = time.time()


@router.get("/health")
async def health_check():
    """
    GET /health — basic health check
    """
    return {
        "status": "healthy",
        "service": "churn-prediction-api",
        "version": settings.APP_VERSION,
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/health/ready")
async def readiness_check(db: Session = Depends(get_db)):
    """
    Readiness check — verifies database and ML models
    """
    checks = {
        "database": False,
        "ml_models": False,
        "config": True,
    }

    # Check database
    try:
        db.execute(text("SELECT 1"))
        checks["database"] = True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")

    # Check ML models
    try:
        model_loader = get_model_loader()
        if model_loader.is_loaded() or model_loader.load_artifacts():
            checks["ml_models"] = True
    except Exception as e:
        logger.error(f"ML models health check failed: {e}")

    all_healthy = all(checks.values())

    return {
        "status": "ready" if all_healthy else "not_ready",
        "checks": checks,
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/health/live")
async def liveness_check():
    """Liveness check — simple ping"""
    return {
        "status": "alive",
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/metrics", response_class=PlainTextResponse)
async def prometheus_metrics():
    """
    GET /metrics — Prometheus-compatible metrics endpoint

    Exposes:
    - Request latency (uptime proxy)
    - Error rate
    - Job queue size (placeholder)
    """
    uptime = time.time() - _start_time

    metrics = (
        f"# HELP churn_api_uptime_seconds Time since API started\n"
        f"# TYPE churn_api_uptime_seconds gauge\n"
        f"churn_api_uptime_seconds {uptime:.2f}\n"
        f"\n"
        f"# HELP churn_api_requests_total Total requests served (placeholder)\n"
        f"# TYPE churn_api_requests_total counter\n"
        f"churn_api_requests_total {_request_count}\n"
        f"\n"
        f"# HELP churn_api_errors_total Total errors (placeholder)\n"
        f"# TYPE churn_api_errors_total counter\n"
        f"churn_api_errors_total {_error_count}\n"
        f"\n"
        f"# HELP churn_api_info API version info\n"
        f"# TYPE churn_api_info gauge\n"
        f'churn_api_info{{version="{settings.APP_VERSION}"}} 1\n'
    )
    return metrics
