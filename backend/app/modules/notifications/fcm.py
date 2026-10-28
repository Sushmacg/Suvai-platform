"""Send push messages through Firebase Cloud Messaging (HTTP v1 API)."""

import logging
from dataclasses import dataclass
from typing import Protocol

import requests

from app.core.config import settings

logger = logging.getLogger(__name__)

FCM_SCOPE = "https://www.googleapis.com/auth/firebase.messaging"


@dataclass(frozen=True)
class SendResult:
    ok: bool
    invalid_token: bool = False
    error: str | None = None


class PushSender(Protocol):
    def send(
        self, token: str, title: str, body: str, data: dict[str, str] | None = None
    ) -> SendResult: ...


class FcmSender:
    def __init__(self, credentials_file: str):
        from google.oauth2 import service_account

        self._creds = service_account.Credentials.from_service_account_file(
            credentials_file, scopes=[FCM_SCOPE]
        )
        self._url = (
            f"https://fcm.googleapis.com/v1/projects/{self._creds.project_id}/messages:send"
        )

    def _access_token(self) -> str:
        from google.auth.transport.requests import Request

        if not self._creds.valid:
            self._creds.refresh(Request())
        return self._creds.token

    def send(
        self, token: str, title: str, body: str, data: dict[str, str] | None = None
    ) -> SendResult:
        payload = {
            "message": {
                "token": token,
                "notification": {"title": title, "body": body},
                "data": data or {},
            }
        }
        try:
            response = requests.post(
                self._url,
                json=payload,
                headers={"Authorization": f"Bearer {self._access_token()}"},
                timeout=10,
            )
        except Exception as exc:  # network or credential problems
            return SendResult(ok=False, error=str(exc)[:200])
        if response.status_code == 200:
            return SendResult(ok=True)
        # Only a token Google says is gone is treated as invalid.
        gone = response.status_code == 404 or "UNREGISTERED" in response.text
        return SendResult(
            ok=False,
            invalid_token=gone,
            error=f"HTTP {response.status_code}: {response.text[:150]}",
        )


_sender: PushSender | None = None
_loaded = False


def get_push_sender() -> PushSender | None:
    """FastAPI dependency. None when FCM is off or credentials are missing."""
    global _sender, _loaded
    if not _loaded:
        _loaded = True
        if settings.FCM_ENABLED and settings.FCM_CREDENTIALS_FILE:
            try:
                _sender = FcmSender(settings.FCM_CREDENTIALS_FILE)
            except Exception:
                logger.exception("FCM credentials could not be loaded")
    return _sender