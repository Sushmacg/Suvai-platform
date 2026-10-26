import pytest
from langchain_core.language_models.fake_chat_models import FakeListChatModel

from app.ai import router as ai_router
from app.ai.settings import AiSettings
from tests.conftest import PREFIX

URL = f"{PREFIX}/assistant/chat"


@pytest.fixture
def use_llm(client):
    def _use(llm):
        client.app.dependency_overrides[ai_router.get_llm] = lambda: llm

    yield _use
    client.app.dependency_overrides.pop(ai_router.get_llm, None)


def post(client, headers, q="How are sales?"):
    return client.post(URL, json={"question": q}, headers=headers)


def test_admin_gets_answer(client, admin_headers, use_llm):
    use_llm(FakeListChatModel(responses=["I have no data access yet."]))
    r = post(client, admin_headers)
    assert r.status_code == 200 and r.json() == {"answer": "I have no data access yet."}


def test_admin_only(client, customer_headers, admin_headers, use_llm):
    use_llm(FakeListChatModel(responses=["x"]))
    assert post(client, customer_headers).status_code == 403
    assert client.post(URL, json={"question": "hi"}).status_code in (401, 403)


@pytest.mark.parametrize("q", ["", "   ", "a" * 501])
def test_question_limits(client, admin_headers, use_llm, q):
    use_llm(FakeListChatModel(responses=["x"]))
    assert post(client, admin_headers, q).status_code == 422


def test_unconfigured_reports_unavailable(client, admin_headers, monkeypatch):
    monkeypatch.setattr(ai_router, "get_ai_settings", lambda: AiSettings(_env_file=None))
    r = post(client, admin_headers)
    assert r.status_code == 503 and "unavailable" in r.text


def test_provider_error_is_mapped_without_leaking(client, admin_headers, use_llm):
    class Boom:
        def invoke(self, *_):
            raise type("RateLimitError", (Exception,), {})("gsk_secret details")

    use_llm(Boom())
    r = post(client, admin_headers)
    assert r.status_code == 429 and "gsk_" not in r.text


def test_empty_answer_is_502(client, admin_headers, use_llm):
    use_llm(FakeListChatModel(responses=["   "]))
    assert post(client, admin_headers).status_code == 502


def test_long_answer_is_truncated(client, admin_headers, use_llm):
    use_llm(FakeListChatModel(responses=["x" * 5000]))
    assert len(post(client, admin_headers).json()["answer"]) == 2000