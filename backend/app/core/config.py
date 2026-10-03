from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Suvai API"
    VERSION: str = "0.1.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    API_V1_PREFIX: str = "/api/v1"

    # Origins allowed to call the API from a browser (dev defaults)
    CORS_ORIGINS: list[str] = [
        "http://localhost:8081",   # Expo / Metro
        "http://localhost:19006",  # Expo web
        "http://localhost:3000",   # any web admin panel later
    ]

    # Read values from .env if it exists; ignore unknown keys
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()