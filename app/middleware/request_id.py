"""Request ID middleware for tracking requests across services."""

import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from loguru import logger


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Middleware to generate and propagate request IDs.
    
    - Generates a unique request ID for each request
    - Uses existing X-Request-ID header if provided
    - Adds request ID to response headers
    - Binds request ID to logger context
    """
    
    REQUEST_ID_HEADER = "X-Request-ID"
    
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
            # Log incoming request
            logger.info(
                f"{request.method} {request.url.path}",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "query_params": str(request.query_params),
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
