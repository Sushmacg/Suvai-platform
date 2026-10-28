from typing import Literal

from pydantic import BaseModel, Field


class DeviceTokenRequest(BaseModel):
    token: str = Field(min_length=20, max_length=512)
    platform: Literal["android", "ios"] = "android"


class DispatchSummary(BaseModel):
    considered: int
    sent: int
    failed: int  # includes notifications with no registered device
    no_devices: int
    invalid_tokens_removed: int