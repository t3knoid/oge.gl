from __future__ import annotations

from contextvars import ContextVar, Token
from datetime import UTC, datetime
import json
import logging
from pathlib import Path
import sys
from typing import Any
from typing import TextIO


_REQUEST_ID: ContextVar[str | None] = ContextVar("request_id", default=None)


_RESERVED_LOG_RECORD_FIELDS = {
    "args",
    "asctime",
    "created",
    "exc_info",
    "exc_text",
    "filename",
    "funcName",
    "levelname",
    "levelno",
    "lineno",
    "module",
    "msecs",
    "message",
    "msg",
    "name",
    "pathname",
    "process",
    "processName",
    "relativeCreated",
    "stack_info",
    "thread",
    "threadName",
    "taskName",
}


class RequestContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        request_id = _REQUEST_ID.get()
        if request_id is not None and not hasattr(record, "request_id"):
            record.request_id = request_id
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "event": record.getMessage(),
            "message": record.getMessage(),
        }

        for key, value in record.__dict__.items():
            if key in _RESERVED_LOG_RECORD_FIELDS:
                continue
            payload[key] = value

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, default=str)


class TextFormatter(logging.Formatter):
    def __init__(self) -> None:
        super().__init__(
            fmt="%(asctime)s %(levelname)s %(name)s %(message)s %(request_id)s",
            datefmt="%Y-%m-%dT%H:%M:%S%z",
        )

    def format(self, record: logging.LogRecord) -> str:
        if not hasattr(record, "request_id"):
            record.request_id = "-"
        return super().format(record)


def set_request_id(request_id: str) -> Token[str | None]:
    return _REQUEST_ID.set(request_id)


def reset_request_id(token: Token[str | None]) -> None:
    _REQUEST_ID.reset(token)


def _resolve_log_format(*, log_format: str, runtime_environment: str) -> str:
    if log_format != "auto":
        return log_format
    if runtime_environment == "local":
        return "text"
    return "json"


def _build_formatter(resolved_log_format: str) -> logging.Formatter:
    if resolved_log_format == "text":
        return TextFormatter()
    return JsonFormatter()


def _build_file_handler(log_file_path: str, formatter: logging.Formatter) -> logging.Handler:
    requested_path = Path(log_file_path)
    fallback_path = Path("/tmp/oge.gl/backend.log")
    candidate_paths = [requested_path]
    if fallback_path != requested_path:
        candidate_paths.append(fallback_path)

    for path in candidate_paths:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            handler = logging.FileHandler(path)
            handler.addFilter(RequestContextFilter())
            handler.setFormatter(formatter)
            return handler
        except OSError:
            continue

    raise RuntimeError("Unable to initialize local file logging handler")


def configure_logging(
    *,
    level: str,
    log_format: str,
    runtime_environment: str,
    log_file_path: str,
    stream: TextIO | None = None,
) -> None:
    normalized_level = level.upper()
    resolved_log_format = _resolve_log_format(log_format=log_format, runtime_environment=runtime_environment)
    formatter = _build_formatter(resolved_log_format)

    handler = logging.StreamHandler(stream=stream if stream is not None else sys.__stderr__)
    handler.addFilter(RequestContextFilter())
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(normalized_level)
    root.addHandler(handler)

    if runtime_environment == "local":
        file_handler = _build_file_handler(log_file_path, formatter)
        root.addHandler(file_handler)

    # Route uvicorn logs through the same handler for a consistent output format.
    for logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        uvicorn_logger = logging.getLogger(logger_name)
        uvicorn_logger.handlers.clear()
        uvicorn_logger.propagate = True
        uvicorn_logger.setLevel(normalized_level)
