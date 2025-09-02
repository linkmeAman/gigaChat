"""Test configuration and fixtures for the entire test suite."""
import os
import asyncio
import pytest
from typing import AsyncGenerator
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from httpx import AsyncClient
from app.core.database import Base
from app.main import app
from tests.config import test_settings
from app.core.database import get_db

# Set test environment
os.environ["ENV_FILE"] = ".env.test"

# Create async engine
test_engine = create_async_engine(
    test_settings.DATABASE_URL,
    echo=True,
)

# Create async session maker
async_session = AsyncSession(bind=test_engine, expire_on_commit=False)

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for testing."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def test_db():
    """Create test database tables."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.fixture
async def db_session(test_db) -> AsyncGenerator[AsyncSession, None]:
    """Create a fresh database session for each test."""
    try:
        yield async_session
        await async_session.rollback()  # Rollback any changes after the test
    finally:
        await async_session.close()  # Clean up the session

@pytest.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create a test client with a clean database session."""
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        async with AsyncClient(app=app, base_url="http://test") as ac:
            yield ac
    finally:
        app.dependency_overrides.clear()

@pytest.fixture
async def auth_user(client: AsyncClient) -> dict:
    """Create a test user for authentication."""
    user_data = {
        "email": test_settings.TEST_USER_EMAIL,
        "password": test_settings.TEST_USER_PASSWORD,
        "username": test_settings.TEST_USER_NAME
    }
    response = await client.post("/api/auth/register", json=user_data)
    assert response.status_code == 201, f"Failed to create test user: {response.text}"
    
    # Return both user data and response data
    response_data = response.json()
    return {**user_data, **response_data}

@pytest.fixture
async def auth_token(client: AsyncClient, auth_user: dict) -> str:
    """Get authentication token for test user."""
    response = await client.post("/api/auth/login", data={
        "username": auth_user["email"],
        "password": test_settings.TEST_USER_PASSWORD
    })
    assert response.status_code == 200, f"Failed to login test user: {response.text}"
    token_data = response.json()
    return token_data["access_token"]

@pytest.fixture
def test_user(client: TestClient):
    """Create a test user."""
    user_data = {
        "email": "test@example.com",
        "password": "testpassword123",
        "username": "testuser"
    }
    response = client.post("/signup", json=user_data)
    assert response.status_code == 200
    
    # Return both user data and response data
    response_data = response.json()
    user_data.update(response_data)
    return user_data

@pytest.fixture
def test_user_token(client: TestClient, test_user: dict) -> str:
    """Get authentication token for test user."""
    response = client.post("/login", data={
        "username": test_user["email"],
        "password": "testpassword123"
    })
    assert response.status_code == 200
    return response.json()["access_token"]