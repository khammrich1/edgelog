"""Application configuration."""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List
import json


class Settings(BaseSettings):
    """Application settings."""

    # Environment
    ENVIRONMENT: str = "development"

    # Database
    DATABASE_URL: str

    # Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # CORS - expect JSON array string
    ALLOWED_ORIGINS: str = '["http://localhost:5173"]'

    # Cookie settings
    COOKIE_SECURE: bool = False
    COOKIE_SAMESITE: str = "lax"
    COOKIE_DOMAIN: str = "localhost"

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True
    )

    @property
    def cors_origins(self) -> List[str]:
        """Parse CORS origins from JSON string."""
        return json.loads(self.ALLOWED_ORIGINS)

    @property
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.ENVIRONMENT == "production"


settings = Settings()
