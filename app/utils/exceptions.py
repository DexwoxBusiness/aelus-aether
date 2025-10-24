"""Custom exceptions for application utilities."""


class CacheError(Exception):
    """Exception raised for cache operation failures."""

    pass


class RateLimitError(Exception):
    """Exception raised for rate limiting failures."""

    pass
