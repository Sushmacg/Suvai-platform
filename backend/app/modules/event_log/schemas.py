import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class EventLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    event_type: str
    aggregate_id: uuid.UUID | None
    payload: dict[str, Any]
    occurred_at: datetime
