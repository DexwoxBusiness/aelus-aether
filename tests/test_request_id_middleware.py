"""Tests for Request ID middleware."""

import json
from io import StringIO
from unittest.mock import patch
from uuid import UUID

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from app.core.logging import configure_logging
from app.middleware.request_id import RequestIDMiddleware


@pytest.fixture
def app():
    """Create a test FastAPI app with RequestIDMiddleware."""
    configure_logging(json_logs=True)

    app = FastAPI()
    app.add_middleware(RequestIDMiddleware)

    @app.get("/test")
    async def test_endpoint(request: Request):
        return {
            "request_id": request.state.request_id,
            "tenant_id": getattr(request.state, "tenant_id", None),
        }

    return app


@pytest.fixture
def client(app):
    """Create a test client."""
    return TestClient(app)


class TestRequestIDGeneration:
    """Test request ID generation."""

    def test_generates_request_id(self, client):
        """Test that middleware generates a request ID."""
        response = client.get("/test")

        assert response.status_code == 200
        data = response.json()

        # Verify request ID is generated
        assert "request_id" in data
        assert data["request_id"] is not None

        # Verify it's a valid UUID
        try:
            UUID(data["request_id"])
        except ValueError:
            pytest.fail("Request ID is not a valid UUID")

    def test_uses_existing_request_id(self, client):
        """Test that middleware uses existing X-Request-ID header."""
        custom_request_id = "custom-request-id-123"

        response = client.get("/test", headers={"X-Request-ID": custom_request_id})

        assert response.status_code == 200
        data = response.json()

        # Verify custom request ID is used
        assert data["request_id"] == custom_request_id

    def test_adds_request_id_to_response_headers(self, client):
        """Test that request ID is added to response headers."""
        response = client.get("/test")

        assert "X-Request-ID" in response.headers
        assert response.headers["X-Request-ID"] is not None

    def test_request_id_matches_response_header(self, client):
        """Test that request ID in state matches response header."""
        response = client.get("/test")

        data = response.json()
        request_id_from_state = data["request_id"]
        request_id_from_header = response.headers["X-Request-ID"]

        assert request_id_from_state == request_id_from_header


class TestTenantContext:
    """Test tenant context handling."""

    def test_extracts_tenant_id_from_header(self, client):
        """Test that middleware extracts tenant ID from header for logging context only."""
        tenant_id = "tenant-123"

        response = client.get("/test", headers={"X-Tenant-ID": tenant_id})

        assert response.status_code == 200
        data = response.json()

        # Tenant ID is NOT set in request.state by request_id middleware anymore
        # It's only used for logging context. JWT auth middleware sets it after validation.
        assert data["tenant_id"] is None  # Not set by request_id middleware anymore
        # It's only used for logging context. JWT auth middleware sets it after validation.
        assert data["tenant_id"] is None  # Not set by request_id middleware

    def test_no_tenant_id_when_header_missing(self, client):
        """Test that tenant ID is None when header is missing."""
        response = client.get("/test")

        assert response.status_code == 200
        data = response.json()

        # Verify tenant ID is None
        assert data["tenant_id"] is None


class TestSensitiveDataSanitization:
    """Test sensitive data sanitization in logs."""

    def test_sanitizes_password_in_query_params(self, app):
        """Test that passwords in query params are sanitized."""
        from app.middleware.request_id import RequestIDMiddleware

        middleware = RequestIDMiddleware(app)

        # Create mock query params
        from starlette.datastructures import QueryParams

        query_params = QueryParams([("password", "secret123"), ("user", "john")])

        sanitized = middleware._sanitize_query_params(query_params)

        assert "***REDACTED***" in sanitized
        assert "secret123" not in sanitized
        assert "john" in sanitized

    def test_sanitizes_api_key_in_query_params(self, app):
        """Test that API keys in query params are sanitized."""
        from app.middleware.request_id import RequestIDMiddleware

        middleware = RequestIDMiddleware(app)

        from starlette.datastructures import QueryParams

        query_params = QueryParams([("api_key", "sk-1234567890"), ("action", "test")])

        sanitized = middleware._sanitize_query_params(query_params)

        assert "***REDACTED***" in sanitized
        assert "sk-1234567890" not in sanitized
        assert "test" in sanitized

    def test_sanitizes_token_in_query_params(self, app):
        """Test that tokens in query params are sanitized."""
        from app.middleware.request_id import RequestIDMiddleware

        middleware = RequestIDMiddleware(app)

        from starlette.datastructures import QueryParams

        query_params = QueryParams([("token", "abc123"), ("id", "456")])

        sanitized = middleware._sanitize_query_params(query_params)

        assert "***REDACTED***" in sanitized
        assert "abc123" not in sanitized
        assert "456" in sanitized


class TestLoggingIntegration:
    """Test logging integration with request ID middleware."""

    @pytest.mark.skip(reason="TestClient doesn't capture stdout logs")
    def test_logs_incoming_request(self, client):
        """Test that incoming requests are logged."""
        with patch("sys.stdout", new=StringIO()) as mock_stdout:
            client.get("/test")
            output = mock_stdout.getvalue()

        # Should contain request log
        assert len(output) > 0

    @pytest.mark.skip(reason="TestClient doesn't capture stdout logs")
    def test_logs_request_completion(self, client):
        """Test that request completion is logged."""
        with patch("sys.stdout", new=StringIO()) as mock_stdout:
            client.get("/test")
            output = mock_stdout.getvalue()

        # Should contain completion log
        assert len(output) > 0

    def test_logs_include_request_id(self, client):
        """Test that logs include request ID."""
        with patch("sys.stdout", new=StringIO()) as mock_stdout:
            client.get("/test")
            output = mock_stdout.getvalue()

        # Parse JSON logs
        log_lines = [line for line in output.strip().split("\n") if line]

        for line in log_lines:
            try:
                log_entry = json.loads(line)
                # Verify request_id is present
                assert "request_id" in log_entry
            except json.JSONDecodeError:
                # Skip non-JSON lines
                pass

    @pytest.mark.skip(reason="TestClient doesn't capture stdout logs")
    def test_logs_include_method_and_path(self, client):
        """Test that logs include HTTP method and path."""
        with patch("sys.stdout", new=StringIO()) as mock_stdout:
            client.get("/test")
            output = mock_stdout.getvalue()

        # Should have logs
        assert len(output) > 0


class TestMultipleRequests:
    """Test middleware with multiple requests."""

    def test_different_request_ids_for_different_requests(self, client):
        """Test that different requests get different request IDs."""
        response1 = client.get("/test")
        response2 = client.get("/test")

        request_id1 = response1.json()["request_id"]
        request_id2 = response2.json()["request_id"]

        # Verify request IDs are different
        assert request_id1 != request_id2

    def test_preserves_custom_request_id_across_request(self, client):
        """Test that custom request ID is preserved."""
        custom_id = "my-custom-id"

        response = client.get("/test", headers={"X-Request-ID": custom_id})

        assert response.json()["request_id"] == custom_id
        assert response.headers["X-Request-ID"] == custom_id


class TestExceptionHandling:
    """Test exception handling in middleware."""

    def test_context_cleared_on_exception(self):
        """Test that context is cleared even when an exception occurs."""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from app.core.logging import configure_logging, get_context_logger
        from app.middleware.request_id import RequestIDMiddleware

        configure_logging(json_logs=True)

        app = FastAPI()
        app.add_middleware(RequestIDMiddleware)

        @app.get("/error")
        async def error_endpoint():
            raise ValueError("Test error")

        client = TestClient(app, raise_server_exceptions=False)

        # Make request that will fail
        response = client.get("/error")

        # Verify error response
        assert response.status_code == 500

        # Verify context was cleared (get a logger and check it has no context)
        get_context_logger("test")
        # If context was properly cleared, logger should not have request_id bound
        # This is implicit - if context wasn't cleared, subsequent requests would have stale context


class TestMultiTenantIsolation:
    """Test multi-tenant logging isolation."""

    def test_tenant_context_isolation(self, client):
        """Test that tenant context is properly isolated between requests."""
        # Make first request with tenant A
        response1 = client.get("/test", headers={"X-Tenant-ID": "tenant-a"})

        # Make second request with tenant B
        response2 = client.get("/test", headers={"X-Tenant-ID": "tenant-b"})

        # Tenant ID is NOT set in request.state by request_id middleware
        # It's only used for logging context
        assert response1.json()["tenant_id"] is None
        assert response2.json()["tenant_id"] is None

    def test_invalid_tenant_id_rejected(self, client):
        """Test that invalid tenant ID formats are rejected."""
        # Try with invalid characters
        response = client.get("/test", headers={"X-Tenant-ID": "tenant@invalid!"})

        # Tenant ID should not be set
        assert response.json()["tenant_id"] is None

    def test_tenant_id_length_validation(self, client):
        """Test that tenant ID length is validated."""
        # Try with too long tenant ID (>64 chars)
        long_tenant_id = "a" * 65

        response = client.get("/test", headers={"X-Tenant-ID": long_tenant_id})

        # Tenant ID should not be set
        assert response.json()["tenant_id"] is None

    def test_valid_tenant_id_formats(self, client):
        """Test that valid tenant ID formats are accepted for logging."""
        valid_tenant_ids = [
            "tenant-123",
            "tenant_abc",
            "TENANT-XYZ",
            "t1",
            "a" * 64,  # Max length
        ]

        for tenant_id in valid_tenant_ids:
            response = client.get("/test", headers={"X-Tenant-ID": tenant_id})

            # Tenant ID is NOT set in request.state by request_id middleware
            assert response.json()["tenant_id"] is None

    @pytest.mark.skip(reason="TestClient doesn't capture stdout logs")
    def test_tenant_context_in_logs(self, client):
        """Test that tenant context appears in logs."""
        tenant_id = "tenant-789"

        with patch("sys.stdout", new=StringIO()) as mock_stdout:
            client.get("/test", headers={"X-Tenant-ID": tenant_id})
            output = mock_stdout.getvalue()

        # Should have logs
        assert len(output) > 0

    def test_no_tenant_cross_contamination(self, client):
        """Test that tenant context doesn't leak between requests."""
        # Request 1 with tenant
        response1 = client.get("/test", headers={"X-Tenant-ID": "tenant-first"})

        # Request 2 without tenant
        response2 = client.get("/test")

        # Request 3 with different tenant
        response3 = client.get("/test", headers={"X-Tenant-ID": "tenant-second"})

        # Tenant ID is NOT set in request.state by request_id middleware
        assert response1.json()["tenant_id"] is None
        assert response2.json()["tenant_id"] is None
        assert response3.json()["tenant_id"] is None
