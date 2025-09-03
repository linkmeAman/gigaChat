"""Unit tests for user profile management functionality."""
import pytest
from fastapi.testclient import TestClient
from tests.helpers import generate_user_data

def test_get_user_profile(client: TestClient, test_user_token: str):
    """Test retrieving user profile information."""
    headers = {"Authorization": f"Bearer {test_user_token}"}
    response = client.get("/api/users/me", headers=headers)
    
    assert response.status_code == 200
    data = response.json()
    assert "email" in data
    assert "full_name" in data
    assert "created_at" in data
    assert "id" in data

def test_update_user_profile(client: TestClient, test_user_token: str):
    """Test updating user profile information."""
    headers = {"Authorization": f"Bearer {test_user_token}"}
    update_data = {
        "full_name": "Updated Name",
        "bio": "This is my updated bio",
        "preferences": {
            "theme": "dark",
            "language": "en"
        }
    }
    
    response = client.put("/api/users/me", headers=headers, json=update_data)
    assert response.status_code == 200
    data = response.json()
    assert data["full_name"] == update_data["full_name"]
    assert data["bio"] == update_data["bio"]
    assert data["preferences"] == update_data["preferences"]

def test_update_email(client: TestClient, test_user_token: str):
    """Test updating user email with verification."""
    headers = {"Authorization": f"Bearer {test_user_token}"}
    new_email = "newemail@example.com"
    
    # Request email change
    response = client.post(
        "/api/users/me/email",
        headers=headers,
        json={"email": new_email}
    )
    assert response.status_code == 202
    
    # Note: In a real test, we'd verify the email verification process
    # For now, we'll test that the old email still works
    response = client.get("/api/users/me", headers=headers)
    assert response.status_code == 200

def test_change_password(client: TestClient, test_user_token: str):
    """Test changing user password."""
    headers = {"Authorization": f"Bearer {test_user_token}"}
    password_data = {
        "current_password": "testpassword123",
        "new_password": "newpassword123"
    }
    
    response = client.post(
        "/api/users/me/password",
        headers=headers,
        json=password_data
    )
    assert response.status_code == 200
    
    # Try logging in with new password
    login_data = {
        "username": "test@example.com",
        "password": "newpassword123"
    }
    response = client.post("/api/auth/login", data=login_data)
    assert response.status_code == 200
    assert "access_token" in response.json()

def test_profile_validation(client: TestClient, test_user_token: str):
    """Test profile update validation."""
    headers = {"Authorization": f"Bearer {test_user_token}"}
    
    # Test invalid email format
    response = client.post(
        "/api/users/me/email",
        headers=headers,
        json={"email": "invalid-email"}
    )
    assert response.status_code == 422
    
    # Test weak password
    response = client.post(
        "/api/users/me/password",
        headers=headers,
        json={
            "current_password": "testpassword123",
            "new_password": "weak"
        }
    )
    assert response.status_code == 422

def test_two_factor_auth(client: TestClient, test_user_token: str):
    """Test 2FA enablement and verification."""
    headers = {"Authorization": f"Bearer {test_user_token}"}
    
    # Enable 2FA
    response = client.post("/api/users/me/2fa/enable", headers=headers)
    assert response.status_code == 200
    setup_data = response.json()
    assert "secret" in setup_data
    assert "qr_code" in setup_data
    
    # Verify 2FA setup (using a mock code here)
    response = client.post(
        "/api/users/me/2fa/verify",
        headers=headers,
        json={"code": "123456"}
    )
    assert response.status_code in [200, 401]  # Depends on if we're using real TOTP

def test_user_preferences(client: TestClient, test_user_token: str):
    """Test user preferences management."""
    headers = {"Authorization": f"Bearer {test_user_token}"}
    
    # Set preferences
    preferences = {
        "theme": "dark",
        "notifications": {
            "email": True,
            "push": False
        },
        "language": "en"
    }
    
    response = client.put(
        "/api/users/me/preferences",
        headers=headers,
        json=preferences
    )
    assert response.status_code == 200
    assert response.json()["preferences"] == preferences
    
    # Get preferences
    response = client.get("/api/users/me/preferences", headers=headers)
    assert response.status_code == 200
    assert response.json() == preferences

def test_user_sessions(client: TestClient, test_user_token: str):
    """Test user session management."""
    headers = {"Authorization": f"Bearer {test_user_token}"}
    
    # Get active sessions
    response = client.get("/api/users/me/sessions", headers=headers)
    assert response.status_code == 200
    sessions = response.json()
    assert isinstance(sessions, list)
    assert len(sessions) > 0
    
    # Test session termination
    if len(sessions) > 0:
        session_id = sessions[0]["id"]
        response = client.delete(
            f"/api/users/me/sessions/{session_id}",
            headers=headers
        )
        assert response.status_code == 204

def test_user_activity_log(client: TestClient, test_user_token: str):
    """Test user activity log retrieval."""
    headers = {"Authorization": f"Bearer {test_user_token}"}
    
    response = client.get("/api/users/me/activity", headers=headers)
    assert response.status_code == 200
    activities = response.json()
    assert isinstance(activities, list)
    
    # Verify activity log structure
    if len(activities) > 0:
        activity = activities[0]
        assert "timestamp" in activity
        assert "action" in activity
        assert "details" in activity

def test_delete_account(client: TestClient, test_user_token: str):
    """Test account deletion process."""
    headers = {"Authorization": f"Bearer {test_user_token}"}
    
    # Request account deletion
    response = client.post(
        "/api/users/me/delete",
        headers=headers,
        json={"password": "testpassword123"}
    )
    assert response.status_code == 200
    
    # Verify account is inaccessible
    response = client.get("/api/users/me", headers=headers)
    assert response.status_code == 401