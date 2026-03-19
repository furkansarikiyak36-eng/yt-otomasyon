"""
utils/logger.py — Centralized logging setup
"""
import logging
import os
from logging.handlers import RotatingFileHandler
from config import Config


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger  # already configured

    level = getattr(logging, Config.LOG_LEVEL.upper(), logging.INFO)
    logger.setLevel(level)

    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Console
    ch = logging.StreamHandler()
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    # File (rotating, max 10MB, keep 5 files)
    os.makedirs(Config.LOG_DIR, exist_ok=True)
    fh = RotatingFileHandler(
        os.path.join(Config.LOG_DIR, f"{name}.log"),
        maxBytes=10 * 1024 * 1024,
        backupCount=5
    )
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    return logger
