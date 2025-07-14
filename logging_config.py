import logging
import json
import os
from datetime import datetime
from pythonjsonlogger import jsonlogger
from logging.handlers import RotatingFileHandler


class StructuredLogger:
    ""
    Structured JSON logger for the Mercari monitoring tool.
    Provides both console and file logging with rotation.
    """
    
    def __init__(self, name: str, log_dir: str = "logs"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)
        
        # Create logs directory if it doesn't exist
        self.log_dir = log_dir
        os.makedirs(self.log_dir, exist_ok=True)
        
        # Setup formatters
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        json_formatter = jsonlogger.JsonFormatter(
            fmt='%(asctime)s %(name)s %(levelname)s %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(console_formatter)
        
        # File handlers with rotation
        file_handler = RotatingFileHandler(
            os.path.join(self.log_dir, 'mercari_monitor.json'),
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(json_formatter)
        
        # Error file handler
        error_handler = RotatingFileHandler(
            os.path.join(self.log_dir, 'mercari_monitor_errors.json'),
            maxBytes=5*1024*1024,  # 5MB
            backupCount=3
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(json_formatter)
        
        # Add handlers to logger
        self.logger.addHandler(console_handler)
        self.logger.addHandler(file_handler)
        self.logger.addHandler(error_handler)
    
    def debug(self, message: str, **kwargs):
        self.logger.debug(message, extra=kwargs)
    
    def info(self, message: str, **kwargs):
        self.logger.info(message, extra=kwargs)
    
    def warning(self, message: str, **kwargs):
        self.logger.warning(message, extra=kwargs)
    
    def error(self, message: str, **kwargs):
        self.logger.error(message, extra=kwargs)
    
    def critical(self, message: str, **kwargs):
        self.logger.critical(message, extra=kwargs)
    
    def log_exception(self, message: str, exc_info=True, **kwargs):
        self.logger.error(message, exc_info=exc_info, extra=kwargs)


def get_logger(name: str) -> StructuredLogger:
    """Factory function to get a configured logger instance."""
    return StructuredLogger(name)


class LoggingContext:
    """Context manager for adding additional context to logs."""
    
    def __init__(self, logger, **context):
        self.logger = logger
        self.context = context
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.logger.log_exception(
                "Exception occurred",
                operation=self.context.get('operation'),
                error_type=str(exc_type.__name__)
            )