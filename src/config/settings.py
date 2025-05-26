"""Application settings and configuration using latest Pydantic v2."""

from functools import lru_cache
from typing import Optional

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with Pydantic v2."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # OpenAI Configuration
    openai_api_key: SecretStr = Field(..., description="OpenAI API Key")
    openai_model_main: str = Field(default="gpt-4", description="Main GPT model")
    openai_model_mini: str = Field(default="gpt-4o-mini", description="Mini GPT model")

    # API Configuration
    api_host: str = Field(default="0.0.0.0", description="API host")
    api_port: int = Field(default=2024, description="API port")
    api_workers: int = Field(default=1, description="Number of API workers")

    # Database Configuration
    database_url: str = Field(
        default="sqlite+aiosqlite:///./soluto_agents.db",
        description="Database URL",
    )

    # Memory Configuration
    memory_type: str = Field(default="sqlite", description="Memory store type")
    redis_url: str = Field(default="redis://localhost:6379/0", description="Redis URL")

    # Logging Configuration
    log_level: str = Field(default="INFO", description="Log level")
    log_format: str = Field(default="structured", description="Log format")

    # Security
    secret_key: SecretStr = Field(
        default="soluto-secret-key-change-in-production",
        description="Secret key for JWT",
    )
    api_key: SecretStr = Field(
        default="soluto-api-key-change-in-production",
        description="API key for authentication",
    )

    # System Configuration
    max_iterations: int = Field(default=10, description="Max agent iterations")
    agent_timeout: int = Field(default=300, description="Agent timeout in seconds")
    memory_ttl: int = Field(default=3600, description="Memory TTL in seconds")
    max_concurrent_agents: int = Field(default=3, description="Max concurrent agents")

    # External Services (optional)
    firecrawl_api_key: Optional[SecretStr] = Field(
        None, description="Firecrawl API key"
    )
    perplexity_api_key: Optional[SecretStr] = Field(
        None, description="Perplexity AI API key"
    )

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Invalid log level: {v}")
        return v.upper()

    @field_validator("memory_type")
    @classmethod
    def validate_memory_type(cls, v: str) -> str:
        """Validate memory type."""
        valid_types = ["sqlite", "redis"]
        if v.lower() not in valid_types:
            raise ValueError(f"Invalid memory type: {v}")
        return v.lower()


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()