"""Redis configuration classes for dependency injection."""

from dataclasses import dataclass


@dataclass
class RedisClientConfig:
    """Configuration for a single Redis client."""
    
    host: str
    port: int
    db: int
    decode_responses: bool = True
    max_connections: int = 50
    socket_connect_timeout: int = 5
    socket_keepalive: bool = True
    health_check_interval: int = 30
    
    def to_dict(self) -> dict:
        """Convert config to dictionary for Redis client initialization."""
        return {
            "host": self.host,
            "port": self.port,
            "db": self.db,
            "decode_responses": self.decode_responses,
            "max_connections": self.max_connections,
            "socket_connect_timeout": self.socket_connect_timeout,
            "socket_keepalive": self.socket_keepalive,
            "health_check_interval": self.health_check_interval,
        }


@dataclass
class RedisConfig:
    """Configuration for all Redis clients."""
    
    queue_config: RedisClientConfig
    cache_config: RedisClientConfig
    rate_limit_config: RedisClientConfig
    
    @classmethod
    def from_settings(cls, host: str, port: int) -> "RedisConfig":
        """
        Create RedisConfig from application settings.
        
        Args:
            host: Redis host
            port: Redis port
            
        Returns:
            RedisConfig with separate client configurations
        """
        return cls(
            queue_config=RedisClientConfig(host=host, port=port, db=0),
            cache_config=RedisClientConfig(host=host, port=port, db=1),
            rate_limit_config=RedisClientConfig(host=host, port=port, db=2),
        )
