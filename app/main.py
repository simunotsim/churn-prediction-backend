"""
Main FastAPI Application
Production-ready churn prediction API with clean architecture
"""

import time
from collections import defaultdict
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.logging_config import setup_logging, get_logger
from app.database.session import init_db, close_db

# Conditionally import ML modules (only available in worker container)
try:
    from app.ml.model_loader import get_model_loader
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False
    get_model_loader = None

# Import routers
from app.routers import auth, dataset, comparison, prediction, health

# Initialize settings and logging
settings = get_settings()
setup_logging()
logger = get_logger(__name__)

# Simple in-memory rate limiting store: {ip: [timestamps]}
_rate_limit_store: dict = defaultdict(list)


# =============================================================================
# APPLICATION LIFESPAN
# =============================================================================


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events — startup and shutdown"""
    # Startup
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"Environment: {settings.ENV}")

    # Initialize database
    try:
        if settings.DATABASE_URL:
            init_db()
            logger.info("Database initialized successfully")
        else:
            logger.warning("DATABASE_URL not set - running without database")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        if settings.ENV == "production":
            raise

    # Preload ML models (only if ML libraries available - worker container)
    if ML_AVAILABLE and get_model_loader is not None:
        try:
            model_loader = get_model_loader()
            model_loader.load_artifacts()
            logger.info("ML models preloaded successfully")
        except Exception as e:
            logger.warning(f"ML model preloading failed: {e}")
            logger.warning("Models will be loaded on first request")
    else:
        logger.info("ML libraries not available - API-only mode (ML delegated to worker)")

    logger.info("Application startup complete")

    yield

    # Shutdown
    logger.info("Shutting down application")
    close_db()
    logger.info("Application shutdown complete")


# =============================================================================
# CREATE APPLICATION
# =============================================================================


def create_app() -> FastAPI:
    """Create and configure FastAPI application"""
    is_debug = settings.ENV != "production"

    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="Production-ready API for customer churn prediction, explainability, and retention strategies",
        docs_url="/docs" if is_debug else None,
        redoc_url="/redoc" if is_debug else None,
        lifespan=lifespan,
    )

    # ======================================================================
    # MIDDLEWARE
    # ======================================================================

    # CORS — restricted in production per spec
    if settings.ALLOWED_ORIGINS == ["*"]:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=False,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        logger.warning("CORS configured to allow all origins - not recommended for production")
    else:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.ALLOWED_ORIGINS,
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            allow_headers=["Authorization", "Content-Type"],
        )
        logger.info(f"CORS configured for origins: {settings.ALLOWED_ORIGINS}")

    # GZip compression for responses > 1KB
    app.add_middleware(GZipMiddleware, minimum_size=1000)

    # Trusted host middleware for production
    if not is_debug:
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=["*"],  # Configure specific hosts in production
        )

    # ======================================================================
    # RATE LIMITING MIDDLEWARE (100 req/min per spec)
    # ======================================================================

    @app.middleware("http")
    async def rate_limit_middleware(request: Request, call_next):
        client_ip = request.client.host if request.client else "unknown"
        now = time.time()
        window = 60  # 1 minute

        # Prune old entries
        _rate_limit_store[client_ip] = [
            t for t in _rate_limit_store[client_ip] if now - t < window
        ]

        if len(_rate_limit_store[client_ip]) >= settings.RATE_LIMIT_PER_MINUTE:
            logger.warning(f"Rate limit exceeded for {client_ip}")
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Try again later."},
            )

        _rate_limit_store[client_ip].append(now)
        response = await call_next(request)
        return response

    # ======================================================================
    # GLOBAL EXCEPTION HANDLER (return 500 without stack trace)
    # ======================================================================

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error(f"Unhandled exception on {request.method} {request.url}: {exc}")
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"},
        )

    # ======================================================================
    # ROUTERS
    # ======================================================================

    # Health checks and metrics (no prefix, public)
    app.include_router(health.router)

    # Authentication endpoints
    app.include_router(auth.router, prefix=settings.API_PREFIX)

    # Dataset management (upload, status, compare)
    app.include_router(dataset.router, prefix=settings.API_PREFIX)

    # Comparison (dedicated router per directory contract)
    app.include_router(comparison.router, prefix=settings.API_PREFIX)

    # Predictions and retention
    app.include_router(prediction.router, prefix=settings.API_PREFIX)

    # ======================================================================
    # ROOT ENDPOINT
    # ======================================================================

    @app.get("/")
    async def root():
        """Root endpoint with API information"""
        return {
            "name": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "status": "operational",
            "docs": "/docs" if is_debug else "disabled",
            "health": "/health",
            "metrics": "/metrics",
        }

    return app


# Create application instance
app = create_app()


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.ENV != "production",
        log_level=settings.LOG_LEVEL.lower(),
        access_log=True,
    )
