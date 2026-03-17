"""
Application settings loaded from environment variables via pydantic-settings.
All secrets live in .env – never hard-code them here.
"""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # MongoDB
    MONGODB_URI: str = Field(default="mongodb://localhost:27017")
    MONGODB_DB_NAME: str = Field(default="geo_news")

    # Google APIs
    GOOGLE_GEOCODING_API_KEY: str = Field(default="")
    GOOGLE_MAPS_JS_API_KEY: str = Field(default="")

    # Scraper
    SCRAPE_SCHEDULE_CRON: str = Field(default="0 * * * *")

    # CORS – comma-separated origins in .env, e.g. "http://localhost:5173"
    CORS_ORIGINS: list[str] = Field(default=["http://localhost:5173"])


settings = Settings()
