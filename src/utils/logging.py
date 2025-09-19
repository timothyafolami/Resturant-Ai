from loguru import logger
from pathlib import Path
from typing import Optional
import os
import sys

_CONFIGURED = False
_SINKS_ADDED = False
_DEFAULT_PATH = "logs/ai_agent.log"


def _ensure_logs_dir(path: str) -> None:
    p = Path(path).parent
    p.mkdir(parents=True, exist_ok=True)


def setup_logger(log_path: str = _DEFAULT_PATH):
    global _CONFIGURED
    if _CONFIGURED:
        return logger

    _ensure_logs_dir(log_path)
    logger.remove()
    logger.add(
        log_path,
        rotation="10 MB",
        retention="7 days",
        level="DEBUG",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} | {message}",
    )
    # Optional console logging (disabled by default). Enable by setting AI_CONSOLE_LOGS=1
    if str(os.getenv("AI_CONSOLE_LOGS", "")).lower() in {"1", "true", "yes", "on"}:
        logger.add(
            sys.stderr,
            level="INFO",
            format="🤖 {time:HH:mm:ss} | {level} | {message}",
        )
    _CONFIGURED = True
    return logger


def _ensure_chat_sinks() -> None:
    global _SINKS_ADDED
    if _SINKS_ADDED:
        return
    # Add context-filtered sinks for internal and external
    def _filter_internal(record):
        return record["extra"].get("context") == "internal"

    def _filter_external(record):
        return record["extra"].get("context") == "external"

    _ensure_logs_dir("logs/internal_chat.log")
    _ensure_logs_dir("logs/external_chat.log")
    logger.add(
        "logs/internal_chat.log",
        rotation="10 MB",
        retention="7 days",
        level="DEBUG",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
        filter=_filter_internal,
    )
    logger.add(
        "logs/external_chat.log",
        rotation="10 MB",
        retention="7 days",
        level="DEBUG",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
        filter=_filter_external,
    )
    _SINKS_ADDED = True


def get_context_logger(context: str = "internal"):
    setup_logger()
    _ensure_chat_sinks()
    return logger.bind(context=context)
