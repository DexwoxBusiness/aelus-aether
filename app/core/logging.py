"""Structured logging configuration using structlog."""

import logging
import random
import sys
from typing import Any

import structlog
from structlog.types import EventDict, Processor


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
        sample_rate_debug: float = 0.01,  # Sample 1% of DEBUG logs
        sample_rate_info: float = 0.1,    # Sample 10% of INFO logs
        sample_rate_warning: float = 1.0,  # Sample 100% of WARNING logs
        sample_rate_error: float = 1.0,    # Sample 100% of ERROR logs
    ):
        """
        Initialize log sampler.
        
        Args:
            sample_rate_debug: Sampling rate for DEBUG logs (0.0 to 1.0)
            sample_rate_info: Sampling rate for INFO logs (0.0 to 1.0)
            sample_rate_warning: Sampling rate for WARNING logs (0.0 to 1.0)
            sample_rate_error: Sampling rate for ERROR logs (0.0 to 1.0)
        """
        self.sample_rates = {
            "debug": sample_rate_debug,
            "info": sample_rate_info,
            "warning": sample_rate_warning,
            "error": sample_rate_error,
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
        
        # Always log if sample rate is 1.0
        if sample_rate >= 1.0:
            return event_dict
        
        # Drop event if random value exceeds sample rate
        if random.random() > sample_rate:
            raise structlog.DropEvent
        
        # Add sampling metadata
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
        'password', 'token', 'secret', 'key', 'authorization', 
        'api_key', 'apikey', 'access_token', 'refresh_token',
        'client_secret', 'private_key', 'jwt', 'bearer'
    }
    
    def _censor_dict(data: dict) -> dict:
        """Recursively censor sensitive keys in dictionaries."""
        censored = {}
        for k, v in data.items():
            if any(sensitive in k.lower() for sensitive in sensitive_keys):
                censored[k] = '***REDACTED***'
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
            event_dict[key] = '***REDACTED***'
        elif isinstance(event_dict[key], dict):
            event_dict[key] = _censor_dict(event_dict[key])
    
    return event_dict


def configure_logging(
    log_level: str = "INFO",
    json_logs: bool = True,
    enable_sampling: bool = False,
) -> None:
    """
    Configure structured logging with structlog.
    
    Sets up JSON logging with request ID propagation, tenant context,
    sensitive data redaction, and optional log sampling.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_logs: Whether to output logs in JSON format (default: True)
        enable_sampling: Enable log sampling for high-volume endpoints (default: False)
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
        processors.append(LogSampler())
    
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


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """
    Get a configured logger instance.
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        Configured structlog logger
    """
    return structlog.get_logger(name)
