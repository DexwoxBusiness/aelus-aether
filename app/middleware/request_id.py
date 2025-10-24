"""Request ID middleware for tracking requests across services."""

import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.datastructures import QueryParams

from app.config import settings
from app.core.logging import bind_request_context, clear_request_context, get_context_logger


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Middleware to generate and propagate request IDs.
    
    - Generates a unique request ID for each request
    - Uses existing X-Request-ID header if provided
    - Adds request ID to response headers
    - Binds request ID to logger context
    - Sanitizes sensitive data in logs
    - Validates tenant ID format to prevent spoofing
    """
    
    REQUEST_ID_HEADER = "X-Request-ID"
    SENSITIVE_KEYS = {'password', 'token', 'secret', 'key', 'authorization', 'api_key', 'apikey'}
    
    def _is_valid_tenant_format(self, tenant_id: str) -> bool:
        """
        Validate tenant ID format to prevent spoofing.
        
        This is a basic format validation. In production, this should be
        enhanced to validate against authenticated user's tenant scope.
        
        Args:
            tenant_id: Tenant ID from header
            
        Returns:
            True if tenant ID format is valid
        """
        if not tenant_id:
            return False
        
        # Basic validation: alphanumeric, hyphens, underscores only
        # Length between 1 and 64 characters
        # TODO (AAET-15): Enhance with authentication-based validation
        # when user authentication is implemented
        import re
        pattern = r'^[a-zA-Z0-9_-]{1,64}$'
        return bool(re.match(pattern, tenant_id))
    
    def _sanitize_query_params(self, query_params: QueryParams) -> str:
        """
        Sanitize query parameters to avoid logging sensitive data.
        
        Args:
            query_params: Request query parameters
            
        Returns:
            Sanitized query parameters as string
        """
        params_dict = dict(query_params)
        
        for key in params_dict.keys():
            if any(sensitive in key.lower() for sensitive in self.SENSITIVE_KEYS):
                params_dict[key] = '***REDACTED***'
        
        return str(params_dict)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and add request ID and tenant context."""
        # Get or generate request ID
        request_id = request.headers.get(self.REQUEST_ID_HEADER)
        if not request_id:
            request_id = str(uuid.uuid4())
        
        # Store request ID in request state for access in route handlers
        request.state.request_id = request_id
        
        # Get and validate tenant ID from headers (for multi-tenant support)
        # NOTE: This is basic format validation. In production with authentication,
        # tenant ID should be validated against the authenticated user's tenant scope.
        # See TODO (AAET-15) for authentication-based validation.
        tenant_id = None
        if settings.tenant_header_name in request.headers:
            tenant_header = request.headers[settings.tenant_header_name]
            if self._is_valid_tenant_format(tenant_header):
                tenant_id = tenant_header
                request.state.tenant_id = tenant_id
            else:
                # Log invalid tenant ID attempt (potential security issue)
                logger = get_context_logger(__name__)
                logger.warning(
                    "Invalid tenant ID format in header",
                    tenant_header=tenant_header[:20],  # Truncate for safety
                )
        
        # Bind context to context variables for automatic propagation
        bind_request_context(request_id=request_id, tenant_id=tenant_id)
        
        try:
            # Get logger with automatic context binding
            logger = get_context_logger(__name__)
            
            # Log incoming request with sanitized query params
            logger.info(
                "Incoming request",
                method=request.method,
                path=request.url.path,
                query_params=self._sanitize_query_params(request.query_params),
            )
            
            # Process request
            response = await call_next(request)
            
            # Add request ID to response headers
            response.headers[self.REQUEST_ID_HEADER] = request_id
            
            # Log response
            logger.info(
                "Request completed",
                status_code=response.status_code,
            )
            
            return response
        except Exception as exc:
            # Log the error with full context
            logger = get_context_logger(__name__)
            logger.error(
                "Request processing failed",
                error=str(exc),
                error_type=type(exc).__name__,
            )
            raise
        finally:
            # Always clear context after request is processed
            clear_request_context()
