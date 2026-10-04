import json
import logging
import re
import sys
from typing import Any, Dict

from app.core.config import settings

# Sensitive token redaction regex patterns
REDACT_PATTERNS = [
    (re.compile(r"Bearer\s+([A-Za-z0-9_\-\.]+)", re.IGNORECASE), "Bearer [REDACTED]"),
    (re.compile(r"(password|token|secret|api_key|apiKey)\s*[:=]\s*['\"]?([^'\"\s,]+)['\"]?", re.IGNORECASE), r"\1=[REDACTED]"),
]


def redact_sensitive_info(message: str) -> str:
    """Sanitizes sensitive tokens, passwords, and API credentials from log messages."""
    sanitized = str(message)
    for pattern, replacement in REDACT_PATTERNS:
        sanitized = pattern.sub(replacement, sanitized)
    return sanitized


class StructuredJsonFormatter(logging.Formatter):
    """
    Production JSON structured log formatter.
    Emits single-line RFC 8259 JSON objects suitable for ingestion by Datadog,
    CloudWatch, GCP Cloud Logging, Grafana Loki, or ELK Stack.
    """

    def format(self, record: logging.LogRecord) -> str:
        raw_message = record.getMessage()
        safe_message = redact_sensitive_info(raw_message)

        log_data: Dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt or "%Y-%m-%dT%H:%M:%SZ"),
            "level": record.levelname,
            "service": "ada-backend",
            "environment": settings.ENVIRONMENT,
            "logger": record.name,
            "message": safe_message,
        }

        # Include request_id if available on the record
        if hasattr(record, "request_id"):
            log_data["request_id"] = getattr(record, "request_id")

        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data)


class DevConsoleFormatter(logging.Formatter):
    """Clean, readable log formatter for local development console."""

    def format(self, record: logging.LogRecord) -> str:
        timestamp = self.formatTime(record, self.datefmt or "%H:%M:%S")
        safe_message = redact_sensitive_info(record.getMessage())
        base = f"[{timestamp}] {record.levelname:<7} in {record.name}: {safe_message}"
        if record.exc_info:
            base += "\n" + self.formatException(record.exc_info)
        return base


def setup_logging() -> None:
    """
    Initializes global system logging interceptors, attaching a structured stream
    handler to the root logger and aligning log levels.
    """
    root_logger = logging.getLogger()

    # Avoid duplicate handlers if setup runs multiple times
    if root_logger.hasHandlers():
        root_logger.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    if getattr(settings, "JSON_LOGGING", False):
        formatter = StructuredJsonFormatter(datefmt="%Y-%m-%dT%H:%M:%SZ")
    else:
        formatter = DevConsoleFormatter(datefmt="%Y-%m-%d %H:%M:%S")

    handler.setFormatter(formatter)
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO)

    # Silence overly verbose external dependencies
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

