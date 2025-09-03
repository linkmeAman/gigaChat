"""Unit tests for conversation management functionality."""
import pytest
from fastapi.testclient import TestClient
from tests.helpers import create_test_conversation

def test_conversation_creation_validation(client: TestClient, test_user_token: str):
    """Test conversation creation with invalid data."""
    headers = {"Authorization": f"Bearer {test_user_token}"}
    
    # Test empty title
    response = client.post(
        "/api/conversations",
        headers=headers,
        json={"title": ""}
    )
    assert response.status_code == 422
    
    # Test missing title
    response = client.post(
        "/api/conversations",
        headers=headers,
        json={}
    )
    assert response.status_code == 422

def test_conversation_update(client: TestClient, test_user_token: str):
    """Test updating conversation details."""
    conv = create_test_conversation(client, test_user_token)
    headers = {"Authorization": f"Bearer {test_user_token}"}
    
    new_title = "Updated Test Conversation"
    response = client.put(
        f"/api/conversations/{conv['id']}",
        headers=headers,
        json={"title": new_title}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == new_title
    assert data["id"] == conv["id"]

def test_conversation_permissions(client: TestClient, test_user_token: str):
    """Test that users can only access their own conversations."""
    # Create a conversation as first user
    conv = create_test_conversation(client, test_user_token)
    
    # Create second user
    user2_data = {
        "email": "user2@example.com",
        "password": "testpassword123",
        "full_name": "Test User 2"
    }
    client.post("/api/auth/register", json=user2_data)
    
    # Login as second user
    response = client.post("/api/auth/login", data={
        "username": user2_data["email"],
        "password": user2_data["password"]
    })
    user2_token = response.json()["access_token"]
    
    # Try to access first user's conversation
    headers = {"Authorization": f"Bearer {user2_token}"}
    response = client.get(f"/api/conversations/{conv['id']}", headers=headers)
    assert response.status_code == 403

def test_conversation_pagination(client: TestClient, test_user_token: str):
    """Test conversation listing pagination."""
    headers = {"Authorization": f"Bearer {test_user_token}"}
    
    # Create multiple conversations
    for i in range(15):  # Assuming page size is 10
        create_test_conversation(client, test_user_token)
    
    # Get first page
    response = client.get("/api/conversations?page=1&size=10", headers=headers)
    assert response.status_code == 200
    first_page = response.json()
    assert len(first_page) == 10
    
    # Get second page
    response = client.get("/api/conversations?page=2&size=10", headers=headers)
    assert response.status_code == 200
    second_page = response.json()
    assert len(second_page) > 0
    
    # Verify pages contain different conversations
    first_page_ids = {conv["id"] for conv in first_page}
    second_page_ids = {conv["id"] for conv in second_page}
    assert not first_page_ids.intersection(second_page_ids)

def test_conversation_search(client: TestClient, test_user_token: str):
    """Test searching conversations by title."""
    headers = {"Authorization": f"Bearer {test_user_token}"}
    
    # Create conversations with specific titles
    titles = ["Python Chat", "JavaScript Discussion", "Python Projects"]
    for title in titles:
        client.post(
            "/api/conversations",
            headers=headers,
            json={"title": title}
        )
    
    # Search for Python conversations
    response = client.get("/api/conversations?search=Python", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 2
    assert all("Python" in conv["title"] for conv in data)
    
    # Search for JavaScript conversations
    response = client.get("/api/conversations?search=JavaScript", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert all("JavaScript" in conv["title"] for conv in data)

def test_conversation_sorting(client: TestClient, test_user_token: str):
    """Test conversation sorting options."""
    headers = {"Authorization": f"Bearer {test_user_token}"}
    
    # Create conversations
    for title in ["A Chat", "B Chat", "C Chat"]:
        client.post(
            "/api/conversations",
            headers=headers,
            json={"title": title}
        )
    
    # Test ascending sort
    response = client.get("/api/conversations?sort=title&order=asc", headers=headers)
    assert response.status_code == 200
    asc_data = response.json()
    assert asc_data[0]["title"] < asc_data[-1]["title"]
    
    # Test descending sort
    response = client.get("/api/conversations?sort=title&order=desc", headers=headers)
    assert response.status_code == 200
    desc_data = response.json()
    assert desc_data[0]["title"] > desc_data[-1]["title"]

def test_bulk_conversation_deletion(client: TestClient, test_user_token: str):
    """Test deleting multiple conversations at once."""
    headers = {"Authorization": f"Bearer {test_user_token}"}
    
    # Create conversations
    conv_ids = []
    for _ in range(3):
        conv = create_test_conversation(client, test_user_token)
        conv_ids.append(conv["id"])
    
    # Delete conversations in bulk
    response = client.post(
        "/api/conversations/bulk-delete",
        headers=headers,
        json={"conversation_ids": conv_ids}
    )
    assert response.status_code == 204
    
    # Verify all conversations are deleted
    for conv_id in conv_ids:
        response = client.get(f"/api/conversations/{conv_id}", headers=headers)
        assert response.status_code == 404