"""Unit tests for authentication functionality."""
import pytest
from fastapi.testclient import TestClient
from app.core.security import verify_password, get_password_hash

def test_password_hashing():
    """Test password hashing and verification."""
    password = "testpassword123"
    hashed = get_password_hash(password)
    
    assert hashed != password
    assert verify_password(password, hashed)
    assert not verify_password("wrongpassword", hashed)

def test_user_registration(client: TestClient):
    """Test user registration endpoint."""
    user_data = {
        "email": "newuser@example.com",
        "password": "testpassword123",
        "full_name": "New User"
    }
    
    response = client.post("/api/auth/register", json=user_data)
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == user_data["email"]
    assert data["full_name"] == user_data["full_name"]
    assert "id" in data

def test_user_login(client: TestClient, test_user: dict):
    """Test user login endpoint."""
    response = client.post("/api/auth/login", data={
        "username": test_user["email"],
        "password": "testpassword123"
    })
    
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

def test_invalid_login(client: TestClient):
    """Test login with invalid credentials."""
    response = client.post("/api/auth/login", data={
        "username": "wrong@example.com",
        "password": "wrongpassword"
    })
    
    assert response.status_code == 401

def test_protected_route(client: TestClient, test_user_token: str):
    """Test access to protected route with valid token."""
    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {test_user_token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "email" in data
    assert "full_name" in data

def test_protected_route_no_token(client: TestClient):
    """Test access to protected route without token."""
    response = client.get("/api/auth/me")
    assert response.status_code == 401

def test_protected_route_invalid_token(client: TestClient):
    """Test access to protected route with invalid token."""
    response = client.get(
        "/api/auth/me",
        headers={"Authorization": "Bearer invalid_token"}
    )
    assert response.status_code == 401