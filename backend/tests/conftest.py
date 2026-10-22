import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.db.base import Base
from app.db.session import get_db
from app.api.deps import require_csrf, require_current_user
from app.main import app
from app.models import User


@pytest.fixture
def client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(dbapi_connection, _connection_record):
        dbapi_connection.execute("PRAGMA foreign_keys=ON")

    TestingSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    Base.metadata.create_all(engine)
    test_user = User(id="00000000-0000-0000-0000-000000000001", status="ACTIVE")
    with TestingSession() as db:
        db.add(test_user)
        db.commit()

    def override_get_db():
        with TestingSession() as db:
            yield db

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[require_current_user] = lambda: test_user
    app.dependency_overrides[require_csrf] = lambda: None
    test_client = TestClient(app)
    yield test_client
    test_client.close()
    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)


@pytest.fixture
def pet(client):
    response = client.post("/api/v1/pets", json={"name": "Mochi", "species": "cat"})
    assert response.status_code == 201
    return response.json()


@pytest.fixture
def demo_db(tmp_path):
    database_path = tmp_path / "relapaw-demo.db"
    demo_engine = create_engine(f"sqlite:///{database_path}")

    @event.listens_for(demo_engine, "connect")
    def enable_demo_foreign_keys(dbapi_connection, _connection_record):
        dbapi_connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(demo_engine)
    with demo_engine.begin() as connection:
        connection.execute(text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)"))
        connection.execute(text("INSERT INTO alembic_version VALUES ('20261021_0018')"))
    yield sessionmaker(bind=demo_engine, expire_on_commit=False), tmp_path / "manifest.json"
    demo_engine.dispose()
