"""Application configuration."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database
    database_url: str = ""

    # Strava API
    strava_client_id: str = ""
    strava_client_secret: str = ""
    strava_access_token: str = ""
    strava_refresh_token: str = ""

    # Google Gemini
    gemini_api_key: str = ""

    # Auth
    base_url: str = "http://localhost:8080"
    session_lifetime_days: int = 30


def get_settings() -> Settings:
    return Settings()
