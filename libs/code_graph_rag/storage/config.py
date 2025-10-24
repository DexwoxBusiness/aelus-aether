"""Storage configuration for PostgreSQL backend.

This module provides configuration for PostgreSQL graph storage.

Added in AAET-84: PostgreSQL storage configuration.
"""

import os
from dataclasses import dataclass


@dataclass
class StorageConfig:
    """Configuration for PostgreSQL graph storage backend.

    Attributes:
        connection_string: PostgreSQL connection string
        min_pool_size: Minimum connection pool size
        max_pool_size: Maximum connection pool size
        connection_timeout: Connection timeout in seconds
        query_timeout: Query timeout in seconds
    """

    connection_string: str = ""
    min_pool_size: int = 2
    max_pool_size: int = 10
    connection_timeout: float = 30.0
    query_timeout: float = 60.0

    @classmethod
    def from_env(cls) -> "StorageConfig":
        """Create configuration from environment variables.

        Environment variables:
            DATABASE_URL: PostgreSQL connection string
            GRAPH_MIN_POOL_SIZE: Minimum connection pool size
            GRAPH_MAX_POOL_SIZE: Maximum connection pool size
            GRAPH_CONNECTION_TIMEOUT: Connection timeout in seconds
            GRAPH_QUERY_TIMEOUT: Query timeout in seconds

        Returns:
            StorageConfig instance

        Example:
            export DATABASE_URL=postgresql://user:pass@localhost/dbname
            config = StorageConfig.from_env()
        """
        return cls(
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
        if not self.connection_string:
            raise ValueError("connection_string is required")

        if not self.connection_string.startswith(("postgresql://", "postgres://")):
            raise ValueError("connection_string must be a PostgreSQL connection string")

        if self.min_pool_size < 1:
            raise ValueError("min_pool_size must be >= 1")

        if self.max_pool_size < self.min_pool_size:
            raise ValueError("max_pool_size must be >= min_pool_size")

        if self.connection_timeout <= 0:
            raise ValueError("connection_timeout must be > 0")

        if self.query_timeout <= 0:
            raise ValueError("query_timeout must be > 0")


def create_store_from_config(config: StorageConfig):
    """Create PostgreSQL storage backend from configuration.

    Args:
        config: Storage configuration

    Returns:
        PostgresGraphStore instance

    Raises:
        ValueError: If configuration is invalid
        ImportError: If asyncpg is not installed

    Example:
        config = StorageConfig.from_env()
        store = create_store_from_config(config)
        await store.connect()
    """
    config.validate()

    from .postgres_store import PostgresGraphStore

    return PostgresGraphStore(config.connection_string)
