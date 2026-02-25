"""
FastAPI Backend Entry Point
This file redirects to the main API implementation in api/main.py
For actual API endpoints and functionality, see backend/api/main.py
"""

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
import uvicorn

# Create a simple FastAPI app that redirects to the main API
app = FastAPI(
    title="Churn Prediction Backend",
    description="Customer Churn Prediction and Retention Analytics System",
    version="2.0.0"
)

@app.get("/")
async def root():
    """Redirect to API documentation"""
    return RedirectResponse(url="/docs")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "message": "Churn Prediction API is running",
        "note": "Main API is located at backend/api/main.py"
    }

if __name__ == '__main__':
    print("=" * 60)
    print("⚠️  NOTE: This is a simplified entry point.")
    print("⚠️  The main API with all features is in: backend/api/main.py")
    print("⚠️  Run the API with: cd api && python main.py")
    print("=" * 60)
    uvicorn.run(app, host="0.0.0.0", port=8000)