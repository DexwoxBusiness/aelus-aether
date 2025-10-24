"""Request ID middleware for tracking requests across services."""

import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.datastructures import QueryParams
import structlog


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Middleware to generate and propagate request IDs.
    
    - Generates a unique request ID for each request
    - Uses existing X-Request-ID header if provided
    - Adds request ID to response headers
    - Binds request ID to logger context
    - Sanitizes sensitive data in logs
    """
    
    REQUEST_ID_HEADER = "X-Request-ID"
    SENSITIVE_KEYS = {'password', 'token', 'secret', 'key', 'authorization', 'api_key', 'apikey'}
    
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
        
        # Get tenant ID from headers if available (for multi-tenant support)
        tenant_id = request.headers.get("X-Tenant-ID")
        if tenant_id:
            request.state.tenant_id = tenant_id
        
        # Get logger and bind context
        logger = structlog.get_logger()
        
        # Build context dictionary
        context = {"request_id": request_id}
        if tenant_id:
            context["tenant_id"] = tenant_id
        
        # Bind context to logger
        logger = logger.bind(**context)
        
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
