"""Unit tests for chat functionality."""
import pytest
from fastapi.testclient import TestClient
from app.core.ai import sanitize_input, format_response
from tests.helpers import create_test_conversation, create_test_message

def test_create_conversation(client: TestClient, test_user_token: str):
    """Test creating a new conversation."""
    headers = {"Authorization": f"Bearer {test_user_token}"}
    response = client.post(
        "/api/conversations",
        headers=headers,
        json={"title": "Test Chat"}
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Test Chat"
    assert "id" in data
    assert "created_at" in data

def test_list_conversations(client: TestClient, test_user_token: str):
    """Test listing user's conversations."""
    # Create a few conversations first
    headers = {"Authorization": f"Bearer {test_user_token}"}
    for i in range(3):
        create_test_conversation(client, test_user_token)
    
    response = client.get("/api/conversations", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 3
    assert all("id" in conv for conv in data)
    assert all("title" in conv for conv in data)

def test_get_conversation(client: TestClient, test_user_token: str):
    """Test getting a specific conversation."""
    conv = create_test_conversation(client, test_user_token)
    headers = {"Authorization": f"Bearer {test_user_token}"}
    
    response = client.get(f"/api/conversations/{conv['id']}", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == conv["id"]
    assert data["title"] == conv["title"]

def test_delete_conversation(client: TestClient, test_user_token: str):
    """Test deleting a conversation."""
    conv = create_test_conversation(client, test_user_token)
    headers = {"Authorization": f"Bearer {test_user_token}"}
    
    response = client.delete(f"/api/conversations/{conv['id']}", headers=headers)
    assert response.status_code == 204
    
    # Verify it's deleted
    response = client.get(f"/api/conversations/{conv['id']}", headers=headers)
    assert response.status_code == 404

def test_send_message(client: TestClient, test_user_token: str):
    """Test sending a message in a conversation."""
    conv = create_test_conversation(client, test_user_token)
    headers = {"Authorization": f"Bearer {test_user_token}"}
    
    message_content = "Hello, this is a test message!"
    response = client.post(
        f"/api/conversations/{conv['id']}/messages",
        headers=headers,
        json={"content": message_content}
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["content"] == message_content
    assert "id" in data
    assert "created_at" in data

def test_get_conversation_messages(client: TestClient, test_user_token: str):
    """Test retrieving messages from a conversation."""
    conv = create_test_conversation(client, test_user_token)
    headers = {"Authorization": f"Bearer {test_user_token}"}
    
    # Send multiple messages
    messages = ["Message 1", "Message 2", "Message 3"]
    for msg in messages:
        create_test_message(client, test_user_token, conv['id'], msg)
    
    response = client.get(f"/api/conversations/{conv['id']}/messages", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= len(messages)
    assert all("content" in msg for msg in data)
    assert all("created_at" in msg for msg in data)

def test_message_order(client: TestClient, test_user_token: str):
    """Test that messages are returned in correct chronological order."""
    conv = create_test_conversation(client, test_user_token)
    headers = {"Authorization": f"Bearer {test_user_token}"}
    
    messages = ["First", "Second", "Third"]
    for msg in messages:
        create_test_message(client, test_user_token, conv['id'], msg)
    
    response = client.get(f"/api/conversations/{conv['id']}/messages", headers=headers)
    assert response.status_code == 200
    data = response.json()
    
    # Verify chronological order
    timestamps = [msg["created_at"] for msg in data]
    assert timestamps == sorted(timestamps)

def test_input_sanitization():
    """Test that user input is properly sanitized."""
    test_cases = [
        ("<script>alert('xss')</script>", "alert('xss')"),
        ("Normal text", "Normal text"),
        ("Text with <b>tags</b>", "Text with tags")
    ]
    
    for input_text, expected in test_cases:
        assert sanitize_input(input_text) == expected

def test_response_formatting():
    """Test that AI responses are properly formatted."""
    test_response = "Test response with [link](http://example.com)"
    formatted = format_response(test_response)
    assert "[link]" in formatted
    assert "http://example.com" in formatted

@pytest.mark.slow
def test_ai_response_generation(client: TestClient, test_user_token: str):
    """Test AI response generation for user messages."""
    conv = create_test_conversation(client, test_user_token)
    headers = {"Authorization": f"Bearer {test_user_token}"}
    
    response = client.post(
        f"/api/conversations/{conv['id']}/messages",
        headers=headers,
        json={"content": "What is the capital of France?"}
    )
    
    assert response.status_code == 201
    data = response.json()
    assert "content" in data
    assert len(data["content"]) > 0

def test_message_length_limit(client: TestClient, test_user_token: str):
    """Test that messages cannot exceed maximum length."""
    conv = create_test_conversation(client, test_user_token)
    headers = {"Authorization": f"Bearer {test_user_token}"}
    
    # Create a message that's too long (assuming 1000 char limit)
    long_message = "x" * 1001
    
    response = client.post(
        f"/api/conversations/{conv['id']}/messages",
        headers=headers,
        json={"content": long_message}
    )
    
    assert response.status_code == 422  # Validation error