"""
Core Layer: Application Settings

Pydantic-based configuration from environment variables.

Clean Architecture Layer: Core
Responsibility: Provide application configuration settings
"""
from pathlib import Path
from pydantic_settings import BaseSettings
from typing import Optional

# NOTE: Sensitive credentials (DATABASE_URL, SECRET_KEY, SMTP_USERNAME, SMTP_PASSWORD, EMAIL_FROM_ADDRESS)
# should be set in the .env file, not hardcoded here.


class Settings(BaseSettings):
    PROJECT_NAME: str = "ManGO"
    VERSION: str = "2.0.0"
    API_PREFIX: str = "/api"
    RUN_SEEDS: bool = False
    
    # Database - supports PostgreSQL (production) and SQLite (development)
    # PostgreSQL: postgresql+asyncpg://user:password@localhost:5432/eam_db
    # SQLite: sqlite+aiosqlite:///./dev.db
    DATABASE_URL: str = "sqlite+aiosqlite:///./dev.db"
    
    # For sync operations (Alembic migrations)
    # PostgreSQL: postgresql://user:password@localhost:5432/eam_db
    # SQLite: sqlite:///./dev.db
    DATABASE_URL_SYNC: Optional[str] = None
    
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Database pool settings (PostgreSQL only; ignored for SQLite)
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_RECYCLE: int = 1800  # seconds
    DB_ECHO: bool = False

    REFRESH_TOKEN_COOKIE_NAME: str = "refresh_token"
    REFRESH_TOKEN_COOKIE_SECURE: bool = False
    REFRESH_TOKEN_COOKIE_SAMESITE: str = "lax"
    
    # Feature flags
    PURCHASE_ORDER_ENABLED: bool = False  # When False, PR flows directly to Purchase Receipt (skip PO)

    # File uploads
    UPLOAD_DIR: str = str(Path(__file__).resolve().parents[2] / "uploads")
    MAX_UPLOAD_SIZE_MB: int = 10

    # Email / SMTP
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USE_TLS: bool = True
    SMTP_USERNAME: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    EMAIL_FROM_ADDRESS: Optional[str] = None
    EMAIL_FROM_NAME: str = "App Notifications"
    EMAIL_ENABLED: bool = True

    # Deep links in notification emails (no trailing slash)
    PUBLIC_APP_URL: str = "http://localhost:3000/"

    CORS_ORIGINS: list[str] = [
        "https://eamvue.cubeworksinnovation.com",
        "http://eamvue.cubeworksinnovation.com",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
        "http://localhost:3002",
        "http://127.0.0.1:3002",
    ]

    # MQTT Broker
    MQTT_BROKER_HOST: str = "localhost"
    MQTT_BROKER_PORT: int = 1883
    MQTT_BROKER_USERNAME: Optional[str] = None
    MQTT_BROKER_PASSWORD: Optional[str] = None

    # Socket.IO CORS origins. If not set, fall back to CORS_ORIGINS.
    # Provide as JSON array in .env, e.g.
    # SOCKETIO_CORS_ORIGINS=["http://localhost:3000","http://127.0.0.1:3000"]
    SOCKETIO_CORS_ORIGINS: Optional[list[str]] = None

    @property
    def socketio_cors_origins(self) -> list[str]:
        if self.SOCKETIO_CORS_ORIGINS:
            return self.SOCKETIO_CORS_ORIGINS
        return self.CORS_ORIGINS
    
    @property
    def sync_database_url(self) -> str:
        """Get sync database URL for Alembic migrations."""
        if self.DATABASE_URL_SYNC:
            return self.DATABASE_URL_SYNC
        # Convert async URL to sync URL
        url = self.DATABASE_URL
        if "asyncpg" in url:
            return url.replace("postgresql+asyncpg", "postgresql")
        if "aiosqlite" in url:
            return url.replace("sqlite+aiosqlite", "sqlite")
        return url
    
    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
