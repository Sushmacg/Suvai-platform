import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import get_db, require_role
from app.modules.event_log import service
from app.modules.event_log.schemas import EventLogResponse

# Admin-only, enforced once for the whole router.
router = APIRouter(
    prefix="/events",
    tags=["events"],
    dependencies=[Depends(require_role("admin"))],
)


@router.get("", response_model=list[EventLogResponse])
def list_events(
    event_type: str | None = Query(None, max_length=50),
    aggregate_id: uuid.UUID | None = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    return service.list_events(db, event_type, aggregate_id, limit, offset)
