"""Helper functions for tests."""
from typing import Dict, Any
import json
import random
import string

def generate_random_string(length: int = 10) -> str:
    """Generate a random string of specified length."""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def generate_user_data() -> Dict[str, str]:
    """Generate random user data for testing."""
    random_suffix = generate_random_string(6)
    return {
        "email": f"test_{random_suffix}@example.com",
        "password": f"password_{random_suffix}",
        "full_name": f"Test User {random_suffix}"
    }

def create_test_conversation(client: Any, token: str) -> Dict[str, Any]:
    """Create a test conversation."""
    headers = {"Authorization": f"Bearer {token}"}
    response = client.post(
        "/api/conversations",
        headers=headers,
        json={"title": "Test Conversation"}
    )
    assert response.status_code == 201
    return response.json()

def create_test_message(
    client: Any,
    token: str,
    conversation_id: str,
    content: str = "Test message"
) -> Dict[str, Any]:
    """Create a test message in a conversation."""
    headers = {"Authorization": f"Bearer {token}"}
    response = client.post(
        f"/api/conversations/{conversation_id}/messages",
        headers=headers,
        json={"content": content}
    )
    assert response.status_code == 201
    return response.json()

def get_error_message(response: Any) -> str:
    """Extract error message from response."""
    try:
        return response.json().get("detail", str(response.content))
    except json.JSONDecodeError:
        return str(response.content)