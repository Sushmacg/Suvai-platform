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