"""Logging configuration"""
import logging
import sys
from logging.handlers import RotatingFileHandler


def setup_logging(app_name: str = "midas-server", log_level: str = "INFO") -> logging.Logger:
    """
    Setup application logging configuration
    
    Args:
        app_name: Name of the application for logging
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(app_name)
    logger.setLevel(getattr(logging, log_level))
    logger.handlers.clear()
    logger.propagate = False
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, log_level))
    
    # File handler with rotation
    file_handler = RotatingFileHandler(
        f"{app_name}.log",
        maxBytes=10485760,  # 10MB
        backupCount=10
    )
    file_handler.setLevel(getattr(logging, log_level))
    
    # Formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)
    
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    # Route module-level logs (e.g. app.llm.*) to the same handlers for easier debugging.
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level))
    root_logger.handlers.clear()
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    
    return logger
