import datetime as dt
import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import get_db, require_role
from app.modules.forecasts import service
from app.modules.forecasts.schemas import ForecastResponse

# Admin-only and read-only. The model is loaded from disk, never trained here.
router = APIRouter(
    prefix="/forecasts", tags=["forecasts"], dependencies=[Depends(require_role("admin"))]
)


@router.get("", response_model=ForecastResponse)
def get_forecasts(
    forecast_date: dt.date | None = Query(None, alias="date"),
    location_id: uuid.UUID | None = None,
    product_id: uuid.UUID | None = None,
    db: Session = Depends(get_db),
):
    return service.get_forecast(db, forecast_date, location_id, product_id)