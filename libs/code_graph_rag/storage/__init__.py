"""Storage abstractions for code graph data.

This module provides abstract interfaces and concrete implementations
for storing and querying code graph data.

Added in AAET-84: Abstract storage interface to support multiple backends.
Updated in AAET-85: Removed SyncGraphStoreWrapper (all async now).
"""

from .config import StorageConfig, create_store_from_config
from .interface import GraphStoreInterface, StorageError
from .postgres_store import PostgresGraphStore

__all__ = [
    "GraphStoreInterface",
    "StorageError",
    "PostgresGraphStore",
    "StorageConfig",
    "create_store_from_config",
]
