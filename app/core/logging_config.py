"""
Centralized logging configuration
Production-ready structured logging with rotation
Format: timestamp | level | module | message
"""

import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from typing import Optional

from app.core.config import get_settings

settings = get_settings()


class StructuredFormatter(logging.Formatter):
    """Structured log formatter: timestamp | level | module | message"""

    def format(self, record: logging.LogRecord) -> str:
        timestamp = self.formatTime(record, datefmt="%Y-%m-%d %H:%M:%S")
        level = record.levelname
        module = record.name
        message = record.getMessage()
        return f"{timestamp} | {level} | {module} | {message}"


def setup_logging(
    log_level: Optional[str] = None,
    log_file: Optional[str] = None,
    log_to_console: bool = True,
) -> logging.Logger:
    """
    Configure application logging with structured format

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional log file path
        log_to_console: Whether to log to console

    Returns:
        Configured logger instance
    """
    level_name = log_level or settings.LOG_LEVEL
    level = getattr(logging, level_name.upper(), logging.INFO)

    logger = logging.getLogger("churn_api")
    logger.setLevel(level)

    # Clear existing handlers
    logger.handlers.clear()

    # Structured formatter: timestamp | level | module | message
    formatter = StructuredFormatter()

    # Console handler
    if log_to_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    # File handler with rotation
    file_path = log_file or settings.LOG_FILE
    if file_path:
        log_path = Path(file_path)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = RotatingFileHandler(
            log_path,
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=5,
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def get_logger(name: str = "churn_api") -> logging.Logger:
    """
    Get logger instance

    Args:
        name: Logger name

    Returns:
        Logger instance
    """
    return logging.getLogger(name)


# Initialize default logger
logger = setup_logging()
