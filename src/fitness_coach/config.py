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
    database_path: str = "data/fitness_coach.db"

    # Strava API
    strava_client_id: str = ""
    strava_client_secret: str = ""
    strava_access_token: str = ""
    strava_refresh_token: str = ""

    # OpenAI (for Strands agents)
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"

    # Anthropic (alternative)
    anthropic_api_key: str = ""

    # Google Gemini
    gemini_api_key: str = ""

    # Ollama settings
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "llama3.1:8b"

    # Coach settings
    coach_name: str = "Coach"


def get_settings() -> Settings:
    return Settings()
