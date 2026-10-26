import json
import uuid

import pytest
from langchain_core.messages import AIMessage, ToolMessage

from app.ai import router as ai_router
from app.ai import tools
from app.ml import predict
from tests.conftest import PREFIX

URL = f"{PREFIX}/assistant/chat"


class ScriptedLLM:
    def __init__(self, *replies):
        self.replies = list(replies)
        self.seen = []

    def bind_tools(self, schemas):
        return self

    def invoke(self, messages):
        self.seen.append(list(messages))
        return self.replies.pop(0)


def tool_call(name="get_demand_forecast", args=None):
    return AIMessage(content="", tool_calls=[{"name": name, "args": args or {}, "id": "c1"}])


def fake_forecast(db, target_date, *a, **k):
    rows = [
        {"date": target_date, "location_id": str(uuid.uuid4()),
         "product_id": str(uuid.uuid4()), "predicted_units": 4.25}
    ]
    return predict.ForecastResult("v-test", rows)


@pytest.fixture
def use_llm(client):
    def _use(llm):
        client.app.dependency_overrides[ai_router.get_llm] = lambda: llm

    yield _use
    client.app.dependency_overrides.pop(ai_router.get_llm, None)


def ask(client, headers):
    return client.post(URL, json={"question": "Demand tomorrow?"}, headers=headers)


def tool_results(llm):
    return [json.loads(m.content) for m in llm.seen[-1] if isinstance(m, ToolMessage)]


def test_answer_is_grounded_in_tool_result(client, admin_headers, use_llm, monkeypatch):
    monkeypatch.setattr(predict, "forecast_demand", fake_forecast)
    llm = ScriptedLLM(tool_call(), AIMessage(content="About 4 units."))
    use_llm(llm)
    r = ask(client, admin_headers)
    assert r.status_code == 200 and r.json()["answer"] == "About 4 units."
    result = tool_results(llm)[0]
    assert result["items"][0]["predicted_units"] == 4.25
    assert "location_id" not in result["items"][0] and "note" in result


def test_forecast_error_is_passed_on_as_unavailable(client, admin_headers, use_llm, monkeypatch):
    def boom(*a, **k):
        raise predict.ModelUnavailableError(r"C:\secret\latest.json")

    monkeypatch.setattr(predict, "forecast_demand", boom)
    llm = ScriptedLLM(tool_call(), AIMessage(content="Forecast data is unavailable."))
    use_llm(llm)
    assert ask(client, admin_headers).status_code == 200
    result = tool_results(llm)[0]
    assert "error" in result and "secret" not in json.dumps(result)


def test_unknown_tool_is_refused(client, admin_headers, use_llm):
    llm = ScriptedLLM(tool_call("run_sql", {"q": "drop table users"}), AIMessage(content="No."))
    use_llm(llm)
    assert ask(client, admin_headers).status_code == 200
    assert tool_results(llm)[0] == {"error": "unknown tool"}


def test_bad_date_argument_is_an_error(client, admin_headers, use_llm):
    llm = ScriptedLLM(tool_call(args={"date": "tomorrow-ish"}), AIMessage(content="Bad date."))
    use_llm(llm)
    assert ask(client, admin_headers).status_code == 200
    assert "error" in tool_results(llm)[0]


def test_endless_tool_calls_are_stopped(client, admin_headers, use_llm, monkeypatch):
    monkeypatch.setattr(predict, "forecast_demand", fake_forecast)
    use_llm(ScriptedLLM(*[tool_call() for _ in range(10)]))
    assert ask(client, admin_headers).status_code == 502
def test_date_argument_accepts_null():
    date_schema = tools.TOOL_SCHEMAS[0]["function"]["parameters"]["properties"]["date"]
    assert "null" in date_schema["type"]
