"""Logging configuration for PyScrAI|Forge.

Configures the root logger to output to the terminal (stdout) for observability.
"""

import logging
import sys

def setup_logging():
    """Configure the root logger to output to stdout."""
    # Create logger
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # Check if handlers already exist to avoid duplicates
    if logger.hasHandlers():
        logger.handlers.clear()

    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)

    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Add formatter to handler
    console_handler.setFormatter(formatter)

    # Add handler to logger
    logger.addHandler(console_handler)

    logging.info("Logging initialized. Output directed to terminal.")

def get_logger(name: str) -> logging.Logger:
    """Get a named logger.

    Args:
        name: Name of the logger (typically __name__)

    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)
