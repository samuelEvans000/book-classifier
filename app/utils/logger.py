"""Structured logger with Rich console + rotating file handler."""

import logging
import os
import sys
from logging.handlers import RotatingFileHandler

from rich.logging import RichHandler
from app.config import config


def get_logger(name: str = "classifier") -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger  # Already configured

    logger.setLevel(logging.DEBUG)

    # Console handler (Rich, INFO+)
    console = RichHandler(
        show_time=True,
        show_path=False,
        rich_tracebacks=True,
        markup=True,
    )
    console.setLevel(logging.INFO)
    logger.addHandler(console)

    # File handler (DEBUG+, rotating 50 MB × 3)
    os.makedirs(os.path.dirname(config.LOG_FILE), exist_ok=True)
    file_handler = RotatingFileHandler(
        config.LOG_FILE,
        maxBytes=50 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    file_handler.setFormatter(fmt)
    logger.addHandler(file_handler)

    return logger


logger = get_logger()