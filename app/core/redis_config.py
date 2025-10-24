"""Redis configuration classes for dependency injection."""

from dataclasses import dataclass


@dataclass
class RedisClientConfig:
    """Configuration for a single Redis client."""

    host: str
    port: int
    db: int
    password: str | None = None
    decode_responses: bool = True
    max_connections: int = 50
    socket_connect_timeout: int = 5
    socket_keepalive: bool = True
    health_check_interval: int = 30

    def to_dict(self) -> dict:
        """Convert config to dictionary for Redis client initialization."""
        config = {
            "host": self.host,
            "port": self.port,
            "db": self.db,
            "decode_responses": self.decode_responses,
            "max_connections": self.max_connections,
            "socket_connect_timeout": self.socket_connect_timeout,
            "socket_keepalive": self.socket_keepalive,
            "health_check_interval": self.health_check_interval,
        }

        # Only add password if provided
        if self.password:
            config["password"] = self.password

        return config


@dataclass
class RedisConfig:
    """Configuration for all Redis clients."""

    queue_config: RedisClientConfig
    cache_config: RedisClientConfig
    rate_limit_config: RedisClientConfig

    @classmethod
    def from_settings(cls, host: str, port: int, password: str | None = None) -> "RedisConfig":
        """
        Create RedisConfig from application settings.

        Args:
            host: Redis host
            port: Redis port
            password: Redis password (optional)

        Returns:
            RedisConfig with separate client configurations
        """
        return cls(
            queue_config=RedisClientConfig(host=host, port=port, db=0, password=password),
            cache_config=RedisClientConfig(host=host, port=port, db=1, password=password),
            rate_limit_config=RedisClientConfig(host=host, port=port, db=2, password=password),
        )
