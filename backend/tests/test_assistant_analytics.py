import pytest
from langchain_core.messages import AIMessage

from app.ai import tools
from tests.test_assistant_tools import ScriptedLLM, ask, tool_call, tool_results, use_llm  # noqa: F401


def test_summary_tool_is_grounded(client, admin_headers, use_llm, monkeypatch):
    seen = {}

    def fake_summary(db, days):
        seen["days"] = days
        return {"revenue": 1200, "orders": 5}

    monkeypatch.setattr(tools.analytics, "summary", fake_summary)
    llm = ScriptedLLM(tool_call("get_business_summary", {"days": 7}), AIMessage(content="Revenue was 1200."))
    use_llm(llm)
    assert ask(client, admin_headers).status_code == 200
    result = tool_results(llm)[0]
    assert seen["days"] == 7 and result["days"] == 7 and result["summary"]["revenue"] == 1200


def test_top_products_tool(client, admin_headers, use_llm, monkeypatch):
    monkeypatch.setattr(tools.analytics, "products", lambda db, days, limit: [{"name": "Nankhatai", "limit": limit}])
    llm = ScriptedLLM(tool_call("get_top_products", {"limit": 3}), AIMessage(content="Nankhatai."))
    use_llm(llm)
    assert ask(client, admin_headers).status_code == 200
    assert tool_results(llm)[0]["products"][0]["limit"] == 3


def test_defaults_when_arguments_are_null(monkeypatch):
    monkeypatch.setattr(tools.analytics, "summary", lambda db, days: {"days_seen": days})
    out = tools.run_tool(object(), "get_business_summary", {"days": None})
    assert out["days"] == 30 and out["summary"] == {"days_seen": 30}


@pytest.mark.parametrize(
    "name,args",
    [
        ("get_business_summary", {"days": 0}),
        ("get_business_summary", {"days": 400}),
        ("get_business_summary", {"days": "7"}),
        ("get_business_summary", {"days": True}),
        ("get_top_products", {"limit": 50}),
    ],
)
def test_invalid_arguments_are_rejected(name, args, monkeypatch):
    def must_not_run(*a, **k):
        raise AssertionError("service must not be called")

    monkeypatch.setattr(tools.analytics, "summary", must_not_run)
    monkeypatch.setattr(tools.analytics, "products", must_not_run)
    assert "error" in tools.run_tool(object(), name, args)


def test_only_approved_tools_exist():
    names = {s["function"]["name"] for s in tools.TOOL_SCHEMAS}
    assert names == set(tools.HANDLERS) == {"get_demand_forecast", "get_business_summary", "get_top_products", "get_expense_summary"}