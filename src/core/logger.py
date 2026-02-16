"""
Logging module for pyCol.

Provides centralized logging with file rotation and configurable log levels.
Log files are stored in %APPDATA%/pyCol/logs/
"""
import os
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

# Global logger instance
_loggers = {}
_file_handler = None
_log_folder = None

def get_log_folder() -> Path:
    """Get the log folder path, creating it if necessary."""
    global _log_folder
    if _log_folder is None:
        # Use LOCALAPPDATA on Windows (not roaming), fallback to home
        localappdata = os.environ.get('LOCALAPPDATA', os.environ.get('APPDATA', os.path.expanduser('~')))
        _log_folder = Path(localappdata) / 'pyCol' / 'logs'
        _log_folder.mkdir(parents=True, exist_ok=True)
    return _log_folder

def init_logging(level: str = 'INFO', max_size_mb: int = 5, backup_count: int = 3):
    """
    Initialize the logging system.
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR)
        max_size_mb: Maximum log file size in megabytes
        backup_count: Number of backup files to keep
    """
    global _file_handler
    
    log_folder = get_log_folder()
    log_file = log_folder / 'pyCol.log'
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-5s | %(name)-15s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Create rotating file handler
    _file_handler = RotatingFileHandler(
        log_file,
        maxBytes=max_size_mb * 1024 * 1024,
        backupCount=backup_count,
        encoding='utf-8'
    )
    _file_handler.setFormatter(formatter)
    
    # Set root logger level
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    
    # Remove existing handlers and add our file handler
    root_logger.handlers.clear()
    root_logger.addHandler(_file_handler)
    
    # Also log to console if available (development mode)
    try:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
    except Exception:
        pass  # No console available (e.g., Windows GUI app)

def set_log_level(level: str):
    """Change the log level at runtime."""
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))

def set_rotation_settings(max_size_mb: int, backup_count: int):
    """Update rotation settings. Takes effect on next log file rotation."""
    global _file_handler
    if _file_handler:
        _file_handler.maxBytes = max_size_mb * 1024 * 1024
        _file_handler.backupCount = backup_count

def get_logger(name: str) -> logging.Logger:
    """
    Get a logger for a specific module.
    
    Args:
        name: Module name (e.g., 'camera', 'settings', 'overlay')
    
    Returns:
        Logger instance
    """
    if name not in _loggers:
        _loggers[name] = logging.getLogger(name)
    return _loggers[name]
