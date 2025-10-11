"""Application configuration."""

from pydantic import Field, PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


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
    log_level: str = "INFO"

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
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
    cohere_api_key: str | None = None
    openai_api_key: str | None = None

    # Rate Limiting
    rate_limit_per_minute: int = 60
    rate_limit_per_hour: int = 1000

    # Monitoring
    prometheus_port: int = 9090


# Global settings instance
settings = Settings()
