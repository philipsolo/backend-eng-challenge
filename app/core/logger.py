import json
import logging
import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional


# ANSI color constants
class Colors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    CYAN = "\033[36m"


LOG_LEVELS = {
    "DEBUG": {"color": Colors.BLUE, "level": logging.DEBUG},
    "INFO": {"color": Colors.GREEN, "level": logging.INFO},
    "WARNING": {"color": Colors.YELLOW, "level": logging.WARNING},
    "ERROR": {"color": Colors.RED, "level": logging.ERROR},
    "CRITICAL": {"color": Colors.BOLD + Colors.RED, "level": logging.CRITICAL},
}

LOG_FORMAT = "%(asctime)s - %(levelname)s - [%(module)s:%(lineno)d] - %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

LOG_DIR = os.environ.get("LOG_DIR", Path(__file__).parent.parent / "logs")


class ColorFormatter(logging.Formatter):
    def format(self, record):
        levelname = record.levelname
        if levelname in LOG_LEVELS:
            record.levelname = f"{LOG_LEVELS[levelname]['color']}{levelname}{Colors.RESET}"
        return super().format(record)


def get_logger(name: str, log_level: str = "INFO", log_file: Optional[str] = None) -> logging.Logger:
    logger = logging.getLogger(name)

    if not logger.handlers:
        level = LOG_LEVELS.get(log_level.upper(), LOG_LEVELS["INFO"])["level"]
        logger.setLevel(level)


        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(ColorFormatter(LOG_FORMAT, datefmt=DATE_FORMAT))
        logger.addHandler(console_handler)


        if log_file:
            log_path = Path(log_file)
            if not log_path.is_absolute():
                log_path = Path(LOG_DIR) / log_file

            log_path.parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(str(log_path))
            file_handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT))
            logger.addHandler(file_handler)

    return logger


def log_task_event(logger: logging.Logger, task_id: str, event: str, details: Dict[str, Any] = None):
    message = f"Task[{task_id}] {event}"
    if details:
        details_str = json.dumps(details, default=str, sort_keys=True)
        message += f" - {details_str}"
    logger.info(message)


app_logger = get_logger("app", log_level="INFO", log_file="app.log")
task_logger = get_logger("task_manager", log_level="DEBUG", log_file="tasks.log")
api_logger = get_logger("api", log_level="INFO", log_file="api.log")