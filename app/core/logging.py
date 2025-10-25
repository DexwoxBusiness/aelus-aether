"""Structured logging configuration using structlog."""

import logging
import random
import sys
from contextvars import ContextVar
from typing import Any, Literal, cast

import structlog
from structlog.types import EventDict, Processor

# Type alias for log levels
LogLevelType = Literal["debug", "info", "warning", "error", "critical"]

# Context variables for request-scoped data
_request_id: ContextVar[str | None] = ContextVar("request_id", default=None)
_tenant_id: ContextVar[str | None] = ContextVar("tenant_id", default=None)
_request_path: ContextVar[str | None] = ContextVar("request_path", default=None)


def add_app_context(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
    """
    Add application context to log events.

    Args:
        logger: Logger instance
        method_name: Method name being called
        event_dict: Event dictionary

    Returns:
        Updated event dictionary with app context
    """
    event_dict["app"] = "aelus-aether"
    return event_dict


class LogSampler:
    """
    Log sampling processor to reduce log volume for high-traffic endpoints.

    Samples logs based on configurable sample rates for different log levels.
    """

    def __init__(
        self,
        sample_rates: dict[LogLevelType, float] | None = None,
    ):
        """
        Initialize log sampler.

        Args:
            sample_rates: Dictionary mapping log levels to sample rates (0.0 to 1.0).
                         If None, uses default rates.
        """
        self.sample_rates = sample_rates or {
            "debug": 0.1,  # Development-friendly default
            "info": 0.2,  # Development-friendly default
            "warning": 1.0,
            "error": 1.0,
            "critical": 1.0,  # Always log critical
        }

    def __call__(self, logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
        """
        Sample log events based on log level.

        Args:
            logger: Logger instance
            method_name: Method name being called
            event_dict: Event dictionary

        Returns:
            Event dictionary or raises DropEvent to skip logging
        """
        level = event_dict.get("level", "info").lower()
        sample_rate = self.sample_rates.get(level, 1.0)

        # Always log if sample rate is 1.0 or higher
        if sample_rate >= 1.0:
            return event_dict

        # Drop event if random value exceeds sample rate
        if random.random() > sample_rate:
            raise structlog.DropEvent

        # Only add metadata when sampling actually occurred (rate < 1.0)
        if sample_rate < 1.0:
            event_dict["sampled"] = True
            event_dict["sample_rate"] = sample_rate

        return event_dict


def censor_sensitive_data(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
    """
    Censor sensitive data in log events.

    Redacts common sensitive field names like passwords, tokens, API keys, etc.

    Args:
        logger: Logger instance
        method_name: Method name being called
        event_dict: Event dictionary

    Returns:
        Updated event dictionary with censored data
    """
    sensitive_keys = {
        "password",
        "token",
        "secret",
        "key",
        "authorization",
        "api_key",
        "apikey",
        "access_token",
        "refresh_token",
        "client_secret",
        "private_key",
        "jwt",
        "bearer",
    }

    def _censor_dict(data: dict[str, Any]) -> dict[str, Any]:
        """Recursively censor sensitive keys in dictionaries."""
        censored: dict[str, Any] = {}
        for k, v in data.items():
            if any(sensitive in k.lower() for sensitive in sensitive_keys):
                censored[k] = "***REDACTED***"
            elif isinstance(v, dict):
                censored[k] = _censor_dict(v)
            elif isinstance(v, list):
                censored[k] = [_censor_dict(item) if isinstance(item, dict) else item for item in v]
            else:
                censored[k] = v
        return censored

    # Censor the event_dict itself
    for key in list(event_dict.keys()):
        if any(sensitive in key.lower() for sensitive in sensitive_keys):
            event_dict[key] = "***REDACTED***"
        elif isinstance(event_dict[key], dict):
            event_dict[key] = _censor_dict(event_dict[key])

    return event_dict


def configure_logging(
    log_level: str = "INFO",
    json_logs: bool = True,
    enable_sampling: bool = False,
    sample_rates: dict[LogLevelType, float] | None = None,
) -> None:
    """
    Configure structured logging with structlog.

    Sets up JSON logging with request ID propagation, tenant context,
    sensitive data redaction, and optional log sampling.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_logs: Whether to output logs in JSON format (default: True)
        enable_sampling: Enable log sampling for high-volume endpoints (default: False)
        sample_rates: Custom sample rates per log level (default: None, uses built-in defaults)
    """
    # Convert log level string to logging constant
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=numeric_level,
    )

    # Build processor chain
    processors: list[Processor] = [
        # Add log level
        structlog.stdlib.add_log_level,
        # Add logger name
        structlog.stdlib.add_logger_name,
        # Add timestamp
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        # Add application context
        add_app_context,
        # Stack info for exceptions
        structlog.processors.StackInfoRenderer(),
        # Format exceptions
        structlog.processors.format_exc_info,
        # Censor sensitive data
        censor_sensitive_data,
    ]

    # Add log sampling if enabled (for high-volume production environments)
    if enable_sampling:
        processors.append(LogSampler(sample_rates=sample_rates))

    # Unwrap event dict
    processors.append(structlog.processors.UnicodeDecoder())

    # Add JSON renderer or console renderer based on configuration
    if json_logs:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def bind_request_context(
    request_id: str | None = None,
    tenant_id: str | None = None,
    request_path: str | None = None,
) -> None:
    """
    Bind request context to current context variables.

    This should be called by middleware to set request-scoped context
    that will be automatically included in all logs.

    Args:
        request_id: Request ID to bind
        tenant_id: Tenant ID to bind
        request_path: Request path to bind (for security auditing)
    """
    if request_id:
        _request_id.set(request_id)
    if tenant_id:
        _tenant_id.set(tenant_id)
    if request_path:
        _request_path.set(request_path)


def clear_request_context() -> None:
    """Clear request context variables."""
    _request_id.set(None)
    _tenant_id.set(None)
    _request_path.set(None)


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """
    Get a configured logger instance.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Configured structlog logger
    """
    return cast(structlog.stdlib.BoundLogger, structlog.get_logger(name))


def get_context_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """
    Get logger with current request context automatically bound.

    This is the recommended way to get a logger in route handlers and
    application code, as it automatically includes request_id and tenant_id
    from the current request context without manual binding.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Configured structlog logger with request context bound

    Example:
        ```python
        from app.core.logging import get_context_logger

        logger = get_context_logger(__name__)
        logger.info("Processing request")  # Automatically includes request_id and tenant_id
        ```
    """
    logger = cast(structlog.stdlib.BoundLogger, structlog.get_logger(name))

    # Get current context values with defensive error handling
    # Handle each context var separately to avoid masking issues
    request_id = None
    tenant_id = None

    try:
        request_id = _request_id.get()
    except LookupError:
        # Context var not properly initialized (e.g., outside request context)
        pass

    try:
        tenant_id = _tenant_id.get()
    except LookupError:
        # Context var not properly initialized (e.g., outside request context)
        pass

    # Only bind if context variables are present and not None
    context_vars = {}
    if request_id is not None:
        context_vars["request_id"] = request_id
    if tenant_id is not None:
        context_vars["tenant_id"] = tenant_id

    if context_vars:
        bound = logger.bind(**context_vars)
        return cast(structlog.stdlib.BoundLogger, bound)

    return logger
