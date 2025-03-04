import os
import logging
from logging.handlers import RotatingFileHandler

# Ensure logs directory exists
LOG_FILE = "logs/app.log"
LOG_DIR = os.path.dirname(LOG_FILE)
os.makedirs(LOG_DIR, exist_ok=True)

# Logging Configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_MAX_SIZE = 5 * 1024 * 1024  # 5 MB
LOG_BACKUP_COUNT = 3

def setup_logging():
    """Setup centralized logging configuration."""
    log_format = "%(asctime)s - %(levelname)s - %(message)s"
    log_level = getattr(logging, LOG_LEVEL, logging.INFO)

    # Create logger
    logger = logging.getLogger("custom_logger")
    logger.setLevel(log_level)

    # Console Handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(log_format))
    logger.addHandler(console_handler)

    # File Handler with rotation
    file_handler = RotatingFileHandler(LOG_FILE, maxBytes=LOG_MAX_SIZE, backupCount=LOG_BACKUP_COUNT)
    file_handler.setFormatter(logging.Formatter(log_format))
    logger.addHandler(file_handler)

    return logger  # Return the logger instance

# Initialize logging and return the logger object
LOGGER = setup_logging()
