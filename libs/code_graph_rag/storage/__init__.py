"""Storage abstractions for code graph data.

This module provides abstract interfaces and concrete implementations
for storing and querying code graph data.

Added in AAET-84: Abstract storage interface to support multiple backends.
"""

from .interface import GraphStoreInterface
from .postgres_store import PostgresGraphStore

__all__ = [
    "GraphStoreInterface",
    "PostgresGraphStore",
]
