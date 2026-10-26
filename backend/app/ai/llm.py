import logging

from app.ai.settings import AiSettings

log = logging.getLogger(__name__)


class AssistantUnavailable(Exception):
    def __init__(self, status_code: int, message: str):
        super().__init__(message)
        self.status_code = status_code
        self.message = message


def build_llm(settings: AiSettings, model: str | None = None):
    """Real Groq chat model. Raises AssistantUnavailable when not configured."""
    if not settings.configured:
        raise AssistantUnavailable(
            503, "The AI assistant is not configured. Real LLM responses are unavailable."
        )
    from langchain_groq import ChatGroq

    return ChatGroq(
        model=model or settings.GROQ_MODEL,
        api_key=settings.GROQ_API_KEY.get_secret_value(),
        temperature=0,
        max_tokens=settings.AI_MAX_OUTPUT_TOKENS,
        timeout=settings.AI_TIMEOUT_SECONDS,
        max_retries=1,
    )


def map_provider_error(exc: Exception) -> AssistantUnavailable:
    """Turn a provider failure into a safe message. Never echoes provider text."""
    name = type(exc).__name__
    log.warning("Assistant provider error: %s", name)  # class name only, no details
    if name == "RateLimitError":
        return AssistantUnavailable(429, "The AI provider rate limit was reached. Try again shortly.")
    if "Timeout" in name:
        return AssistantUnavailable(504, "The AI provider timed out. Try again.")
    if name in ("AuthenticationError", "PermissionDeniedError"):
        return AssistantUnavailable(502, "The AI provider rejected the server credentials.")
    if name in ("NotFoundError", "BadRequestError"):
        return AssistantUnavailable(502, "The configured AI model is unavailable.")
    if name == "APIConnectionError":
        return AssistantUnavailable(503, "Could not reach the AI provider.")
    return AssistantUnavailable(502, "The AI provider returned an error.")