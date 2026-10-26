import pytest

from app.ai import llm
from app.ai.settings import AiSettings


def make(**kw):
    return AiSettings(_env_file=None, **kw)


def test_unconfigured_without_key_or_model():
    assert not make().configured
    assert not make(GROQ_API_KEY="k").configured
    assert not make(GROQ_MODEL="m").configured
    assert make(GROQ_API_KEY="k", GROQ_MODEL="m").configured


def test_build_llm_refuses_when_unconfigured():
    with pytest.raises(llm.AssistantUnavailable) as e:
        llm.build_llm(make())
    assert e.value.status_code == 503 and "unavailable" in e.value.message


@pytest.mark.parametrize(
    "name,code",
    [
        ("RateLimitError", 429),
        ("APITimeoutError", 504),
        ("AuthenticationError", 502),
        ("NotFoundError", 502),
        ("APIConnectionError", 503),
        ("SomethingElse", 502),
    ],
)
def test_provider_errors_are_mapped_safely(name, code):
    exc = type(name, (Exception,), {})("secret-detail gsk_abc")
    out = llm.map_provider_error(exc)
    assert out.status_code == code
    assert "gsk_" not in out.message and "secret" not in out.message