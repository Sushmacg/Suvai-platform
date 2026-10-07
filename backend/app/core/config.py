from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    API_V1_PREFIX: str = "/api/v1"
    app_name: str = "Suvai API"
    version: str = "0.1.0"

    environment: str = "development"
    debug: bool = True
    cors_origins: str = ""

    ADMIN_NAME: str = "Suvai Owner"
    ADMIN_PHONE: str = ""
    ADMIN_PASSWORD: str = ""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()