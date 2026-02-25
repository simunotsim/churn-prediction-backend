# Split Container Deployment Guide

## 🎯 Architecture Overview

Your churn prediction backend is now split into **two optimized containers**:

### 1. Lightweight API Container (~150-200MB)
- **Purpose**: Handle HTTP requests, authentication, routing
- **Dependencies**: FastAPI, SQLAlchemy, Celery client, JWT auth
- **NO ML Libraries**: No pandas, numpy, xgboost, scikit-learn
- **Health**: Fast startup, minimal memory (~256-512MB)

### 2. Heavy ML Worker Container (~500-600MB)
- **Purpose**: Execute ML predictions, dataset processing
- **Dependencies**: Full ML stack (pandas, numpy, xgboost, scikit-learn)
- **Models**: Loads models from mounted volumes
- **Health**: Higher memory (~1-2GB), longer startup

**Total Size**: ~650-800MB (vs. previous ~1GB monolithic)

---

## 🚀 Quick Start

### Option 1: Build and Deploy Locally

```powershell
# From backend directory
cd backend

# Build both containers
.\build_and_verify.ps1

# Deploy entire stack
cd ..
docker-compose up -d

# Verify containers
docker ps
docker-compose logs -f backend worker
```

### Option 2: Manual Build

```bash
# Build API container (lightweight)
cd backend
docker build -f Dockerfile.api -t simu06/churn-api:lightweight .

# Build Worker container (heavy)
docker build -f Dockerfile.worker -t simu06/churn-worker:ml .

# Check sizes
docker images | grep churn
```

### Option 3: Pull Pre-built Images

```bash
# Pull from Docker Hub (if you've pushed them)
docker pull simu06/churn-api:lightweight
docker pull simu06/churn-worker:ml

# Deploy
docker-compose up -d
```

---

## 🔧 Configuration

### Environment Variables

Create `.env` file in project root:

```env
# Application
ENV=production
DEBUG=false
SECRET_KEY=your-super-secret-key-here-change-me
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8501

# Database (use MySQL service or AWS RDS)
DATABASE_URL=mysql+pymysql://user:password@host:3306/churn_db

# Redis
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0

# Auth
ACCESS_TOKEN_EXPIRE_MINUTES=60

# ML Settings
CHURN_THRESHOLD=0.5
HIGH_RISK_THRESHOLD=0.7
CRITICAL_RISK_THRESHOLD=0.85

# Logging
LOG_LEVEL=INFO
```

### Required Files

Ensure these exist before deploying:

```bash
models/
  ├── churn_model.pkl          # XGBoost model
  ├── scaler.pkl               # StandardScaler
  └── label_encoders.pkl       # LabelEncoders

data/
  ├── processed/               # For output
  └── raw/                     # For uploaded datasets
```

---

## 🏗️ Production Deployment

### AWS ECS Deployment

```yaml
# Task Definition for API
{
  "family": "churn-api",
  "containerDefinitions": [{
    "name": "api",
    "image": "simu06/churn-api:lightweight",
    "memory": 512,
    "cpu": 256,
    "portMappings": [{"containerPort": 8000}],
    "environment": [
      {"name": "ENV", "value": "production"},
      {"name": "DATABASE_URL", "value": "mysql+pymysql://..."}
    ],
    "healthCheck": {
      "command": ["CMD-SHELL", "curl -f http://localhost:8000/health/live || exit 1"],
      "interval": 30,
      "timeout": 5,
      "retries": 3
    }
  }]
}

# Task Definition for Worker
{
  "family": "churn-worker",
  "containerDefinitions": [{
    "name": "worker",
    "image": "simu06/churn-worker:ml",
    "memory": 2048,
    "cpu": 1024,
    "mountPoints": [{
      "sourceVolume": "models",
      "containerPath": "/app/models",
      "readOnly": true
    }]
  }]
}
```

### Kubernetes Deployment

```yaml
# API Deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: churn-api
spec:
  replicas: 3  # Scale API horizontally
  template:
    spec:
      containers:
      - name: api
        image: simu06/churn-api:lightweight
        resources:
          requests:
            memory: "256Mi"
            cpu: "200m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health/live
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 30

---
# Worker Deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: churn-worker
spec:
  replicas: 2  # Scale workers based on load
  template:
    spec:
      containers:
      - name: worker
        image: simu06/churn-worker:ml
        resources:
          requests:
            memory: "1Gi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "1000m"
        volumeMounts:
        - name: models
          mountPath: /app/models
          readOnly: true
      volumes:
      - name: models
        persistentVolumeClaim:
          claimName: ml-models-pvc
```

### Docker Compose (Production)

```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  backend:
    image: simu06/churn-api:lightweight
    replicas: 3
    environment:
      - ENV=production
      - SECRET_KEY=${SECRET_KEY}
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 512M
      restart_policy:
        condition: on-failure
        max_attempts: 3

  worker:
    image: simu06/churn-worker:ml
    replicas: 2
    environment:
      - ENV=production
    volumes:
      - /mnt/efs/models:/app/models:ro  # AWS EFS mount
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 2G
```

---

## 🧪 Testing

### Health Checks

```bash
# API health
curl http://localhost:8000/health/live
curl http://localhost:8000/health/ready

# Expected response
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00",
  "database": "connected",
  "redis": "connected"
}
```

### Functional Tests

```bash
# 1. Register a user
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"test123"}'

# 2. Login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"test123"}'

# 3. Predict churn
curl -X POST http://localhost:8000/api/v1/predictions/predict \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "tenure": 12,
    "MonthlyCharges": 70.0,
    "TotalCharges": 840.0,
    "Contract": "Month-to-month",
    "InternetService": "Fiber optic"
  }'
```

### Load Testing

```bash
# Install Apache Bench
# Test API performance
ab -n 1000 -c 10 http://localhost:8000/health/live

# Expected: ~500-1000 req/sec for lightweight API
```

---

## 📊 Monitoring

### Container Metrics

```bash
# CPU and memory usage
docker stats backend worker

# Logs
docker-compose logs -f --tail=100 backend
docker-compose logs -f --tail=100 worker

# Worker tasks (Celery)
docker exec -it churn-worker celery -A worker.celery_app inspect active
docker exec -it churn-worker celery -A worker.celery_app inspect stats
```

### Application Metrics

- **API Response Time**: Monitor `/health/ready` endpoint
- **Prediction Latency**: Track time from request to Celery task completion
- **Worker Queue Depth**: Check Celery queue length in Redis
- **Error Rates**: Monitor logs for exceptions

---

## 🔄 CI/CD Pipeline

### GitHub Actions Example

```yaml
name: Build and Deploy

on:
  push:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Build API
        run: |
          cd backend
          docker build -f Dockerfile.api -t simu06/churn-api:${{ github.sha }} .
          docker tag simu06/churn-api:${{ github.sha }} simu06/churn-api:latest
      
      - name: Build Worker
        run: |
          cd backend
          docker build -f Dockerfile.worker -t simu06/churn-worker:${{ github.sha }} .
          docker tag simu06/churn-worker:${{ github.sha }} simu06/churn-worker:latest
      
      - name: Push to Docker Hub
        run: |
          echo "${{ secrets.DOCKER_PASSWORD }}" | docker login -u simu06 --password-stdin
          docker push simu06/churn-api:${{ github.sha }}
          docker push simu06/churn-api:latest
          docker push simu06/churn-worker:${{ github.sha }}
          docker push simu06/churn-worker:latest
      
      - name: Deploy to ECS
        run: |
          aws ecs update-service --cluster churn --service api --force-new-deployment
          aws ecs update-service --cluster churn --service worker --force-new-deployment
```

---

## 🐛 Troubleshooting

### API Container Won't Start

```bash
# Check logs
docker logs churn-backend

# Common issues:
# 1. SECRET_KEY not set
#    Fix: Set in .env or docker-compose.yml
# 2. Database connection failed
#    Fix: Verify DATABASE_URL and database is running
# 3. Import errors
#    Fix: Rebuild with --no-cache
```

### Worker Container Won't Start

```bash
# Check logs
docker logs churn-worker

# Common issues:
# 1. Redis connection failed
#    Fix: Ensure Redis is running and accessible
# 2. Model files not found
#    Fix: Check models/ volume is mounted correctly
# 3. Memory issues
#    Fix: Increase worker memory limits
```

### Models Not Loading

```bash
# Verify files exist
docker exec -it churn-worker ls -lh /app/models

# Should see:
# -rw-r--r-- churn_model.pkl
# -rw-r--r-- scaler.pkl
# -rw-r--r-- label_encoders.pkl

# If missing, check volume mount in docker-compose.yml
```

### High Memory Usage

```bash
# Check worker memory
docker stats churn-worker

# If too high:
# 1. Reduce worker_max_tasks_per_child in celery_app.py
# 2. Increase worker replicas, decrease memory per worker
# 3. Add memory limits in docker-compose.yml
```

---

## 📈 Performance Optimization

### API Container

- **Horizontal Scaling**: Run 3-5 API replicas behind load balancer
- **Connection Pooling**: Increase `pool_size` in database session
- **Caching**: Add Redis cache for frequent queries
- **Async Endpoints**: Use `async def` for I/O-bound operations

### Worker Container

- **Concurrency**: Adjust Celery `worker_concurrency` based on CPU cores
- **Queue Prioritization**: Use separate queues for critical tasks
- **Model Caching**: Keep models in memory (already implemented)
- **Batch Processing**: Process multiple predictions in single task

---

## 🎓 Best Practices

1. **Never include training in production** - Train models offline, deploy artifacts
2. **Separate API from ML** - Keep API lightweight, delegate heavy work to workers
3. **Mount models as volumes** - Don't bake models into images
4. **Use environment variables** - Never hardcode credentials
5. **Monitor everything** - Track metrics, logs, and alerts
6. **Scale independently** - Scale API and workers based on different load patterns
7. **Version your images** - Tag with git commit SHA for rollback capability
8. **Health checks everywhere** - Implement `/health/live` and `/health/ready`

---

## 📝 Maintenance

### Updating Models

```bash
# 1. Train new model offline
python train_model.py

# 2. Save to models/ directory
# models/churn_model_v2.pkl

# 3. Update MODEL_VERSION in settings.py
# 4. Restart worker
docker-compose restart worker
```

### Database Migrations

```bash
# Using Alembic (recommended)
docker exec -it churn-backend alembic revision --autogenerate -m "Add new column"
docker exec -it churn-backend alembic upgrade head
```

### Log Rotation

```yaml
# Add to docker-compose.yml
services:
  backend:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

---

## 🆘 Support

For issues or questions:
1. Check logs: `docker-compose logs`
2. Review ARCHITECTURE.md for design details
3. Review DOCKER_OPTIMIZATION.md for image size tips
4. Check health endpoints
5. Test locally before deploying to production

---

**Deployment Checklist:**
- [ ] Environment variables configured
- [ ] Models uploaded to models/
- [ ] Database accessible
- [ ] Redis running
- [ ] Images built and sized correctly
- [ ] Health checks passing
- [ ] Logs configured
- [ ] Monitoring setup
- [ ] CI/CD pipeline tested
- [ ] Rollback plan ready

Good luck with your deployment! 🚀
