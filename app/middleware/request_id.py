"""Request ID middleware for tracking requests across services."""

import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.datastructures import QueryParams
from loguru import logger


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
        """Process request and add request ID."""
        # Get or generate request ID
        request_id = request.headers.get(self.REQUEST_ID_HEADER)
        if not request_id:
            request_id = str(uuid.uuid4())
        
        # Store request ID in request state for access in route handlers
        request.state.request_id = request_id
        
        # Bind request ID to logger context
        with logger.contextualize(request_id=request_id):
            # Log incoming request with sanitized query params
            logger.info(
                f"{request.method} {request.url.path}",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "query_params": self._sanitize_query_params(request.query_params),
                }
            )
            
            # Process request
            response = await call_next(request)
            
            # Add request ID to response headers
            response.headers[self.REQUEST_ID_HEADER] = request_id
            
            # Log response
            logger.info(
                f"Response {response.status_code}",
                extra={
                    "status_code": response.status_code,
                }
            )
            
            return response
