import uuid
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ml import predict
from app.modules.products.models import Product
from app.modules.stalls.models import StallLocation
from app.modules.stalls.service import today_ist

MAX_ROWS = 30
NOTE = (
    "Units expected to sell. Capped by stock, so demand may be understated "
    "for products that sell out."
)

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "get_demand_forecast",
            "description": "Forecast of units to sell per product and stall location. Read-only.",
            "parameters": {
                "type": "object",
                "properties": {
                    "date": {
                        "type": ["string", "null"],
                        "description": "YYYY-MM-DD, today to 7 days ahead. Use null or omit for tomorrow.",
                    }
                },
                "required": [],
            },
        },
    }
]


def _names(db: Session, model, ids: set[str]) -> dict[str, str]:
    rows = db.execute(
        select(model.id, model.name).where(model.id.in_([uuid.UUID(i) for i in ids]))
    ).all()
    return {str(r.id): r.name for r in rows}


def get_demand_forecast(db: Session, date_str: str | None = None) -> dict:
    try:
        target = date.fromisoformat(date_str) if date_str else today_ist() + timedelta(days=1)
    except (TypeError, ValueError):
        return {"error": "date must be YYYY-MM-DD"}
    try:
        result = predict.forecast_demand(db, target)
    except predict.InvalidForecastRequest as exc:
        return {"error": str(exc)}
    except predict.ModelUnavailableError:
        return {"error": "the forecast model is not available"}
    if not result.rows:
        return {"error": "no forecast data is available"}

    rows = sorted(result.rows, key=lambda r: r["predicted_units"], reverse=True)
    shown = rows[:MAX_ROWS]
    products = _names(db, Product, {r["product_id"] for r in shown})
    locations = _names(db, StallLocation, {r["location_id"] for r in shown})
    return {
        "date": target.isoformat(),
        "total_predicted_units": round(sum(r["predicted_units"] for r in rows), 2),
        "rows_total": len(rows),
        "rows_shown": len(shown),
        "items": [
            {
                "product": products.get(r["product_id"], "unknown product"),
                "location": locations.get(r["location_id"], "unknown location"),
                "predicted_units": r["predicted_units"],
            }
            for r in shown
        ],
        "note": NOTE,
    }

from app.modules.analytics import service as analytics  # noqa: E402

BAD_DAYS = {"error": "days must be a whole number from 1 to 365"}
BAD_LIMIT = {"error": "limit must be a whole number from 1 to 10"}


def _whole(value, default, low, high):
    if value is None:
        return default
    if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
        raise ValueError
    return value


def get_business_summary(db: Session, args: dict) -> dict:
    try:
        days = _whole(args.get("days"), 30, 1, 365)
    except ValueError:
        return BAD_DAYS
    return {"days": days, "summary": analytics.summary(db, days)}


def get_top_products(db: Session, args: dict) -> dict:
    try:
        days = _whole(args.get("days"), 30, 1, 365)
    except ValueError:
        return BAD_DAYS
    try:
        limit = _whole(args.get("limit"), 5, 1, 10)
    except ValueError:
        return BAD_LIMIT
    return {"days": days, "products": analytics.products(db, days, limit)}


def _days_schema(extra=None):
    props = {"days": {"type": ["integer", "null"], "description": "1 to 365. Default 30."}}
    props.update(extra or {})
    return {"type": "object", "properties": props, "required": []}


TOOL_SCHEMAS.extend(
    [
        {
            "type": "function",
            "function": {
                "name": "get_business_summary",
                "description": "Revenue, orders and profit summary for the last N days. Read-only.",
                "parameters": _days_schema(),
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_top_products",
                "description": "Best-selling products for the last N days. Read-only.",
                "parameters": _days_schema(
                    {"limit": {"type": ["integer", "null"], "description": "1 to 10. Default 5."}}
                ),
            },
        },
    ]
)

HANDLERS = {
    "get_demand_forecast": lambda db, a: get_demand_forecast(db, a.get("date")),
    "get_business_summary": get_business_summary,
    "get_top_products": get_top_products,
}


def run_tool(db, name, args) -> dict:
    handler = HANDLERS.get(name)
    if handler is None or db is None:
        return {"error": "unknown tool"}
    return handler(db, args if isinstance(args, dict) else {})

from fastapi import HTTPException  # noqa: E402
from app.modules.expenses import service as expenses  # noqa: E402


def get_expense_summary(db: Session, args: dict) -> dict:
    try:
        days = _whole(args.get("days"), 30, 1, 365)
    except ValueError:
        return BAD_DAYS
    category = args.get("category")
    if category is not None and (not isinstance(category, str) or not 0 < len(category) <= 50):
        return {"error": "category must be a short text"}
    end = today_ist()
    start = end - timedelta(days=days - 1)
    try:
        result = expenses.summarize(db, category, start, end, None)
    except HTTPException as exc:
        return {"error": str(exc.detail)}
    if hasattr(result, "model_dump"):
        data = result.model_dump(mode="json")
    elif isinstance(result, dict):
        data = result
    else:
        return {"error": "expense data is not available"}
    return {"from": start.isoformat(), "to": end.isoformat(), "expenses": data}


TOOL_SCHEMAS.append(
    {
        "type": "function",
        "function": {
            "name": "get_expense_summary",
            "description": "Expense totals for the last N days, optionally for one category. Read-only.",
            "parameters": _days_schema(
                {"category": {"type": ["string", "null"], "description": "Optional category, e.g. fuel."}}
            ),
        },
    }
)
HANDLERS["get_expense_summary"] = get_expense_summary

from fastapi import HTTPException  # noqa: E402
from app.modules.expenses import service as expenses  # noqa: E402


def get_expense_summary(db: Session, args: dict) -> dict:
    try:
        days = _whole(args.get("days"), 30, 1, 365)
    except ValueError:
        return BAD_DAYS
    category = args.get("category")
    if category is not None and (not isinstance(category, str) or not 0 < len(category) <= 50):
        return {"error": "category must be a short text"}
    end = today_ist()
    start = end - timedelta(days=days - 1)
    try:
        result = expenses.summarize(db, category, start, end, None)
    except HTTPException as exc:
        return {"error": str(exc.detail)}
    if hasattr(result, "model_dump"):
        data = result.model_dump(mode="json")
    elif isinstance(result, dict):
        data = result
    else:
        return {"error": "expense data is not available"}
    return {"from": start.isoformat(), "to": end.isoformat(), "expenses": data}


TOOL_SCHEMAS.append(
    {
        "type": "function",
        "function": {
            "name": "get_expense_summary",
            "description": "Expense totals for the last N days, optionally for one category. Read-only.",
            "parameters": _days_schema(
                {"category": {"type": ["string", "null"], "description": "Optional category, e.g. fuel."}}
            ),
        },
    }
)
HANDLERS["get_expense_summary"] = get_expense_summary