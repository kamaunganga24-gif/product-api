# tests/conftest.py
import bcrypt

# 1. Fix missing __about__ attribute in modern bcrypt (bcrypt >= 4.0)
if not hasattr(bcrypt, "__about__"):
    class About:
        __version__ = bcrypt.__version__
    bcrypt.__about__ = About()

# 2. Patch bcrypt.hashpw to handle passwords > 72 bytes without raising ValueError
_original_hashpw = bcrypt.hashpw
def _patched_hashpw(password, salt):
    if isinstance(password, (bytes, bytearray)) and len(password) > 72:
        password = password[:72]
    return _original_hashpw(password, salt)

bcrypt.hashpw = _patched_hashpw

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from main import app, get_session

TEST_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})

@pytest.fixture(name="client")
def client_fixture():
    SQLModel.metadata.create_all(engine)
    def get_test_session():
        with Session(engine) as session:
            yield session
            
    app.dependency_overrides[get_session] = get_test_session
    yield TestClient(app)
    app.dependency_overrides.clear()
    SQLModel.metadata.drop_all(engine)

@pytest.fixture
def test_user():
    return {
        "username": "testuser",
        "email": "test@example.com",
        "password": "testpass123",
        "full_name": "Test User"
    }

@pytest.fixture
def auth_headers(client, test_user):
    client.post("/register", json=test_user)
    response = client.post("/login", data={"username": test_user["username"], "password": test_user["password"]})
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}