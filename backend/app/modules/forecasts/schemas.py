import datetime as dt
import uuid

from pydantic import BaseModel


class ForecastItem(BaseModel):
    date: dt.date
    location_id: uuid.UUID
    product_id: uuid.UUID
    predicted_units: float


class ForecastResponse(BaseModel):
    model_version: str
    forecast_date: dt.date
    items: list[ForecastItem]