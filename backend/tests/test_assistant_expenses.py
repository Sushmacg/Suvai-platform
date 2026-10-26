import pytest
from fastapi import HTTPException

from app.ai import tools
from app.modules.stalls.service import today_ist


class FakeSummary:
    def model_dump(self, mode="json"):
        return {"total": "250.00", "count": 2}


def test_summary_uses_the_requested_window(monkeypatch):
    seen = {}

    def fake(db, category, start, end, session_id):
        seen.update(category=category, start=start, end=end, session_id=session_id)
        return FakeSummary()

    monkeypatch.setattr(tools.expenses, "summarize", fake)
    out = tools.run_tool(object(), "get_expense_summary", {"days": 7, "category": "fuel"})
    assert out["expenses"] == {"total": "250.00", "count": 2}
    assert seen["category"] == "fuel" and seen["session_id"] is None
    assert seen["end"] == today_ist() and (seen["end"] - seen["start"]).days == 6


def test_defaults_to_30_days(monkeypatch):
    monkeypatch.setattr(tools.expenses, "summarize", lambda *a: FakeSummary())
    out = tools.run_tool(object(), "get_expense_summary", {"days": None, "category": None})
    assert (today_ist() - __import__("datetime").date.fromisoformat(out["from"])).days == 29


@pytest.mark.parametrize("args", [{"days": 0}, {"days": 999}, {"category": "x" * 60}, {"category": 5}])
def test_invalid_arguments_never_reach_the_service(args, monkeypatch):
    def must_not_run(*a):
        raise AssertionError("service must not be called")

    monkeypatch.setattr(tools.expenses, "summarize", must_not_run)
    assert "error" in tools.run_tool(object(), "get_expense_summary", args)


def test_service_errors_become_tool_errors(monkeypatch):
    def boom(*a):
        raise HTTPException(400, "bad range")

    monkeypatch.setattr(tools.expenses, "summarize", boom)
    assert tools.run_tool(object(), "get_expense_summary", {}) == {"error": "bad range"}