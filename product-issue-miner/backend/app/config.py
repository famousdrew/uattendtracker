"""
Application configuration using pydantic-settings.
Loads configuration from environment variables and .env file.
"""

from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    Supports loading from .env file for local development.
    """

    # Zendesk API Configuration
    ZENDESK_SUBDOMAIN: str = Field(
        default="workwelltech",
        description="Zendesk subdomain (e.g., 'company' for company.zendesk.com)"
    )
    ZENDESK_EMAIL: str = Field(
        description="Zendesk user email for API authentication"
    )
    ZENDESK_API_TOKEN: str = Field(
        description="Zendesk API token for authentication"
    )
    ZENDESK_BRAND_ID: Optional[int] = Field(
        default=None,
        description="Zendesk brand ID to filter tickets (optional)"
    )

    # Anthropic API Configuration
    ANTHROPIC_API_KEY: str = Field(
        description="Anthropic API key for Claude AI"
    )

    # Database Configuration
    DATABASE_URL: str = Field(
        description="PostgreSQL database URL (use postgresql+asyncpg:// for async)"
    )

    # Redis Configuration (optional)
    REDIS_URL: Optional[str] = Field(
        default=None,
        description="Redis URL for caching and job queues"
    )

    # Security Configuration
    DASHBOARD_PASSWORD: str = Field(
        description="Password for dashboard access"
    )

    # CORS Configuration
    CORS_ORIGINS: str = Field(
        default="http://localhost:3000",
        description="Comma-separated list of allowed CORS origins"
    )

    # Rate Limiting Configuration
    AUTH_RATE_LIMIT: int = Field(
        default=5,
        description="Maximum authentication requests per minute per IP"
    )

    GENERAL_RATE_LIMIT: int = Field(
        default=100,
        description="Maximum general API requests per minute per IP"
    )

    # Request Size Limits
    MAX_REQUEST_SIZE: int = Field(
        default=10 * 1024 * 1024,  # 10MB
        description="Maximum request body size in bytes"
    )

    # Environment
    ENVIRONMENT: str = Field(
        default="development",
        description="Application environment: development, staging, production"
    )

    # API Configuration
    API_BASE_URL: Optional[str] = Field(
        default=None,
        description="Base URL for API endpoints (e.g., https://api.example.com)"
    )

    FRONTEND_URL: Optional[str] = Field(
        default=None,
        description="Frontend URL for CORS configuration (legacy, use CORS_ORIGINS)"
    )

    # Logging Configuration
    LOG_LEVEL: str = Field(
        default="INFO",
        description="Logging level: DEBUG, INFO, WARNING, ERROR, CRITICAL"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

    @property
    def zendesk_api_url(self) -> str:
        """Get the base Zendesk API URL."""
        return f"https://{self.ZENDESK_SUBDOMAIN}.zendesk.com/api/v2"

    @property
    def database_url_sync(self) -> str:
        """Get synchronous database URL for Alembic migrations."""
        return self.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")

    @property
    def cors_origins_list(self) -> list[str]:
        """Get CORS origins as a list."""
        if self.CORS_ORIGINS == "*":
            return ["*"]
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]

    def __repr__(self) -> str:
        """
        Custom repr that masks sensitive values.

        Prevents accidental exposure of credentials in logs.
        """
        sensitive_fields = {
            "ZENDESK_API_TOKEN",
            "ANTHROPIC_API_KEY",
            "DASHBOARD_PASSWORD",
            "DATABASE_URL",
            "REDIS_URL",
        }

        fields = []
        for field_name, field_info in self.model_fields.items():
            value = getattr(self, field_name)
            if field_name in sensitive_fields and value:
                # Mask sensitive values
                if isinstance(value, str) and len(value) > 8:
                    masked = value[:4] + "***" + value[-4:]
                else:
                    masked = "***"
                fields.append(f"{field_name}={masked!r}")
            else:
                fields.append(f"{field_name}={value!r}")

        return f"Settings({', '.join(fields)})"


# Create singleton settings instance
settings = Settings()
