from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db, require_role
from app.modules.users.models import User
from app.modules.users.schemas import UserResponse

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserResponse)
def read_me(user: User = Depends(get_current_user)):
    return user


@router.get("", response_model=list[UserResponse])
def list_users(
    _admin: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    return db.scalars(select(User).order_by(User.created_at)).all()


# ---- RBAC verification endpoints (safe to keep or remove later) ----
@router.get("/admin-check")
def admin_check(user: User = Depends(require_role("admin"))):
    return {"message": "Admin access granted", "role": user.role}


@router.get("/customer-check")
def customer_check(user: User = Depends(require_role("customer"))):
    return {"message": "Customer access granted", "role": user.role}
