from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class AiSettings(BaseSettings):
    GROQ_API_KEY: SecretStr | None = None
    GROQ_MODEL: str = ""
    GROQ_FALLBACK_MODEL: str = ""
    AI_TIMEOUT_SECONDS: int = 20
    AI_MAX_OUTPUT_TOKENS: int = 600
    AI_MAX_QUESTION_CHARS: int = 500

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def configured(self) -> bool:
        key = self.GROQ_API_KEY.get_secret_value().strip() if self.GROQ_API_KEY else ""
        return bool(key and self.GROQ_MODEL.strip())


def get_ai_settings() -> AiSettings:
    return AiSettings()