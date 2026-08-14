"""Application logging to logs/application.log."""

from __future__ import annotations

import logging
import os
import traceback
from typing import Optional

_LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
_LOG_PATH = os.path.join(_LOG_DIR, "application.log")
_LOGGER: Optional[logging.Logger] = None


def get_logger() -> logging.Logger:
    global _LOGGER
    if _LOGGER is not None:
        return _LOGGER

    os.makedirs(_LOG_DIR, exist_ok=True)
    logger = logging.getLogger("water_demand_app")
    logger.setLevel(logging.DEBUG)
    if not logger.handlers:
        handler = logging.FileHandler(_LOG_PATH, encoding="utf-8")
        handler.setFormatter(
            logging.Formatter("%(asctime)s | %(levelname)s | %(funcName)s | %(message)s")
        )
        logger.addHandler(handler)
    _LOGGER = logger
    return logger


def log_exception(
    message: str,
    *,
    exc: Optional[BaseException] = None,
    project_id: str = "",
    function: str = "",
) -> None:
    logger = get_logger()
    parts = [message]
    if project_id:
        parts.append(f"project_id={project_id}")
    if function:
        parts.append(f"function={function}")
    text = " | ".join(parts)
    if exc is not None:
        logger.error("%s\n%s", text, "".join(traceback.format_exception(type(exc), exc, exc.__traceback__)))
    else:
        logger.error(text)
