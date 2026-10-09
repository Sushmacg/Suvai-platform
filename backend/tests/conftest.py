import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.db.all_models  # noqa: F401  (registers all models)
from app.core.config import settings
from app.core.deps import get_db
from app.core.security import hash_password
from app.db.base import Base
from app.main import app
from app.modules.users.models import User

PREFIX = settings.API_V1_PREFIX
TEST_DB_URL = settings.DATABASE_URL.rsplit("/", 1)[0] + "/suvai_test"
PASSWORD = "password123"

engine = create_engine(TEST_DB_URL)
TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)


@pytest.fixture(autouse=True)
def fresh_database():
    # Safety: never wipe anything except the dedicated test database.
    assert TEST_DB_URL.endswith("/suvai_test")
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield


@pytest.fixture
def client():
    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


def _headers_for(client, phone: str, role: str) -> dict:
    with TestingSession() as db:
        db.add(
            User(
                name=f"Test {role}",
                phone=phone,
                password_hash=hash_password(PASSWORD),
                role=role,
            )
        )
        db.commit()
    response = client.post(
        f"{PREFIX}/auth/login", json={"phone": phone, "password": PASSWORD}
    )
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture
def admin_headers(client):
    return _headers_for(client, "9000000001", "admin")


@pytest.fixture
def customer_headers(client):
    return _headers_for(client, "9000000002", "customer")
