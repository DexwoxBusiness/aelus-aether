"""Ingestion services for code parsing and graph building.

This package contains services for parsing code repositories and
building knowledge graphs with proper tenant context.
"""

from .parser_service import ParserService

__all__ = ["ParserService"]
