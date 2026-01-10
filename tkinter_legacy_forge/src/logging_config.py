"""Logging configuration for PyScrAI|Forge.

Configures the root logger to output to the terminal (stdout) for observability.
"""

import logging
import sys
import os

def setup_logging(verbose: bool = False):
    """Configure the root logger to output to stdout.
    
    Args:
        verbose: If True, sets log level to DEBUG for verbose output
    """
    # Create logger
    logger = logging.getLogger()
    
    # Set log level based on verbose flag or environment variable
    log_level = logging.DEBUG if (verbose or os.getenv("PYSCRAI_VERBOSE", "").lower() in ("1", "true", "yes")) else logging.INFO
    logger.setLevel(log_level)
    
    # Check if handlers already exist to avoid duplicates
    if logger.hasHandlers():
        logger.handlers.clear()
        
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Add formatter to handler
    console_handler.setFormatter(formatter)
    
    # Add handler to logger
    logger.addHandler(console_handler)
    
    if log_level == logging.DEBUG:
        logging.info("Logging initialized with VERBOSE mode (DEBUG level). Output directed to terminal.")
    else:
        logging.info("Logging initialized. Output directed to terminal.")

def get_logger(name: str) -> logging.Logger:
    """Get a named logger.
    
    Args:
        name: Name of the logger (typically __name__)
        
    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)
