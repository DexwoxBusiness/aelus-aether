"""Storage abstractions for code graph data.

This module provides abstract interfaces and concrete implementations
for storing and querying code graph data.

Added in AAET-84: Abstract storage interface to support multiple backends.
"""

from .interface import GraphStoreInterface, StorageError
from .postgres_store import PostgresGraphStore
from .config import StorageConfig, create_store_from_config
from .sync_wrapper import SyncGraphStoreWrapper

__all__ = [
    "GraphStoreInterface",
    "StorageError",
    "PostgresGraphStore",
    "StorageConfig",
    "create_store_from_config",
    "SyncGraphStoreWrapper",
]
