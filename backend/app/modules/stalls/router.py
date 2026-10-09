import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.core.deps import get_db, require_role
from app.modules.stalls import service
from app.modules.stalls.schemas import (
    CurrentStallResponse,
    LocationCreate,
    LocationResponse,
    LocationUpdate,
    NearestSessionResponse,
    SessionCreate,
    SessionResponse,
    SessionStatusUpdate,
    SessionUpdate,
)
from app.modules.users.models import User

router = APIRouter(prefix="/stalls", tags=["stalls"])


# ---------- Customer (public) ----------
@router.get("/current", response_model=CurrentStallResponse)
def current(db: Session = Depends(get_db)):
    state, session = service.current_session(db)
    return CurrentStallResponse(
        state=state,
        session=SessionResponse.model_validate(session) if session else None,
    )


@router.get("/today", response_model=list[SessionResponse])
def today(db: Session = Depends(get_db)):
    return service.todays_sessions(db)


@router.get("/upcoming", response_model=list[SessionResponse])
def upcoming(days: int = Query(7, ge=1, le=30), db: Session = Depends(get_db)):
    return service.upcoming_sessions(db, days)


@router.get("/nearest", response_model=list[NearestSessionResponse])
def nearest(
    lat: float = Query(ge=-90, le=90),
    lng: float = Query(ge=-180, le=180),
    limit: int = Query(5, ge=1, le=20),
    db: Session = Depends(get_db),
):
    results = []
    for distance, session in service.nearest_sessions(db, lat, lng, limit):
        base = SessionResponse.model_validate(session).model_dump()
        results.append(NearestSessionResponse(**base, distance_km=round(distance, 2)))
    return results


@router.get("/locations", response_model=list[LocationResponse])
def list_locations(db: Session = Depends(get_db)):
    return service.list_locations(db)


# ---------- Admin: locations ----------
@router.get("/locations/all", response_model=list[LocationResponse])
def admin_list_locations(
    _admin: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    return service.list_locations(db, include_inactive=True)


@router.post(
    "/locations", response_model=LocationResponse, status_code=status.HTTP_201_CREATED
)
def create_location(
    data: LocationCreate,
    _admin: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    return service.create_location(db, data)


@router.patch("/locations/{location_id}", response_model=LocationResponse)
def update_location(
    location_id: uuid.UUID,
    data: LocationUpdate,
    _admin: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    return service.update_location(db, location_id, data)


@router.delete("/locations/{location_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_location(
    location_id: uuid.UUID,
    _admin: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    service.deactivate_location(db, location_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------- Admin: sessions (schedules) ----------
@router.get("/sessions", response_model=list[SessionResponse])
def admin_list_sessions(
    start: date | None = None,
    end: date | None = None,
    _admin: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    return service.list_sessions(db, start, end)


@router.post(
    "/sessions", response_model=SessionResponse, status_code=status.HTTP_201_CREATED
)
def create_session(
    data: SessionCreate,
    _admin: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    return service.create_session(db, data)


@router.patch("/sessions/{session_id}", response_model=SessionResponse)
def update_session(
    session_id: uuid.UUID,
    data: SessionUpdate,
    _admin: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    return service.update_session(db, session_id, data)


@router.patch("/sessions/{session_id}/status", response_model=SessionResponse)
def change_session_status(
    session_id: uuid.UUID,
    data: SessionStatusUpdate,
    _admin: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    return service.change_status(db, session_id, data.status)


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session(
    session_id: uuid.UUID,
    _admin: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    service.delete_session(db, session_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
