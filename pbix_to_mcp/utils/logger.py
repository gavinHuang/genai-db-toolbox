"""
Logging Utility

Sets up logging for the PBIX to MCP conversion process.
"""

import logging
import sys
from pathlib import Path
from typing import Optional


def setup_logger(
    name: str,
    log_file: Optional[Path] = None,
    level: int = logging.INFO,
    console_output: bool = True,
) -> logging.Logger:
    """
    Set up a logger with file and console handlers.

    Args:
        name: Logger name
        log_file: Optional log file path
        level: Logging level
        console_output: Whether to output to console

    Returns:
        Configured logger
    """
    logger = logging.getLogger(name)

    # Clear existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    logger.setLevel(level)

    # Create formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Console handler
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    # File handler
    if log_file:
        log_file.parent.mkdir(exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)  # Always debug level for file
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get an existing logger or create a basic one.

    Args:
        name: Logger name

    Returns:
        Logger instance
    """
    logger = logging.getLogger(name)

    # If no handlers exist, set up basic console logging
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter("%(name)s - %(levelname)s - %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger


def set_log_level(logger_name: str, level: int) -> None:
    """
    Set log level for a specific logger.

    Args:
        logger_name: Name of the logger
        level: New log level
    """
    logger = logging.getLogger(logger_name)
    logger.setLevel(level)

    # Update handler levels too
    for handler in logger.handlers:
        if isinstance(handler, logging.StreamHandler):
            handler.setLevel(level)


def disable_logger(logger_name: str) -> None:
    """
    Disable a specific logger.

    Args:
        logger_name: Name of the logger to disable
    """
    logger = logging.getLogger(logger_name)
    logger.disabled = True


def enable_logger(logger_name: str) -> None:
    """
    Enable a specific logger.

    Args:
        logger_name: Name of the logger to enable
    """
    logger = logging.getLogger(logger_name)
    logger.disabled = False
