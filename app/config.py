"""Application configuration."""

from enum import Enum

from pydantic import Field, PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class LogLevel(str, Enum):
    """Valid log levels."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Application
    app_name: str = "aelus-aether"
    app_version: str = "0.1.0"
    environment: str = "development"
    debug: bool = False
    log_level: LogLevel = LogLevel.INFO
    json_logs: bool = True  # Enable JSON structured logging
    log_sampling: bool = False  # Enable log sampling for high-volume endpoints
    log_sample_rate_debug: float = 0.01  # Sample 1% of DEBUG logs
    log_sample_rate_info: float = 0.05  # Sample 5% of INFO logs (conservative for production)
    log_sample_rate_warning: float = 1.0  # Sample 100% of WARNING logs
    log_sample_rate_error: float = 1.0  # Sample 100% of ERROR logs
    
    # Multi-tenancy
    tenant_header_name: str = "X-Tenant-ID"  # Standardized tenant ID header name

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000  # Standard FastAPI port (JIRA AAET-9 specified 8080, but 8000 is more common)
    api_prefix: str = "/api/v1"

    # Security
    secret_key: str = Field(..., min_length=32)
    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = 1440  # 24 hours

    # PostgreSQL
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "aelus"
    postgres_password: str = Field(..., min_length=8)
    postgres_db: str = "aelus_aether"
    database_url: PostgresDsn | None = None

    @property
    def db_url(self) -> str:
        """Get database URL."""
        if self.database_url:
            return str(self.database_url)
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: str | None = None
    redis_url: str | None = None

    @property
    def redis_connection_url(self) -> str:
        """Get Redis URL."""
        if self.redis_url:
            return self.redis_url
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"

    # Celery
    celery_broker_url: str | None = None
    celery_result_backend: str | None = None

    @property
    def celery_broker(self) -> str:
        """Get Celery broker URL."""
        return self.celery_broker_url or self.redis_connection_url

    @property
    def celery_backend(self) -> str:
        """Get Celery result backend URL."""
        return self.celery_result_backend or self.redis_connection_url

    # AI Services
    voyage_api_key: str | None = None
    voyage_model_name: str = "voyage-code-3"
    voyage_embedding_dimension: int = 1024
    voyage_max_batch_size: int = 96
    voyage_rate_limit_delay: float = 1.0
    
    cohere_api_key: str | None = None
    openai_api_key: str | None = None

    # Rate Limiting
    rate_limit_per_minute: int = 60
    rate_limit_per_hour: int = 1000

    # Monitoring
    prometheus_port: int = 9090


# Global settings instance
settings = Settings()
