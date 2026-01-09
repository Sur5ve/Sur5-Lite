#!/usr/bin/env python3
"""
Sur5 Logging System
Centralized logging with file rotation and colored console output.
"""

import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional


# Log levels mapping for easy access
LOG_LEVELS = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}

# Default configuration
DEFAULT_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
DEFAULT_MAX_BYTES = 5 * 1024 * 1024  # 5 MB
DEFAULT_BACKUP_COUNT = 3
DEFAULT_LOG_LEVEL = logging.INFO

# Module-level logger cache
_loggers = {}
_file_handler: Optional[RotatingFileHandler] = None
_console_handler: Optional[logging.StreamHandler] = None
_is_initialized = False


class ColoredFormatter(logging.Formatter):
    """Formatter that adds colors to log levels for console output."""
    
    # ANSI color codes (works on Windows 10+ and Unix)
    COLORS = {
        logging.DEBUG: "\033[36m",     # Cyan
        logging.INFO: "\033[32m",      # Green
        logging.WARNING: "\033[33m",   # Yellow
        logging.ERROR: "\033[31m",     # Red
        logging.CRITICAL: "\033[35m",  # Magenta
    }
    RESET = "\033[0m"
    BOLD = "\033[1m"
    
    def __init__(self, fmt=None, datefmt=None, use_colors=True):
        super().__init__(fmt, datefmt)
        self.use_colors = use_colors and self._supports_color()
    
    def _supports_color(self) -> bool:
        """Check if the terminal supports color output."""
        # Check if we're in a terminal
        if not hasattr(sys.stdout, 'isatty') or not sys.stdout.isatty():
            return False
        
        # Windows 10+ supports ANSI colors
        if sys.platform == 'win32':
            try:
                import ctypes
                kernel32 = ctypes.windll.kernel32
                # Enable ANSI escape sequences
                kernel32.SetConsoleMode(
                    kernel32.GetStdHandle(-11),
                    7  # ENABLE_PROCESSED_OUTPUT | ENABLE_WRAP_AT_EOL_OUTPUT | ENABLE_VIRTUAL_TERMINAL_PROCESSING
                )
                return True
            except Exception:
                return False
        
        # Unix terminals generally support colors
        return True
    
    def format(self, record: logging.LogRecord) -> str:
        if self.use_colors and record.levelno in self.COLORS:
            levelname = record.levelname
            record.levelname = f"{self.COLORS[record.levelno]}{levelname}{self.RESET}"
            formatted = super().format(record)
            record.levelname = levelname  # Restore original
            return formatted
        return super().format(record)


def get_log_directory() -> Path:
    """Get the log directory path (portable-aware)."""
    try:
        from .portable_paths import get_app_root, is_portable_mode
        
        if is_portable_mode():
            log_dir = get_app_root() / "UserData" / "logs"
        else:
            # Use standard app data location
            if sys.platform == 'win32':
                base = Path(os.environ.get('LOCALAPPDATA', Path.home()))
            elif sys.platform == 'darwin':
                base = Path.home() / "Library" / "Application Support"
            else:
                base = Path.home() / ".local" / "share"
            log_dir = base / "Sur5" / "logs"
    except ImportError:
        # Fallback if portable_paths not available
        log_dir = Path.cwd() / "logs"
    
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


def init_logging(
    log_level: int = DEFAULT_LOG_LEVEL,
    log_to_file: bool = True,
    log_to_console: bool = True,
    log_format: str = DEFAULT_LOG_FORMAT,
    date_format: str = DEFAULT_DATE_FORMAT,
    max_bytes: int = DEFAULT_MAX_BYTES,
    backup_count: int = DEFAULT_BACKUP_COUNT,
    colored_console: bool = True,
) -> None:
    """
    Initialize the logging system.
    
    Args:
        log_level: Minimum log level to capture
        log_to_file: Whether to log to file
        log_to_console: Whether to log to console
        log_format: Log message format string
        date_format: Date format string
        max_bytes: Maximum log file size before rotation
        backup_count: Number of backup files to keep
        colored_console: Whether to use colored output in console
    """
    global _file_handler, _console_handler, _is_initialized
    
    if _is_initialized:
        return
    
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Remove any existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # File handler with rotation
    if log_to_file:
        try:
            log_dir = get_log_directory()
            log_file = log_dir / "sur5.log"
            
            _file_handler = RotatingFileHandler(
                log_file,
                maxBytes=max_bytes,
                backupCount=backup_count,
                encoding='utf-8'
            )
            _file_handler.setLevel(log_level)
            _file_handler.setFormatter(logging.Formatter(log_format, date_format))
            root_logger.addHandler(_file_handler)
        except Exception as e:
            print(f"[Logger] Could not initialize file handler: {e}")
    
    # Console handler with optional colors
    if log_to_console:
        _console_handler = logging.StreamHandler(sys.stdout)
        _console_handler.setLevel(log_level)
        
        if colored_console:
            formatter = ColoredFormatter(log_format, date_format)
        else:
            formatter = logging.Formatter(log_format, date_format)
        
        _console_handler.setFormatter(formatter)
        root_logger.addHandler(_console_handler)
    
    _is_initialized = True
    
    # Log initialization
    logger = get_logger("Sur5.Logger")
    logger.info(f"Logging initialized (level: {logging.getLevelName(log_level)})")
    if log_to_file:
        logger.debug(f"Log file: {get_log_directory() / 'sur5.log'}")


def get_logger(name: str) -> logging.Logger:
    """
    Get or create a logger with the given name.
    
    Args:
        name: Logger name (e.g., "Sur5.Services.Model")
        
    Returns:
        Configured logger instance
    """
    global _is_initialized
    
    # Auto-initialize if not done yet
    if not _is_initialized:
        init_logging()
    
    if name not in _loggers:
        _loggers[name] = logging.getLogger(name)
    
    return _loggers[name]


def set_log_level(level: int) -> None:
    """
    Set the log level for all handlers.
    
    Args:
        level: New log level (use logging.DEBUG, logging.INFO, etc.)
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    if _file_handler:
        _file_handler.setLevel(level)
    if _console_handler:
        _console_handler.setLevel(level)


def get_log_file_path() -> Optional[Path]:
    """Get the current log file path."""
    if _file_handler:
        return Path(_file_handler.baseFilename)
    return get_log_directory() / "sur5.log"


def get_recent_logs(lines: int = 100) -> str:
    """
    Get the most recent log lines.
    
    Args:
        lines: Number of lines to retrieve
        
    Returns:
        String containing the recent log lines
    """
    log_file = get_log_file_path()
    if not log_file or not log_file.exists():
        return ""
    
    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            all_lines = f.readlines()
            return ''.join(all_lines[-lines:])
    except Exception as e:
        return f"Error reading log file: {e}"


# Convenience function to create module-level loggers
def create_module_logger(module_name: str) -> logging.Logger:
    """
    Create a logger for a module with Sur5 prefix.
    
    Usage:
        logger = create_module_logger(__name__)
        logger.info("Message")
    
    Args:
        module_name: Usually __name__ from the calling module
        
    Returns:
        Configured logger
    """
    # Convert module path to logger name
    # e.g., "sur5_lite_pyside.services.model_service" -> "Sur5.Services.ModelService"
    parts = module_name.split('.')
    
    # Clean up the name
    clean_parts = []
    for part in parts:
        if part == "sur5_lite_pyside":
            clean_parts.append("Sur5")
        elif part.startswith("_"):
            continue
        else:
            # Convert snake_case to TitleCase
            clean_parts.append(''.join(word.title() for word in part.split('_')))
    
    logger_name = '.'.join(clean_parts) if clean_parts else "Sur5"
    return get_logger(logger_name)


# Export public interface
__all__ = [
    "init_logging",
    "get_logger",
    "create_module_logger",
    "set_log_level",
    "get_log_file_path",
    "get_recent_logs",
    "get_log_directory",
    "LOG_LEVELS",
    "ColoredFormatter",
]

