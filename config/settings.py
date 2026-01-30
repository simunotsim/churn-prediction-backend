from pathlib import Path

# Base directory for the project
BASE_DIR = Path(__file__).resolve().parent.parent

# Data directories
RAW_DATA_DIR = BASE_DIR / 'data' / 'raw'
PROCESSED_DATA_DIR = BASE_DIR / 'data' / 'processed'

# Model parameters
MODEL_PARAMS = {
    'n_estimators': 100,
    'max_depth': 5,
    'random_state': 42
}

# Logging settings
LOGGING_CONFIG = {
    'level': 'INFO',
    'format': '%(asctime)s - %(levelname)s - %(message)s',
    'filename': BASE_DIR / 'logs' / 'app.log'
}

# Other constants
CHURN_THRESHOLD = 0.5  # Probability threshold for predicting churn
