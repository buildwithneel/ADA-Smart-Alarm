from typing import Any, List, Optional, Union

from pydantic import ValidationInfo, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    PROJECT_NAME: str = "ADA - Adaptive Dynamic Alarm"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"
    SECRET_KEY: str = "supersecret-ada-dev-key-change-in-production"

    # Database Settings
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_USER: str = "ada_admin"
    POSTGRES_PASSWORD: str = "change_me_in_production"
    POSTGRES_DB: str = "ada_prod"
    DATABASE_URL: Optional[str] = None

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def assemble_db_connection(cls, v: Optional[str], info: ValidationInfo) -> Any:
        if isinstance(v, str) and v.strip():
            return v.strip()
        user = info.data.get("POSTGRES_USER", "ada_admin")
        pwd = info.data.get("POSTGRES_PASSWORD", "change_me_in_production")
        server = info.data.get("POSTGRES_SERVER", "localhost")
        db = info.data.get("POSTGRES_DB", "ada_prod")
        return f"postgresql://{user}:{pwd}@{server}:5432/{db}"

    # Database Connection Pool Settings (Production Tuned)
    DB_POOL_SIZE: int = 15
    DB_MAX_OVERFLOW: int = 25
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 1800  # Recycle after 30 minutes to prevent stale cloud disconnects
    DB_POOL_PRE_PING: bool = True

    # Security, Headers & Payload Protection Settings
    ENABLE_DOCS: bool = True  # Can be disabled in production via ENABLE_DOCS=false
    MAX_CONTENT_LENGTH_BYTES: int = 2 * 1024 * 1024  # 2 MB maximum request body size
    JSON_LOGGING: bool = False  # Enabled in production
    SECURE_HEADERS_ENABLED: bool = True
    ALLOWED_HOSTS: List[str] = ["*"]

    # Redis Settings
    REDIS_URL: str = "redis://localhost:6379/0"

    # Celery Settings
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"

    # External Provider Credentials (decoupled / optional)
    GOOGLE_MAPS_API_KEY: Optional[str] = None
    MAPBOX_ACCESS_TOKEN: Optional[str] = None
    FIREBASE_PROJECT_ID: Optional[str] = None

    # Maps, Routing & Geocoding Provider Architecture
    ROUTING_PROVIDER: str = "google"
    ROUTING_FALLBACK_PROVIDER: str = "mapbox"
    GEOCODING_PROVIDER: str = "google"
    GEOCODING_FALLBACK_PROVIDER: str = "mapbox"
    ENABLE_PROVIDER_FALLBACK: bool = True
    PROVIDER_TIMEOUT_SECONDS: float = 6.0
    GEOCODING_CACHE_TTL_SECONDS: int = 86400  # 24 hours
    ROUTE_CACHE_TTL_SECONDS: int = 300  # 5 minutes (for traffic freshness)
    RATE_LIMIT_PER_MINUTE: int = 60

    # Step 8: Dynamic Traffic Recalculation & Refresh Policy
    TRAFFIC_REFRESH_INTERVAL_SECONDS: int = 300  # Periodic sweep interval (5 min)
    UPCOMING_ALARM_WINDOW_SECONDS: int = 14400  # 4 hours window before departure
    ETA_CHANGE_THRESHOLD_SECONDS: int = 180  # 3 minutes threshold to prevent schedule churn
    ROUTE_FRESHNESS_SECONDS: int = 600  # 10 minutes: route considered fresh
    ROUTE_STALE_THRESHOLD_SECONDS: int = 1800  # 30 minutes: route marked stale/outdated
    MAX_PROVIDER_REQUESTS_PER_RUN: int = 50  # Protect provider quotas in batch runs
    RECALCULATION_LOCK_TIMEOUT_SECONDS: int = 30  # Redis distributed lock TTL

    # Step 9: Notifications & Web Push Configuration
    VAPID_PUBLIC_KEY: Optional[str] = None
    VAPID_PRIVATE_KEY: Optional[str] = None
    VAPID_CLAIMS_EMAIL: str = "mailto:admin@ada-alarm.app"
    NOTIFICATION_RETENTION_DAYS: int = 30
    MAX_NOTIFICATION_RETRIES: int = 3
    NOTIFICATION_RETRY_BACKOFF_SECONDS: int = 60
    NOTIFICATION_DELIVERY_BATCH_SIZE: int = 100
    NOTIFICATION_SWEEP_INTERVAL_SECONDS: int = 30
    NOTIFICATION_LOCK_TIMEOUT_SECONDS: int = 20

    # Step 10: Weather + Calendar + Context Intelligence
    WEATHER_PROVIDER: str = "open-meteo"
    WEATHER_API_KEY: Optional[str] = None
    WEATHER_CACHE_TTL_SECONDS: int = 900  # 15 minutes
    WEATHER_FORECAST_MAX_AGE_SECONDS: int = 3600  # 1 hour
    WEATHER_BUFFER_DEFAULT_MINUTES: int = 10
    WEATHER_BUFFER_MAX_MINUTES: int = 30
    WEATHER_PRECIPITATION_THRESHOLD_MM: float = 0.5  # Qualifying rain threshold
    WEATHER_SWEEP_INTERVAL_SECONDS: int = 600  # Periodic weather refresh (10 min)

    GOOGLE_CALENDAR_CLIENT_ID: Optional[str] = None
    GOOGLE_CALENDAR_CLIENT_SECRET: Optional[str] = None
    GOOGLE_CALENDAR_REDIRECT_URI: str = "http://localhost:5173/settings?tab=calendar"
    CALENDAR_SYNC_INTERVAL_SECONDS: int = 900  # 15 minutes
    CALENDAR_UPCOMING_WINDOW_DAYS: int = 7
    TOKEN_ENCRYPTION_KEY: Optional[str] = None

    # Step 11: AI Assistant & Personalization Architecture
    AI_PROVIDER: str = "mock"  # "mock", "gemini", "openai", "disabled"
    AI_API_KEY: Optional[str] = None
    AI_MODEL_NAME: str = "gemini-1.5-flash"
    AI_TIMEOUT_SECONDS: float = 10.0
    AI_MAX_RETRIES: int = 2
    AI_RATE_LIMIT_PER_MINUTE: int = 20
    AI_MAX_INPUT_LENGTH: int = 1000
    AI_CONVERSATION_HISTORY_ENABLED: bool = True
    AI_CONVERSATION_RETENTION_DAYS: int = 30

    # CORS Allowed Origins
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
    ]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, list):
            return v
        import json

        try:
            return json.loads(v)
        except Exception:
            return ["http://localhost:5173", "http://127.0.0.1:5173"]

    @model_validator(mode="after")
    def validate_production_configuration(self) -> "Settings":
        """
        Enforce strict security and fail-fast validation when deployed in production.
        Prevents starting with default secrets, dev passwords, or insecure fallbacks.
        """
        if self.ENVIRONMENT == "production":
            # Enable JSON structured logging by default in production
            if not self.JSON_LOGGING:
                object.__setattr__(self, "JSON_LOGGING", True)

            # 1. SECRET_KEY validation
            if self.SECRET_KEY == "supersecret-ada-dev-key-change-in-production":
                raise ValueError(
                    "CRITICAL SECURITY: Insecure default SECRET_KEY cannot be used in production. "
                    "Set a cryptographically strong SECRET_KEY (min 32 characters)."
                )
            if len(self.SECRET_KEY) < 32:
                raise ValueError(
                    "CRITICAL SECURITY: Production SECRET_KEY must be at least 32 characters long."
                )

            # 2. Database credentials validation
            if self.POSTGRES_PASSWORD == "change_me_in_production":
                raise ValueError(
                    "CRITICAL SECURITY: Default POSTGRES_PASSWORD ('change_me_in_production') "
                    "cannot be used in production."
                )
            if self.DATABASE_URL and "change_me_in_production" in self.DATABASE_URL:
                raise ValueError(
                    "CRITICAL SECURITY: Default database password found in DATABASE_URL."
                )

        return self


settings = Settings()
