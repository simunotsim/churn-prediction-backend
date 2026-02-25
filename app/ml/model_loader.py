"""
ML Model loader and manager
Handles loading and caching of ML models, scalers, and encoders
"""

import joblib
from pathlib import Path
from typing import Optional, Tuple, Any
from threading import Lock

from app.core.config import get_settings
from app.core.logging import get_logger

settings = get_settings()
logger = get_logger(__name__)


class ModelLoader:
    """Singleton model loader with lazy loading and caching"""
    
    _instance = None
    _lock = Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._model = None
        self._scaler = None
        self._encoders = None
        self._initialized = True
    
    def load_artifacts(self) -> Tuple[Any, Any, Any]:
        """
        Load model artifacts (model, scaler, encoders)
        
        Returns:
            Tuple of (model, scaler, encoders)
        
        Raises:
            FileNotFoundError: If model files not found
            Exception: If loading fails
        """
        if self._model is not None:
            # Already loaded
            return self._model, self._scaler, self._encoders
        
        try:
            model_path = settings.MODELS_PATH
            
            # Check if files exist
            model_file = model_path / settings.MODEL_FILE
            scaler_file = model_path / settings.SCALER_FILE
            encoders_file = model_path / settings.ENCODERS_FILE
            
            if not model_file.exists():
                raise FileNotFoundError(f"Model file not found: {model_file}")
            if not scaler_file.exists():
                raise FileNotFoundError(f"Scaler file not found: {scaler_file}")
            if not encoders_file.exists():
                raise FileNotFoundError(f"Encoders file not found: {encoders_file}")
            
            # Load artifacts
            logger.info(f"Loading model from {model_path}")
            self._model = joblib.load(model_file)
            self._scaler = joblib.load(scaler_file)
            self._encoders = joblib.load(encoders_file)
            
            logger.info("Model artifacts loaded successfully")
            return self._model, self._scaler, self._encoders
            
        except Exception as e:
            logger.error(f"Failed to load model artifacts: {e}")
            raise
    
    def get_model(self) -> Any:
        """Get loaded model (loads if not already loaded)"""
        model, _, _ = self.load_artifacts()
        return model
    
    def get_scaler(self) -> Any:
        """Get loaded scaler (loads if not already loaded)"""
        _, scaler, _ = self.load_artifacts()
        return scaler
    
    def get_encoders(self) -> Any:
        """Get loaded encoders (loads if not already loaded)"""
        _, _, encoders = self.load_artifacts()
        return encoders
    
    def reload(self) -> None:
        """Reload model artifacts (useful for model updates)"""
        logger.info("Reloading model artifacts")
        self._model = None
        self._scaler = None
        self._encoders = None
        self.load_artifacts()
    
    def is_loaded(self) -> bool:
        """Check if models are loaded"""
        return self._model is not None


# Global model loader instance
model_loader = ModelLoader()


def get_model_loader() -> ModelLoader:
    """Get model loader instance (for dependency injection)"""
    return model_loader
