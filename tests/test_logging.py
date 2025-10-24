"""Tests for structured logging functionality."""

import json
import logging
from io import StringIO
from unittest.mock import patch

import pytest
import structlog

from app.core.logging import (
    add_app_context,
    censor_sensitive_data,
    configure_logging,
    get_logger,
    LogSampler,
)


class TestLoggingConfiguration:
    """Test logging configuration."""
    
    def test_configure_logging_json_format(self):
        """Test that logging is configured with JSON output."""
        # Configure with JSON logs
        configure_logging(log_level="INFO", json_logs=True)
        
        # Get logger
        logger = get_logger("test")
        
        # Capture output
        with patch("sys.stdout", new=StringIO()) as mock_stdout:
            logger.info("test message", key="value")
            output = mock_stdout.getvalue()
        
        # Verify JSON format
        log_entry = json.loads(output)
        assert log_entry["event"] == "test message"
        assert log_entry["key"] == "value"
        assert "timestamp" in log_entry
        assert "level" in log_entry
    
    def test_configure_logging_console_format(self):
        """Test that logging can be configured with console output."""
        # Configure with console logs
        configure_logging(log_level="INFO", json_logs=False)
        
        # Get logger
        logger = get_logger("test")
        
        # Capture output
        with patch("sys.stdout", new=StringIO()) as mock_stdout:
            logger.info("test message")
            output = mock_stdout.getvalue()
        
        # Verify console format (not JSON)
        assert "test message" in output
        with pytest.raises(json.JSONDecodeError):
            json.loads(output)
    
    def test_log_levels(self):
        """Test different log levels."""
        configure_logging(log_level="DEBUG", json_logs=True)
        logger = get_logger("test")
        
        with patch("sys.stdout", new=StringIO()) as mock_stdout:
            logger.debug("debug message")
            logger.info("info message")
            logger.warning("warning message")
            logger.error("error message")
            
            output = mock_stdout.getvalue()
        
        # Verify all log levels are present
        assert "debug message" in output
        assert "info message" in output
        assert "warning message" in output
        assert "error message" in output


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
        event_dict = {
            "user": {
                "name": "John",
                "password": "secret123"
            }
        }
        result = censor_sensitive_data(None, None, event_dict)
        
        assert result["user"]["name"] == "John"
        assert result["user"]["password"] == "***REDACTED***"
    
    def test_censor_case_insensitive(self):
        """Test that censoring is case-insensitive."""
        event_dict = {
            "PASSWORD": "secret123",
            "Api_Key": "sk-1234567890",
            "ACCESS_TOKEN": "token123"
        }
        result = censor_sensitive_data(None, None, event_dict)
        
        assert result["PASSWORD"] == "***REDACTED***"
        assert result["Api_Key"] == "***REDACTED***"
        assert result["ACCESS_TOKEN"] == "***REDACTED***"
    
    def test_preserve_non_sensitive_data(self):
        """Test that non-sensitive data is preserved."""
        event_dict = {
            "user_id": "123",
            "email": "test@example.com",
            "action": "login"
        }
        result = censor_sensitive_data(None, None, event_dict)
        
        assert result["user_id"] == "123"
        assert result["email"] == "test@example.com"
        assert result["action"] == "login"


class TestLogSampler:
    """Test log sampling functionality."""
    
    def test_sampler_always_logs_critical(self):
        """Test that critical logs are always logged."""
        sampler = LogSampler(
            sample_rate_debug=0.0,
            sample_rate_info=0.0,
            sample_rate_warning=0.0,
            sample_rate_error=0.0,
        )
        
        event_dict = {"level": "critical", "event": "critical error"}
        
        # Should not raise DropEvent
        result = sampler(None, None, event_dict)
        assert result["event"] == "critical error"
    
    def test_sampler_always_logs_error_when_rate_100(self):
        """Test that errors are always logged when sample rate is 1.0."""
        sampler = LogSampler(sample_rate_error=1.0)
        
        event_dict = {"level": "error", "event": "error message"}
        
        # Should not raise DropEvent
        result = sampler(None, None, event_dict)
        assert result["event"] == "error message"
    
    def test_sampler_drops_logs_when_rate_0(self):
        """Test that logs are dropped when sample rate is 0."""
        sampler = LogSampler(sample_rate_info=0.0)
        
        event_dict = {"level": "info", "event": "info message"}
        
        # Should raise DropEvent
        with pytest.raises(structlog.DropEvent):
            sampler(None, None, event_dict)
    
    def test_sampler_adds_metadata_when_sampled(self):
        """Test that sampling metadata is added to sampled logs."""
        sampler = LogSampler(sample_rate_info=1.0)
        
        event_dict = {"level": "info", "event": "info message"}
        
        # Mock random to always sample
        with patch("random.random", return_value=0.0):
            result = sampler(None, None, event_dict)
        
        # Should have sampling metadata (only when rate < 1.0)
        # Since rate is 1.0, no metadata is added
        assert "sampled" not in result
    
    def test_sampler_metadata_with_partial_rate(self):
        """Test sampling metadata with partial sample rate."""
        sampler = LogSampler(sample_rate_info=0.5)
        
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
        assert isinstance(logger, structlog.stdlib.BoundLogger)
    
    def test_get_logger_without_name(self):
        """Test getting logger without name."""
        configure_logging()
        logger = get_logger()
        
        assert logger is not None
        assert isinstance(logger, structlog.stdlib.BoundLogger)


class TestStructuredLogging:
    """Test structured logging with context."""
    
    def test_logger_with_context(self):
        """Test that logger can bind context."""
        configure_logging(json_logs=True)
        logger = get_logger("test")
        
        # Bind context
        logger = logger.bind(request_id="123", tenant_id="tenant-1")
        
        with patch("sys.stdout", new=StringIO()) as mock_stdout:
            logger.info("test message")
            output = mock_stdout.getvalue()
        
        log_entry = json.loads(output)
        assert log_entry["request_id"] == "123"
        assert log_entry["tenant_id"] == "tenant-1"
    
    def test_logger_with_multiple_fields(self):
        """Test logging with multiple fields."""
        configure_logging(json_logs=True)
        logger = get_logger("test")
        
        with patch("sys.stdout", new=StringIO()) as mock_stdout:
            logger.info(
                "user action",
                user_id="user-123",
                action="login",
                ip_address="192.168.1.1"
            )
            output = mock_stdout.getvalue()
        
        log_entry = json.loads(output)
        assert log_entry["event"] == "user action"
        assert log_entry["user_id"] == "user-123"
        assert log_entry["action"] == "login"
        assert log_entry["ip_address"] == "192.168.1.1"
    
    def test_logger_includes_timestamp(self):
        """Test that logs include timestamp."""
        configure_logging(json_logs=True)
        logger = get_logger("test")
        
        with patch("sys.stdout", new=StringIO()) as mock_stdout:
            logger.info("test message")
            output = mock_stdout.getvalue()
        
        log_entry = json.loads(output)
        assert "timestamp" in log_entry
        # Verify ISO format
        assert "T" in log_entry["timestamp"]
        assert "Z" in log_entry["timestamp"]
    
    def test_logger_includes_app_context(self):
        """Test that logs include app context."""
        configure_logging(json_logs=True)
        logger = get_logger("test")
        
        with patch("sys.stdout", new=StringIO()) as mock_stdout:
            logger.info("test message")
            output = mock_stdout.getvalue()
        
        log_entry = json.loads(output)
        assert log_entry["app"] == "aelus-aether"
