import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.main import app
from backend.database.database import Base, get_db
from backend.auth.auth_utils import add_user, get_admin_permissions

# Use an in-memory SQLite database for tests
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session")
def db_session():
    # Create the database tables
    Base.metadata.create_all(bind=engine)
    
    # Seed the admin user
    db = TestingSessionLocal()
    add_user(db, 'admin', 'admin', ['Admin'], get_admin_permissions())
    db.commit()
    db.close()
    
    yield
    
    # Drop tables after session
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db(db_session):
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="function", autouse=True)
def patch_sessionlocal(monkeypatch):
    import backend.main
    monkeypatch.setattr(backend.main, "SessionLocal", TestingSessionLocal)

@pytest.fixture(scope="function")
def client(db):
    def override_get_db():
        try:
            yield db
        finally:
            db.close()
            
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def auth_client(client):
    response = client.post("/login", data={"username": "admin", "password": "admin"})
    assert response.status_code == 200
    token = response.json()["access_token"]
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client
