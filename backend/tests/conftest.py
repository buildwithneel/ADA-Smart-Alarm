from __future__ import annotations

import os
import uuid
from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

# Force testing environment
os.environ["ENVIRONMENT"] = "testing"

from app.api.deps import get_db
from app.main import app as fastapi_app
from app.models.base import Base
from app.models.preference import UserPreference
from app.models.user import User

# In-memory SQLite database isolated per test session
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(autouse=True)
def test_environment_cleanup():
    from app.services.weather.weather_service import clear_weather_cache
    clear_weather_cache()
    yield
    clear_weather_cache()


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def test_user(db_session: Session) -> User:
    user = User(
        id=uuid.uuid4(),
        firebase_uid="test-user-firebase-uid-001",
        email="tester@ada-alarm.com",
        name="ADA Test User",
        timezone="America/New_York",
        is_active=True,
    )
    db_session.add(user)
    db_session.flush()

    pref = UserPreference(
        user_id=user.id,
        default_transportation="driving",
        default_preparation_time=25,
        default_safety_buffer=10,
    )
    db_session.add(pref)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def client(db_session: Session, test_user: User) -> Generator[TestClient, None, None]:
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    fastapi_app.dependency_overrides[get_db] = override_get_db

    # Default client with Bearer auth for test_user
    default_headers = {
        "Authorization": f"Bearer test-token:{test_user.firebase_uid}:{test_user.email}:{test_user.name}"
    }

    with TestClient(fastapi_app, headers=default_headers) as test_client:
        yield test_client

    fastapi_app.dependency_overrides.clear()


@pytest.fixture
def unauthenticated_client(db_session: Session) -> Generator[TestClient, None, None]:
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    fastapi_app.dependency_overrides[get_db] = override_get_db

    with TestClient(fastapi_app) as test_client:
        yield test_client

    fastapi_app.dependency_overrides.clear()
