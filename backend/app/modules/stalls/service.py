import math
import uuid
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.modules.stalls.models import StallLocation, StallSession
from app.modules.stalls.schemas import (
    LocationCreate,
    LocationUpdate,
    SessionCreate,
    SessionUpdate,
)

IST = ZoneInfo("Asia/Kolkata")
ACTIVE_STATUSES = ("scheduled", "open")

# Allowed status changes: current status -> new statuses
ALLOWED_TRANSITIONS = {
    "scheduled": {"open", "cancelled"},
    "open": {"closed"},
}

SLOT_TAKEN = "A session already exists for this location, date and start time"
ANOTHER_OPEN = "Another session is already open. Close it first."


def today_ist() -> date:
    return datetime.now(IST).date()


# ---------------- Locations ----------------
def list_locations(db: Session, include_inactive: bool = False) -> list[StallLocation]:
    query = select(StallLocation).order_by(StallLocation.name)
    if not include_inactive:
        query = query.where(StallLocation.is_active.is_(True))
    return list(db.scalars(query).all())


def get_location(
    db: Session, location_id: uuid.UUID, include_inactive: bool = False
) -> StallLocation:
    location = db.get(StallLocation, location_id)
    if not location or (not include_inactive and not location.is_active):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Location not found")
    return location


def create_location(db: Session, data: LocationCreate) -> StallLocation:
    location = StallLocation(**data.model_dump())
    db.add(location)
    db.commit()
    db.refresh(location)
    return location


def _ensure_no_upcoming_sessions(db: Session, location: StallLocation) -> None:
    upcoming = db.scalar(
        select(StallSession.id).where(
            StallSession.location_id == location.id,
            StallSession.status.in_(ACTIVE_STATUSES),
            StallSession.session_date >= today_ist(),
        )
    )
    if upcoming:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Location has upcoming sessions. Cancel or close them first.",
        )


def update_location(
    db: Session, location_id: uuid.UUID, data: LocationUpdate
) -> StallLocation:
    location = get_location(db, location_id, include_inactive=True)
    changes = data.model_dump(exclude_unset=True)
    if changes.get("is_active") is False:
        _ensure_no_upcoming_sessions(db, location)
    for field, value in changes.items():
        if value is None and field in ("name", "latitude", "longitude", "is_active"):
            continue  # required fields cannot be cleared
        setattr(location, field, value)
    db.commit()
    db.refresh(location)
    return location


def deactivate_location(db: Session, location_id: uuid.UUID) -> None:
    location = get_location(db, location_id, include_inactive=True)
    _ensure_no_upcoming_sessions(db, location)
    location.is_active = False
    db.commit()


# ---------------- Sessions ----------------
def _session_query():
    return select(StallSession).options(joinedload(StallSession.location))


def get_session(db: Session, session_id: uuid.UUID) -> StallSession:
    session = db.scalar(_session_query().where(StallSession.id == session_id))
    if not session:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Session not found")
    return session


def _ensure_slot_free(
    db: Session,
    location_id: uuid.UUID,
    session_date: date,
    start_time: time,
    ignore_id: uuid.UUID | None = None,
) -> None:
    query = select(StallSession.id).where(
        StallSession.location_id == location_id,
        StallSession.session_date == session_date,
        StallSession.start_time == start_time,
    )
    if ignore_id:
        query = query.where(StallSession.id != ignore_id)
    if db.scalar(query):
        raise HTTPException(status.HTTP_409_CONFLICT, SLOT_TAKEN)


def create_session(db: Session, data: SessionCreate) -> StallSession:
    get_location(db, data.location_id)  # must exist and be active
    if data.session_date < today_ist():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Session date is in the past")
    _ensure_slot_free(db, data.location_id, data.session_date, data.start_time)

    session = StallSession(**data.model_dump())
    db.add(session)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, SLOT_TAKEN)
    return get_session(db, session.id)


def update_session(db: Session, session_id: uuid.UUID, data: SessionUpdate) -> StallSession:
    session = get_session(db, session_id)
    if session.status != "scheduled":
        raise HTTPException(status.HTTP_409_CONFLICT, "Only scheduled sessions can be edited")

    changes = data.model_dump(exclude_unset=True)
    for field in ("location_id", "session_date", "start_time", "end_time"):
        if field in changes and changes[field] is None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"{field} cannot be empty")

    if "location_id" in changes:
        get_location(db, changes["location_id"])

    new_location = changes.get("location_id", session.location_id)
    new_date = changes.get("session_date", session.session_date)
    new_start = changes.get("start_time", session.start_time)
    new_end = changes.get("end_time", session.end_time)

    if new_end <= new_start:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "end_time must be after start_time")
    if "session_date" in changes and new_date < today_ist():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Session date is in the past")
    _ensure_slot_free(db, new_location, new_date, new_start, ignore_id=session.id)

    for field, value in changes.items():
        setattr(session, field, value)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, SLOT_TAKEN)
    return get_session(db, session_id)


def delete_session(db: Session, session_id: uuid.UUID) -> None:
    session = get_session(db, session_id)
    if session.status not in ("scheduled", "cancelled"):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Open or closed sessions are kept as history and cannot be deleted",
        )
    db.delete(session)
    db.commit()


def change_status(db: Session, session_id: uuid.UUID, new_status: str) -> StallSession:
    session = get_session(db, session_id)
    if new_status not in ALLOWED_TRANSITIONS.get(session.status, set()):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Cannot change a '{session.status}' session to '{new_status}'",
        )
    if new_status == "open":
        other_open = db.scalar(
            select(StallSession.id).where(
                StallSession.status == "open", StallSession.id != session.id
            )
        )
        if other_open:
            raise HTTPException(status.HTTP_409_CONFLICT, ANOTHER_OPEN)
    session.status = new_status
    try:
        db.commit()
    except IntegrityError:  # two requests raced; PostgreSQL's one-open index caught it
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, ANOTHER_OPEN)
    return get_session(db, session_id)


def list_sessions(
    db: Session,
    start: date | None = None,
    end: date | None = None,
    active_only: bool = False,
) -> list[StallSession]:
    query = _session_query().order_by(StallSession.session_date, StallSession.start_time)
    if start:
        query = query.where(StallSession.session_date >= start)
    if end:
        query = query.where(StallSession.session_date <= end)
    if active_only:
        query = query.where(StallSession.status.in_(ACTIVE_STATUSES))
    return list(db.scalars(query).all())


def todays_sessions(db: Session) -> list[StallSession]:
    today = today_ist()
    return list_sessions(db, today, today, active_only=True)


def upcoming_sessions(db: Session, days: int) -> list[StallSession]:
    today = today_ist()
    return list_sessions(db, today, today + timedelta(days=days), active_only=True)


def current_session(db: Session) -> tuple[str, StallSession | None]:
    """The open session if there is one, otherwise the next scheduled one."""
    open_session = db.scalar(_session_query().where(StallSession.status == "open"))
    if open_session:
        return "open", open_session

    now = datetime.now(IST)
    for session in list_sessions(db, start=now.date(), active_only=True):
        ended_today = session.session_date == now.date() and session.end_time <= now.time()
        if session.status == "scheduled" and not ended_today:
            return "upcoming", session
    return "none", None


# ---------------- Nearest stall ----------------
def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Straight-line distance between two coordinates, in kilometres."""
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    d_phi = p2 - p1
    d_lambda = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(d_lambda / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def nearest_sessions(
    db: Session, lat: float, lng: float, limit: int, days: int = 7
) -> list[tuple[float, StallSession]]:
    sessions = upcoming_sessions(db, days)
    ranked = [
        (haversine_km(lat, lng, s.location.latitude, s.location.longitude), s)
        for s in sessions
    ]
    ranked.sort(key=lambda pair: pair[0])
    return ranked[:limit]
