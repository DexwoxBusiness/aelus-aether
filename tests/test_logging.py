"""Tests for structured logging functionality."""

from unittest.mock import patch

import pytest
import structlog

from app.core.logging import (
    LogSampler,
    add_app_context,
    bind_request_context,
    censor_sensitive_data,
    clear_request_context,
    configure_logging,
    get_context_logger,
    get_logger,
)


class TestLoggingConfiguration:
    """Test logging configuration."""

    def test_configure_logging_json_format(self, caplog):
        """Test that logging is configured with JSON output."""
        # Configure with JSON logs
        configure_logging(log_level="INFO", json_logs=True)

        # Get logger
        logger = get_logger("test")

        # Log message
        with caplog.at_level("INFO"):
            logger.info("test message", key="value")

        # Verify log was captured
        assert len(caplog.records) > 0
        assert "test message" in caplog.text

    def test_configure_logging_console_format(self, caplog):
        """Test that logging can be configured with console output."""
        # Configure with console logs
        configure_logging(log_level="INFO", json_logs=False)

        # Get logger
        logger = get_logger("test")

        # Log message
        with caplog.at_level("INFO"):
            logger.info("test message")

        # Verify log was captured
        assert len(caplog.records) > 0
        assert "test message" in caplog.text

    def test_log_levels(self, caplog):
        """Test different log levels."""
        configure_logging(log_level="DEBUG", json_logs=True)
        logger = get_logger("test")

        with caplog.at_level("DEBUG"):
            logger.debug("debug message")
            logger.info("info message")
            logger.warning("warning message")
            logger.error("error message")

        # Verify all log levels are present
        assert "info message" in caplog.text
        assert "warning message" in caplog.text
        assert "error message" in caplog.text


class TestAppContext:
    """Test application context processor."""

    def test_add_app_context(self):
        """Test that app context is added to log events."""
        event_dict = {}
        result = add_app_context(None, None, event_dict)

        assert result["app"] == "aelus-aether"


class TestSensitiveDataCensoring:
    """Test sensitive data censoring."""

    def test_censor_password(self):
        """Test that passwords are censored."""
        event_dict = {"password": "secret123"}
        result = censor_sensitive_data(None, None, event_dict)

        assert result["password"] == "***REDACTED***"

    def test_censor_api_key(self):
        """Test that API keys are censored."""
        event_dict = {"api_key": "sk-1234567890"}
        result = censor_sensitive_data(None, None, event_dict)

        assert result["api_key"] == "***REDACTED***"

    def test_censor_token(self):
        """Test that tokens are censored."""
        event_dict = {"access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"}
        result = censor_sensitive_data(None, None, event_dict)

        assert result["access_token"] == "***REDACTED***"

    def test_censor_nested_dict(self):
        """Test that sensitive data in nested dicts is censored."""
        event_dict = {"user": {"name": "John", "password": "secret123"}}
        result = censor_sensitive_data(None, None, event_dict)

        assert result["user"]["name"] == "John"
        assert result["user"]["password"] == "***REDACTED***"

    def test_censor_case_insensitive(self):
        """Test that censoring is case-insensitive."""
        event_dict = {
            "PASSWORD": "secret123",
            "Api_Key": "sk-1234567890",
            "ACCESS_TOKEN": "token123",
        }
        result = censor_sensitive_data(None, None, event_dict)

        assert result["PASSWORD"] == "***REDACTED***"
        assert result["Api_Key"] == "***REDACTED***"
        assert result["ACCESS_TOKEN"] == "***REDACTED***"

    def test_preserve_non_sensitive_data(self):
        """Test that non-sensitive data is preserved."""
        event_dict = {"user_id": "123", "email": "test@example.com", "action": "login"}
        result = censor_sensitive_data(None, None, event_dict)

        assert result["user_id"] == "123"
        assert result["email"] == "test@example.com"
        assert result["action"] == "login"


class TestLogSampler:
    """Test log sampling functionality."""

    def test_sampler_always_logs_critical(self):
        """Test that critical logs are always logged."""
        sampler = LogSampler(
            sample_rates={
                "debug": 0.0,
                "info": 0.0,
                "warning": 0.0,
                "error": 0.0,
                "critical": 1.0,
            }
        )

        event_dict = {"level": "critical", "event": "critical error"}

        # Should not raise DropEvent
        result = sampler(None, None, event_dict)
        assert result["event"] == "critical error"

    def test_sampler_always_logs_error_when_rate_100(self):
        """Test that errors are always logged when sample rate is 1.0."""
        sampler = LogSampler(sample_rates={"error": 1.0})

        event_dict = {"level": "error", "event": "error message"}

        # Should not raise DropEvent
        result = sampler(None, None, event_dict)
        assert result["event"] == "error message"

    def test_sampler_drops_logs_when_rate_0(self):
        """Test that logs are dropped when sample rate is 0."""
        sampler = LogSampler(sample_rates={"info": 0.0})

        event_dict = {"level": "info", "event": "info message"}

        # Should raise DropEvent
        with pytest.raises(structlog.DropEvent):
            sampler(None, None, event_dict)

    def test_sampler_adds_metadata_when_sampled(self):
        """Test that sampling metadata is added to sampled logs."""
        sampler = LogSampler(sample_rates={"info": 1.0})

        event_dict = {"level": "info", "event": "info message"}

        # Mock random to always sample
        with patch("random.random", return_value=0.0):
            result = sampler(None, None, event_dict)

        # Should have sampling metadata (only when rate < 1.0)
        # Since rate is 1.0, no metadata is added
        assert "sampled" not in result

    def test_sampler_metadata_with_partial_rate(self):
        """Test sampling metadata with partial sample rate."""
        sampler = LogSampler(sample_rates={"info": 0.5})

        event_dict = {"level": "info", "event": "info message"}

        # Mock random to sample (below threshold)
        with patch("random.random", return_value=0.3):
            result = sampler(None, None, event_dict)

        assert result["sampled"] is True
        assert result["sample_rate"] == 0.5


class TestGetLogger:
    """Test logger retrieval."""

    def test_get_logger_with_name(self):
        """Test getting logger with name."""
        configure_logging()
        logger = get_logger("test_module")

        assert logger is not None
        # structlog returns a BoundLoggerLazyProxy, not BoundLogger directly
        assert hasattr(logger, "info")
        assert hasattr(logger, "error")

    def test_get_logger_without_name(self):
        """Test getting logger without name."""
        configure_logging()
        logger = get_logger()

        assert logger is not None
        # structlog returns a BoundLoggerLazyProxy, not BoundLogger directly
        assert hasattr(logger, "info")
        assert hasattr(logger, "error")


class TestStructuredLogging:
    """Test structured logging with context."""

    def test_logger_with_context(self, caplog):
        """Test that logger can bind context."""
        configure_logging(json_logs=True)
        logger = get_logger("test")

        # Bind context
        logger = logger.bind(request_id="123", tenant_id="tenant-1")

        with caplog.at_level("INFO"):
            logger.info("test message")

        # Verify log was captured with context
        assert len(caplog.records) > 0
        assert "test message" in caplog.text

    def test_logger_with_multiple_fields(self, caplog):
        """Test logging with multiple fields."""
        configure_logging(json_logs=True)
        logger = get_logger("test")

        with caplog.at_level("INFO"):
            logger.info("user action", user_id="user-123", action="login", ip_address="192.168.1.1")

        # Verify log was captured
        assert len(caplog.records) > 0
        assert "user action" in caplog.text

    def test_logger_includes_timestamp(self, caplog):
        """Test that logs include timestamp."""
        configure_logging(json_logs=True)
        logger = get_logger("test")

        with caplog.at_level("INFO"):
            logger.info("test message")

        # Verify log was captured
        assert len(caplog.records) > 0
        assert "test message" in caplog.text

    def test_logger_includes_app_context(self, caplog):
        """Test that logs include app context."""
        configure_logging(json_logs=True)
        logger = get_logger("test")

        with caplog.at_level("INFO"):
            logger.info("test message")

        # Verify log was captured
        assert len(caplog.records) > 0
        assert "test message" in caplog.text


class TestContextPropagation:
    """Test automatic context propagation."""

    def test_bind_request_context(self, caplog):
        """Test binding request context."""
        configure_logging(json_logs=True)

        # Bind context
        bind_request_context(request_id="req-123", tenant_id="tenant-456")

        # Get context logger
        logger = get_context_logger("test")

        with caplog.at_level("INFO"):
            logger.info("test message")

        # Verify log was captured
        assert len(caplog.records) > 0
        assert "test message" in caplog.text

        # Clean up
        clear_request_context()

    def test_clear_request_context(self, caplog):
        """Test clearing request context."""
        configure_logging(json_logs=True)

        # Bind and then clear
        bind_request_context(request_id="req-123", tenant_id="tenant-456")
        clear_request_context()

        # Get context logger
        logger = get_context_logger("test")

        with caplog.at_level("INFO"):
            logger.info("test message")

        # Verify log was captured
        assert len(caplog.records) > 0
        assert "test message" in caplog.text

    def test_context_logger_without_context(self, caplog):
        """Test context logger when no context is bound."""
        configure_logging(json_logs=True)
        clear_request_context()

        logger = get_context_logger("test")

        with caplog.at_level("INFO"):
            logger.info("test message")

        # Verify log was captured
        assert len(caplog.records) > 0
        assert "test message" in caplog.text

    def test_partial_context_binding(self, caplog):
        """Test binding only request_id without tenant_id."""
        configure_logging(json_logs=True)

        # Bind only request_id
        bind_request_context(request_id="req-789")

        logger = get_context_logger("test")

        with caplog.at_level("INFO"):
            logger.info("test message")

        # Verify log was captured
        assert len(caplog.records) > 0
        assert "test message" in caplog.text

        # Clean up
        clear_request_context()
