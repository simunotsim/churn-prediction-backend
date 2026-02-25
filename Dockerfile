# ============================================================
# Production Dockerfile for Churn Prediction API
# Multi-stage build for minimal image size
# ============================================================

# ============================================================
# Stage 1: Build dependencies
# ============================================================
FROM python:3.11-slim AS builder

WORKDIR /build

ENV PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=300

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ make \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install all Python dependencies in one layer
RUN pip install --prefix=/install --no-cache-dir -r requirements.txt

# Clean up unnecessary files to reduce image size
RUN find /install -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null; \
    find /install -type d -name "tests" -exec rm -rf {} + 2>/dev/null; \
    find /install -type d -name "test" -exec rm -rf {} + 2>/dev/null; \
    find /install -name "*.pyc" -delete 2>/dev/null; \
    find /install -name "*.pyo" -delete 2>/dev/null; \
    true

# ============================================================
# Stage 2: Production runtime image
# ============================================================
FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy Python packages from builder
COPY --from=builder /install/lib /usr/local/lib
COPY --from=builder /install/bin /usr/local/bin

# Copy application code with new structure
COPY app/ ./app/
COPY worker/ ./worker/

# Create necessary directories
RUN mkdir -p /app/data/processed /app/models /app/logs

# Expose API port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Default command - run FastAPI with uvicorn
# For production, use: gunicorn app.main:app -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000 --workers 4
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
