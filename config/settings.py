"""
Configuration settings for the Churn Prediction API
Uses environment variables for portability across environments
"""

import os
from pathlib import Path

# Load .env file if python-dotenv is available
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    pass  # python-dotenv not installed, use system env vars


def get_project_root():
    """Get the project root directory dynamically"""
    # Start from config folder, go up to find project root
    current = Path(__file__).resolve().parent.parent.parent
    
    # Check if we're in the right place (has data/ or models/)
    if (current / "data").exists() or (current / "models").exists():
        return current
    
    # Fallback to environment variable
    if os.getenv("PROJECT_ROOT"):
        return Path(os.getenv("PROJECT_ROOT"))
    
    # Fallback to parent of backend folder
    return Path(__file__).resolve().parent.parent.parent


# =============================================================================
# PATH CONFIGURATION (Override with environment variables)
# =============================================================================

PROJECT_ROOT = get_project_root()
BASE_DIR = Path(__file__).resolve().parent.parent  # backend folder

# Model paths - from separate models repo/folder
MODELS_PATH = Path(os.getenv("MODELS_PATH", PROJECT_ROOT / "models"))

# Data paths
DATA_PATH = Path(os.getenv("DATA_PATH", PROJECT_ROOT / "data"))
RAW_DATA_DIR = DATA_PATH / "raw"
PROCESSED_DATA_DIR = DATA_PATH / "processed"

# =============================================================================
# FILE NAMES (Override with environment variables)
# =============================================================================

MODEL_FILE = os.getenv("MODEL_FILE", "xgb_tuned_model.pkl")
SCALER_FILE = os.getenv("SCALER_FILE", "scaler.pkl")
ENCODERS_FILE = os.getenv("ENCODERS_FILE", "label_encoders.pkl")
PREDICTIONS_FILE = os.getenv("PREDICTIONS_FILE", "customer_predictions.csv")
RETENTION_FILE = os.getenv("RETENTION_FILE", "retention_actions.csv")
MODEL_COMPARISON_FILE = os.getenv("MODEL_COMPARISON_FILE", "model_comparison.csv")

# =============================================================================
# API CONFIGURATION
# =============================================================================

API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))
DEBUG = os.getenv("DEBUG", "true").lower() == "true"

# CORS - allowed origins (comma-separated in env var)
# Use "*" to allow all origins in development
ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS", 
    "*"
).split(",")

# Strip whitespace from origins
ALLOWED_ORIGINS = [origin.strip() for origin in ALLOWED_ORIGINS]

# =============================================================================
# MODEL PARAMETERS
# =============================================================================

MODEL_PARAMS = {
    'n_estimators': 100,
    'max_depth': 5,
    'random_state': 42
}

CHURN_THRESHOLD = float(os.getenv("CHURN_THRESHOLD", "0.5"))

# =============================================================================
# DATABASE CONFIGURATION (For future dynamic data)
# =============================================================================

DATABASE_URL = os.getenv("DATABASE_URL", "")
USE_DATABASE = os.getenv("USE_DATABASE", "false").lower() == "true"

# =============================================================================
# LOGGING
# =============================================================================

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_DIR = BASE_DIR / "logs"

LOGGING_CONFIG = {
    'level': LOG_LEVEL,
    'format': '%(asctime)s - %(levelname)s - %(message)s',
    'filename': LOG_DIR / 'app.log'
}

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_model_path(filename: str = None) -> Path:
    """Get full path to a model file"""
    if filename:
        return MODELS_PATH / filename
    return MODELS_PATH / MODEL_FILE

def get_data_path(filename: str) -> Path:
    """Get full path to a processed data file"""
    return PROCESSED_DATA_DIR / filename

def print_config():
    """Print current configuration for debugging"""
    print("=" * 60)
    print("CONFIGURATION")
    print("=" * 60)
    print(f"   PROJECT_ROOT: {PROJECT_ROOT}")
    print(f"   MODELS_PATH: {MODELS_PATH}")
    print(f"   DATA_PATH: {DATA_PATH}")
    print(f"   API_HOST: {API_HOST}:{API_PORT}")
    print(f"   DEBUG: {DEBUG}")
    print(f"   USE_DATABASE: {USE_DATABASE}")
    print("=" * 60)
