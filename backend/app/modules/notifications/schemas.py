import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

Audience = Literal["user", "admins", "all_customers"]
NotificationStatus = Literal["pending", "sent", "failed"]


class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    event_type: str
    audience: str
    title: str
    body: str
    status: str
    created_at: datetime


class NotificationAdminResponse(NotificationResponse):
    event_id: uuid.UUID | None
    user_id: uuid.UUID | None
    sent_at: datetime | None
