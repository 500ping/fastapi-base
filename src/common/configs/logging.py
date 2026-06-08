import logging
import sys
import uuid
from contextvars import ContextVar
from typing import Any, Optional

import structlog

from src.common.configs.settings import get_settings

# Context variable to store request ID across the request lifecycle
request_id_context: ContextVar[Optional[str]] = ContextVar("request_id", default=None)


def add_request_id(_logger: Any, _method_name: str, event_dict: dict) -> dict:
    """Inject the current request ID (or ``-``) into every log record.

    Uses ``setdefault`` so an explicitly bound ``request_id`` (e.g. from a
    background task running after the request context is gone) is preserved.
    """
    event_dict.setdefault("request_id", get_request_id() or "-")
    return event_dict


def setup_logging() -> None:
    """
    Setup application logging configuration.

    This function:
    1. Configures structlog to emit JSON log lines
    2. Configures log level based on settings.debug
    3. Routes standard library logging (uvicorn, fastapi, ...) through the
       same JSON renderer so every log line shares one structured format
    """
    settings = get_settings()

    # Determine log level based on debug setting
    log_level = logging.DEBUG if settings.debug else logging.INFO

    # Processors shared between structlog-native and stdlib ("foreign") records,
    # so uvicorn/fastapi logs render with the same JSON fields as app logs.
    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        add_request_id,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.CallsiteParameterAdder(
            {
                structlog.processors.CallsiteParameter.FUNC_NAME,
                structlog.processors.CallsiteParameter.LINENO,
            }
        ),
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    structlog.configure(
        processors=shared_processors
        + [structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            # Rename "event" -> "message" and "func_name" -> "function".
            structlog.processors.EventRenamer("message"),
            _rename_callsite_keys,
            structlog.processors.JSONRenderer(),
        ],
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers = [handler]
    root_logger.setLevel(log_level)

    # Set levels for specific loggers to reduce noise
    for noisy_logger in ("uvicorn", "uvicorn.error", "uvicorn.access", "fastapi"):
        logging.getLogger(noisy_logger).setLevel(logging.WARNING)


def _rename_callsite_keys(_logger: Any, _method_name: str, event_dict: dict) -> dict:
    """Give callsite fields friendlier JSON names."""
    if "func_name" in event_dict:
        event_dict["function"] = event_dict.pop("func_name")
    if "lineno" in event_dict:
        event_dict["line"] = event_dict.pop("lineno")
    return event_dict


def get_logger(name: str) -> Any:
    """
    Get a logger instance for a specific module.

    Args:
        name: Usually __name__ of the calling module

    Returns:
        Structlog logger bound to the given name
    """
    return structlog.get_logger(name)


def set_request_id() -> None:
    """
    Set a new request ID in the current context.
    """
    request_id = str(uuid.uuid4())[:8]
    request_id_context.set(request_id)


def get_request_id() -> Optional[str]:
    """
    Get the current request ID from context.

    Returns:
        The current request ID or None if not set
    """
    return request_id_context.get()
