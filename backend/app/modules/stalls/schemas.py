import uuid
from datetime import date, time
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class LocationCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    address: str | None = Field(default=None, max_length=300)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    google_place_id: str | None = Field(default=None, max_length=255)


class LocationUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    address: str | None = Field(default=None, max_length=300)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    google_place_id: str | None = Field(default=None, max_length=255)
    is_active: bool | None = None


class LocationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    address: str | None
    latitude: float
    longitude: float
    google_place_id: str | None
    is_active: bool


class SessionCreate(BaseModel):
    location_id: uuid.UUID
    session_date: date
    start_time: time
    end_time: time
    notes: str | None = None

    @model_validator(mode="after")
    def check_times(self):
        if self.end_time <= self.start_time:
            raise ValueError("end_time must be after start_time")
        return self


class SessionUpdate(BaseModel):
    location_id: uuid.UUID | None = None
    session_date: date | None = None
    start_time: time | None = None
    end_time: time | None = None
    notes: str | None = None


class SessionStatusUpdate(BaseModel):
    status: Literal["open", "closed", "cancelled"]


class SessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    session_date: date
    start_time: time
    end_time: time
    status: str
    notes: str | None
    location: LocationResponse


class NearestSessionResponse(SessionResponse):
    distance_km: float


class CurrentStallResponse(BaseModel):
    state: Literal["open", "upcoming", "none"]
    session: SessionResponse | None = None
