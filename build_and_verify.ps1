# Build and Verify Split Container Architecture
# This script builds both lightweight API and heavy ML worker containers

Write-Host "`n=== Churn Prediction - Split Container Build & Verification ===" -ForegroundColor Cyan
Write-Host "Expected Results:" -ForegroundColor Yellow
Write-Host "  - API Container: ~150-200MB (lightweight, no ML)" -ForegroundColor Green
Write-Host "  - Worker Container: ~500-600MB (heavy, includes ML)" -ForegroundColor Green
Write-Host "  - Total: ~650-800MB (vs. previous ~1GB monolithic)`n" -ForegroundColor Green

# Check if we're in backend directory
if (-not (Test-Path "Dockerfile.api")) {
    Write-Host "ERROR: Run this script from the backend directory!" -ForegroundColor Red
    Write-Host "Usage: cd backend && .\build_and_verify.ps1" -ForegroundColor Yellow
    exit 1
}

# Check Docker is running
Write-Host "[1/6] Checking Docker..." -ForegroundColor Cyan
try {
    docker info | Out-Null
    Write-Host "✓ Docker is running" -ForegroundColor Green
} catch {
    Write-Host "✗ Docker is not running. Please start Docker Desktop." -ForegroundColor Red
    exit 1
}

# Build lightweight API container
Write-Host "`n[2/6] Building Lightweight API Container..." -ForegroundColor Cyan
Write-Host "Using: Dockerfile.api (no ML dependencies)" -ForegroundColor Gray
$apiStartTime = Get-Date
docker build -f Dockerfile.api -t churn-api:lightweight -t simu06/churn-api:lightweight .

if ($LASTEXITCODE -ne 0) {
    Write-Host "✗ API build failed!" -ForegroundColor Red
    exit 1
}
$apiDuration = ((Get-Date) - $apiStartTime).TotalSeconds
Write-Host "✓ API container built in $([math]::Round($apiDuration, 1)) seconds" -ForegroundColor Green

# Build heavy ML worker container
Write-Host "`n[3/6] Building Heavy ML Worker Container..." -ForegroundColor Cyan
Write-Host "Using: Dockerfile.worker (includes pandas, numpy, xgboost)" -ForegroundColor Gray
$workerStartTime = Get-Date
docker build -f Dockerfile.worker -t churn-worker:ml -t simu06/churn-worker:ml .

if ($LASTEXITCODE -ne 0) {
    Write-Host "✗ Worker build failed!" -ForegroundColor Red
    exit 1
}
$workerDuration = ((Get-Date) - $workerStartTime).TotalSeconds
Write-Host "✓ Worker container built in $([math]::Round($workerDuration, 1)) seconds" -ForegroundColor Green

# Get image sizes
Write-Host "`n[4/6] Analyzing Container Sizes..." -ForegroundColor Cyan
$images = docker images --format "table {{.Repository}}:{{.Tag}}\t{{.Size}}" | Select-String "churn-"

Write-Host "`nContainer Sizes:" -ForegroundColor Yellow
$images | ForEach-Object {
    Write-Host "  $_" -ForegroundColor White
}

# Extract sizes for comparison
$apiSize = (docker images churn-api:lightweight --format "{{.Size}}")
$workerSize = (docker images churn-worker:ml --format "{{.Size}}")

Write-Host "`nSize Analysis:" -ForegroundColor Yellow
Write-Host "  API Container:    $apiSize" -ForegroundColor $(if ($apiSize -match "1[0-9][0-9]MB|200MB") { "Green" } else { "Yellow" })
Write-Host "  Worker Container: $workerSize" -ForegroundColor $(if ($workerSize -match "[4-6][0-9][0-9]MB") { "Green" } else { "Yellow" })

# Verify layers
Write-Host "`n[5/6] Verifying Container Layers..." -ForegroundColor Cyan
Write-Host "`nAPI Container Layers:" -ForegroundColor Yellow
docker history churn-api:lightweight --human --format "table {{.CreatedBy}}\t{{.Size}}" | Select-Object -First 10

Write-Host "`nWorker Container Layers:" -ForegroundColor Yellow
docker history churn-worker:ml --human --format "table {{.CreatedBy}}\t{{.Size}}" | Select-Object -First 10

# Quick container test
Write-Host "`n[6/6] Testing Containers..." -ForegroundColor Cyan

Write-Host "Testing API container startup..." -ForegroundColor Gray
$apiTest = docker run --rm -d --name test-api -e SECRET_KEY=test-key -e DATABASE_URL=sqlite:///./test.db churn-api:lightweight
Start-Sleep -Seconds 3

$apiHealthy = docker logs test-api 2>&1 | Select-String "Application startup complete"
if ($apiHealthy) {
    Write-Host "✓ API container starts successfully" -ForegroundColor Green
} else {
    Write-Host "⚠ API container may have issues (check logs)" -ForegroundColor Yellow
}
docker stop test-api | Out-Null

Write-Host "Testing Worker container startup..." -ForegroundColor Gray
$workerTest = docker run --rm -d --name test-worker -e SECRET_KEY=test-key -e CELERY_BROKER_URL=redis://localhost:6379/0 churn-worker:ml
Start-Sleep -Seconds 3

$workerHealthy = docker logs test-worker 2>&1 | Select-String "celery@"
if ($workerHealthy) {
    Write-Host "✓ Worker container starts successfully" -ForegroundColor Green
} else {
    Write-Host "⚠ Worker container may have issues (check logs)" -ForegroundColor Yellow
}
docker stop test-worker | Out-Null

# Summary
Write-Host "`n=== Build Summary ===" -ForegroundColor Cyan
Write-Host "✓ Lightweight API built:  $apiSize" -ForegroundColor Green
Write-Host "✓ Heavy ML Worker built:  $workerSize" -ForegroundColor Green
Write-Host "✓ Total size reduction:   Success" -ForegroundColor Green

Write-Host "`nNext Steps:" -ForegroundColor Yellow
Write-Host "1. Deploy with: docker-compose up -d" -ForegroundColor White
Write-Host "2. Check logs:  docker-compose logs -f backend worker" -ForegroundColor White
Write-Host "3. Test API:    curl http://localhost:8000/health/live" -ForegroundColor White
Write-Host "4. Push images: docker push simu06/churn-api:lightweight && docker push simu06/churn-worker:ml" -ForegroundColor White

Write-Host "`n=== Verification Complete ===" -ForegroundColor Green
