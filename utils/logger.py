import logging
import os
from logging.handlers import RotatingFileHandler
from colorlog import ColoredFormatter

LOG_DIR = ".logs"
LOG_FILE = "automation.log"


def get_logger(name: str = "") -> logging.Logger:
    os.makedirs(LOG_DIR, exist_ok=True)
    logger = logging.getLogger(name)
    logger.propagate = False  # Prevent duplicate logs from bubbling up

    if logger.handlers:
        return logger

    text_format = ""

    if name != "":
        text_format = (
            "%(log_color)s[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s"
        )
    else:
        text_format = "%(log_color)s[%(asctime)s] [%(levelname)s] %(message)s"

    color_formatter = ColoredFormatter(
        text_format,
        datefmt="%Y-%m-%d %H:%M:%S",
        log_colors={
            "DEBUG": "cyan",
            "INFO": "green",
            "WARNING": "yellow",
            "ERROR": "red",
            "CRITICAL": "bold_red",
        },
    )

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(color_formatter)

    file_handler = RotatingFileHandler(
        os.path.join(LOG_DIR, LOG_FILE), maxBytes=5_000_000, backupCount=3
    )
    file_formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler.setFormatter(file_formatter)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger


def configure_root_logger(level=logging.INFO):
    logger = get_logger("root")
    logger.setLevel(level)
    for handler in logger.handlers:
        handler.setLevel(level)
