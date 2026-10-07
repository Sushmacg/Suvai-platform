from sqlalchemy import select

import app.db.all_models  # noqa: F401  (registers all models)
from app.core.config import settings
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.modules.users.models import User


def seed_admin() -> None:
    if not settings.ADMIN_PHONE or not settings.ADMIN_PASSWORD:
        print("ADMIN_PHONE / ADMIN_PASSWORD not set in .env. Skipping.")
        return

    with SessionLocal() as db:
        existing = db.scalar(select(User).where(User.phone == settings.ADMIN_PHONE))
        if existing:
            print("Admin already exists. Nothing to do.")
            return
        db.add(
            User(
                name=settings.ADMIN_NAME,
                phone=settings.ADMIN_PHONE,
                password_hash=hash_password(settings.ADMIN_PASSWORD),
                role="admin",
            )
        )
        db.commit()
        print("Admin created.")


if __name__ == "__main__":
    seed_admin()