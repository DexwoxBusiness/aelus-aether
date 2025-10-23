"""Middleware for cross-cutting concerns."""

from app.middleware.request_id import RequestIDMiddleware

__all__ = ["RequestIDMiddleware"]
