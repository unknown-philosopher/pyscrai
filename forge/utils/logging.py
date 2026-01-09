"""
Logging configuration for Forge 3.0.

Provides structured logging with file rotation and formatted output.
"""

from __future__ import annotations

import logging
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

# Module-level logger cache
_loggers: dict[str, logging.Logger] = {}


# ============================================================================
# Custom Formatter
# ============================================================================


class ForgeFormatter(logging.Formatter):
    """Custom formatter with color support and structured output."""
    
    # ANSI color codes for terminal output
    COLORS = {
        "DEBUG": "\033[36m",     # Cyan
        "INFO": "\033[32m",      # Green
        "WARNING": "\033[33m",   # Yellow
        "ERROR": "\033[31m",     # Red
        "CRITICAL": "\033[35m",  # Magenta
        "RESET": "\033[0m",      # Reset
    }
    
    def __init__(
        self,
        use_colors: bool = True,
        include_timestamp: bool = True,
    ):
        """Initialize the formatter.
        
        Args:
            use_colors: Whether to use ANSI colors (for terminals)
            include_timestamp: Whether to include timestamps
        """
        self.use_colors = use_colors
        self.include_timestamp = include_timestamp
        super().__init__()
    
    def format(self, record: logging.LogRecord) -> str:
        # Build format parts
        parts = []
        
        # Timestamp
        if self.include_timestamp:
            timestamp = datetime.fromtimestamp(record.created, UTC).strftime(
                "%Y-%m-%d %H:%M:%S"
            )
            parts.append(f"[{timestamp}]")
        
        # Level
        level = record.levelname
        if self.use_colors:
            color = self.COLORS.get(level, "")
            reset = self.COLORS["RESET"]
            parts.append(f"{color}{level:8}{reset}")
        else:
            parts.append(f"{level:8}")
        
        # Logger name (shortened)
        name = record.name
        if name.startswith("forge."):
            name = name[6:]  # Remove "forge." prefix for readability
        parts.append(f"[{name:20}]")
        
        # Message
        parts.append(record.getMessage())
        
        # Exception info
        if record.exc_info:
            parts.append(self.formatException(record.exc_info))
        
        return " ".join(parts)


# ============================================================================
# Setup Functions
# ============================================================================


def setup_logging(
    level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO",
    log_dir: str | Path | None = None,
    console_output: bool = True,
    file_output: bool = True,
    log_filename: str = "forge.log",
) -> None:
    """Configure the logging system for Forge.
    
    Args:
        level: Minimum log level to capture
        log_dir: Directory for log files (required if file_output=True)
        console_output: Whether to log to console
        file_output: Whether to log to file
        log_filename: Name of the log file
        
    Usage:
        setup_logging(level="DEBUG", log_dir="./logs")
    """
    root_logger = logging.getLogger("forge")
    root_logger.setLevel(getattr(logging, level))
    
    # Clear existing handlers
    root_logger.handlers = []
    
    # Console handler
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, level))
        console_handler.setFormatter(ForgeFormatter(use_colors=True))
        root_logger.addHandler(console_handler)
    
    # File handler
    if file_output and log_dir is not None:
        log_path = Path(log_dir)
        log_path.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(
            log_path / log_filename,
            encoding="utf-8",
        )
        file_handler.setLevel(getattr(logging, level))
        file_handler.setFormatter(ForgeFormatter(use_colors=False))
        root_logger.addHandler(file_handler)
    
    # Prevent propagation to root logger
    root_logger.propagate = False


def get_logger(name: str) -> logging.Logger:
    """Get or create a logger with the given name.
    
    Args:
        name: Logger name (will be prefixed with "forge.")
        
    Returns:
        Configured logger instance
        
    Usage:
        logger = get_logger("extraction")
        logger.info("Starting extraction")
    """
    if not name.startswith("forge."):
        full_name = f"forge.{name}"
    else:
        full_name = name
    
    if full_name not in _loggers:
        _loggers[full_name] = logging.getLogger(full_name)
    
    return _loggers[full_name]


# ============================================================================
# Convenience Functions
# ============================================================================


def log_operation(
    logger: logging.Logger,
    operation: str,
    details: dict | None = None,
) -> None:
    """Log an operation with optional details.
    
    Args:
        logger: Logger to use
        operation: Name of the operation
        details: Optional dict of details
    """
    if details:
        detail_str = ", ".join(f"{k}={v}" for k, v in details.items())
        logger.info(f"{operation}: {detail_str}")
    else:
        logger.info(operation)


def log_error(
    logger: logging.Logger,
    operation: str,
    error: Exception,
    context: dict | None = None,
) -> None:
    """Log an error with context.
    
    Args:
        logger: Logger to use
        operation: Name of the failed operation
        error: The exception
        context: Optional context dict
    """
    msg = f"FAILED {operation}: {type(error).__name__}: {error}"
    if context:
        context_str = ", ".join(f"{k}={v}" for k, v in context.items())
        msg = f"{msg} | Context: {context_str}"
    logger.error(msg, exc_info=True)


# ============================================================================
# Default Setup
# ============================================================================


# Create a basic console-only setup for early imports
setup_logging(level="INFO", console_output=True, file_output=False)
