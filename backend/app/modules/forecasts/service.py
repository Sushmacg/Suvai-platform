import datetime as dt
import logging
import uuid
from datetime import timedelta

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.ml import predict
from app.modules.stalls.service import today_ist

log = logging.getLogger(__name__)


def get_forecast(
    db: Session,
    target_date: dt.date | None = None,
    location_id: uuid.UUID | None = None,
    product_id: uuid.UUID | None = None,
) -> dict:
    target = target_date or today_ist() + timedelta(days=1)
    try:
        result = predict.forecast_demand(
            db,
            target,
            [str(location_id)] if location_id else None,
            [str(product_id)] if product_id else None,
        )
    except predict.InvalidForecastRequest as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc))
    except predict.ModelUnavailableError as exc:
        log.warning("Forecast model unavailable: %s", exc)
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "The forecast model is not available. Train it first.",
        )
    return {"model_version": result.model_version, "forecast_date": target, "items": result.rows}