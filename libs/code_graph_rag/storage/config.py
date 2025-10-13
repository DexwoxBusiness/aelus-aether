"""Storage configuration for backend selection.

This module provides configuration for selecting and configuring
different storage backends (PostgreSQL, Memgraph, etc.).

Added in AAET-84: Configuration system for backend selection.
"""

import os
from dataclasses import dataclass
from typing import Literal


@dataclass
class StorageConfig:
    """Configuration for graph storage backend.
    
    Attributes:
        backend: Storage backend type ("postgres" or "memgraph")
        connection_string: Database connection string
        min_pool_size: Minimum connection pool size (PostgreSQL only)
        max_pool_size: Maximum connection pool size (PostgreSQL only)
        connection_timeout: Connection timeout in seconds
        query_timeout: Query timeout in seconds
    """
    
    backend: Literal["postgres", "memgraph"] = "postgres"
    connection_string: str = ""
    min_pool_size: int = 2
    max_pool_size: int = 10
    connection_timeout: float = 30.0
    query_timeout: float = 60.0
    
    @classmethod
    def from_env(cls) -> "StorageConfig":
        """Create configuration from environment variables.
        
        Environment variables:
            GRAPH_BACKEND: Storage backend ("postgres" or "memgraph")
            DATABASE_URL: Database connection string
            GRAPH_MIN_POOL_SIZE: Minimum connection pool size
            GRAPH_MAX_POOL_SIZE: Maximum connection pool size
            GRAPH_CONNECTION_TIMEOUT: Connection timeout in seconds
            GRAPH_QUERY_TIMEOUT: Query timeout in seconds
        
        Returns:
            StorageConfig instance
        
        Example:
            export GRAPH_BACKEND=postgres
            export DATABASE_URL=postgresql://user:pass@localhost/dbname
            config = StorageConfig.from_env()
        """
        return cls(
            backend=os.getenv("GRAPH_BACKEND", "postgres"),  # type: ignore
            connection_string=os.getenv("DATABASE_URL", ""),
            min_pool_size=int(os.getenv("GRAPH_MIN_POOL_SIZE", "2")),
            max_pool_size=int(os.getenv("GRAPH_MAX_POOL_SIZE", "10")),
            connection_timeout=float(os.getenv("GRAPH_CONNECTION_TIMEOUT", "30.0")),
            query_timeout=float(os.getenv("GRAPH_QUERY_TIMEOUT", "60.0")),
        )
    
    def validate(self) -> None:
        """Validate configuration.
        
        Raises:
            ValueError: If configuration is invalid
        """
        if self.backend not in ("postgres", "memgraph"):
            raise ValueError(f"Invalid backend: {self.backend}. Must be 'postgres' or 'memgraph'")
        
        if not self.connection_string:
            raise ValueError("connection_string is required")
        
        if self.min_pool_size < 1:
            raise ValueError("min_pool_size must be >= 1")
        
        if self.max_pool_size < self.min_pool_size:
            raise ValueError("max_pool_size must be >= min_pool_size")
        
        if self.connection_timeout <= 0:
            raise ValueError("connection_timeout must be > 0")
        
        if self.query_timeout <= 0:
            raise ValueError("query_timeout must be > 0")


def create_store_from_config(config: StorageConfig):
    """Create a storage backend from configuration.
    
    Args:
        config: Storage configuration
    
    Returns:
        GraphStoreInterface implementation
    
    Raises:
        ValueError: If configuration is invalid
        ImportError: If required backend dependencies are missing
    
    Example:
        config = StorageConfig.from_env()
        store = create_store_from_config(config)
        await store.connect()
    """
    config.validate()
    
    if config.backend == "postgres":
        from .postgres_store import PostgresGraphStore
        return PostgresGraphStore(config.connection_string)
    elif config.backend == "memgraph":
        # Future: Create MemgraphAdapter
        raise NotImplementedError("Memgraph backend not yet implemented via config")
    else:
        raise ValueError(f"Unknown backend: {config.backend}")
