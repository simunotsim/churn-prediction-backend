"""
Backward-compatible logging module.
All implementation lives in logging_config.py per architecture contract.
"""

from app.core.logging_config import setup_logging, get_logger, logger, StructuredFormatter

__all__ = ["setup_logging", "get_logger", "logger", "StructuredFormatter"]

