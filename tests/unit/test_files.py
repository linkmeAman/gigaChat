"""Unit tests for file operations functionality."""
import pytest
import io
import os
from fastapi.testclient import TestClient
from tests.helpers import generate_random_string

def create_test_file(size_kb: int = 100) -> tuple[str, bytes]:
    """Create a test file with specified size."""
    content = os.urandom(size_kb * 1024)
    filename = f"test_file_{generate_random_string()}.bin"
    return filename, content

def test_file_upload(client: TestClient, test_user_token: str):
    """Test basic file upload functionality."""
    headers = {"Authorization": f"Bearer {test_user_token}"}
    filename, content = create_test_file()
    
    files = {
        "file": (filename, io.BytesIO(content), "application/octet-stream")
    }
    
    response = client.post(
        "/api/files/upload",
        headers=headers,
        files=files
    )
    
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert "filename" in data
    assert data["filename"] == filename
    assert "size" in data
    assert "mime_type" in data
    assert "created_at" in data

def test_file_download(client: TestClient, test_user_token: str):
    """Test file download functionality."""
    headers = {"Authorization": f"Bearer {test_user_token}"}
    filename, content = create_test_file()
    
    # Upload file first
    files = {
        "file": (filename, io.BytesIO(content), "application/octet-stream")
    }
    upload_response = client.post(
        "/api/files/upload",
        headers=headers,
        files=files
    )
    file_id = upload_response.json()["id"]
    
    # Download file
    download_response = client.get(
        f"/api/files/{file_id}/download",
        headers=headers
    )
    
    assert download_response.status_code == 200
    assert download_response.content == content
    assert "content-disposition" in download_response.headers

def test_file_metadata(client: TestClient, test_user_token: str):
    """Test file metadata operations."""
    headers = {"Authorization": f"Bearer {test_user_token}"}
    filename, content = create_test_file()
    
    # Upload file
    files = {
        "file": (filename, io.BytesIO(content), "application/octet-stream")
    }
    metadata = {
        "description": "Test file description",
        "tags": ["test", "example"]
    }
    
    response = client.post(
        "/api/files/upload",
        headers=headers,
        files=files,
        data=metadata
    )
    
    file_id = response.json()["id"]
    
    # Get metadata
    response = client.get(f"/api/files/{file_id}", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["description"] == metadata["description"]
    assert data["tags"] == metadata["tags"]
    
    # Update metadata
    updated_metadata = {
        "description": "Updated description",
        "tags": ["updated", "test"]
    }
    response = client.put(
        f"/api/files/{file_id}",
        headers=headers,
        json=updated_metadata
    )
    assert response.status_code == 200
    assert response.json()["description"] == updated_metadata["description"]
    assert response.json()["tags"] == updated_metadata["tags"]

def test_file_sharing(client: TestClient, test_user_token: str):
    """Test file sharing functionality."""
    headers = {"Authorization": f"Bearer {test_user_token}"}
    filename, content = create_test_file()
    
    # Upload file
    files = {
        "file": (filename, io.BytesIO(content), "application/octet-stream")
    }
    response = client.post("/api/files/upload", headers=headers, files=files)
    file_id = response.json()["id"]
    
    # Create share link
    response = client.post(
        f"/api/files/{file_id}/share",
        headers=headers,
        json={"expires_in": 3600}  # 1 hour
    )
    assert response.status_code == 201
    share_data = response.json()
    assert "share_url" in share_data
    assert "expires_at" in share_data
    
    # Access shared file
    share_url = share_data["share_url"]
    response = client.get(share_url)
    assert response.status_code == 200
    assert response.content == content

def test_file_deletion(client: TestClient, test_user_token: str):
    """Test file deletion."""
    headers = {"Authorization": f"Bearer {test_user_token}"}
    filename, content = create_test_file()
    
    # Upload file
    files = {
        "file": (filename, io.BytesIO(content), "application/octet-stream")
    }
    response = client.post("/api/files/upload", headers=headers, files=files)
    file_id = response.json()["id"]
    
    # Delete file
    response = client.delete(f"/api/files/{file_id}", headers=headers)
    assert response.status_code == 204
    
    # Verify file is deleted
    response = client.get(f"/api/files/{file_id}", headers=headers)
    assert response.status_code == 404

def test_storage_quota(client: TestClient, test_user_token: str):
    """Test storage quota management."""
    headers = {"Authorization": f"Bearer {test_user_token}"}
    
    # Get current quota usage
    response = client.get("/api/files/quota", headers=headers)
    assert response.status_code == 200
    initial_quota = response.json()
    assert "used" in initial_quota
    assert "total" in initial_quota
    
    # Upload file and check updated quota
    filename, content = create_test_file(size_kb=1024)  # 1MB file
    files = {
        "file": (filename, io.BytesIO(content), "application/octet-stream")
    }
    response = client.post("/api/files/upload", headers=headers, files=files)
    assert response.status_code == 201
    
    # Check updated quota
    response = client.get("/api/files/quota", headers=headers)
    updated_quota = response.json()
    assert updated_quota["used"] > initial_quota["used"]

def test_file_validation(client: TestClient, test_user_token: str):
    """Test file validation rules."""
    headers = {"Authorization": f"Bearer {test_user_token}"}
    
    # Test file size limit
    large_filename, large_content = create_test_file(size_kb=5120)  # 5MB
    files = {
        "file": (large_filename, io.BytesIO(large_content), "application/octet-stream")
    }
    response = client.post("/api/files/upload", headers=headers, files=files)
    assert response.status_code == 413  # Payload too large
    
    # Test invalid file type
    files = {
        "file": ("test.exe", io.BytesIO(b"test"), "application/x-msdownload")
    }
    response = client.post("/api/files/upload", headers=headers, files=files)
    assert response.status_code == 415  # Unsupported media type

def test_bulk_operations(client: TestClient, test_user_token: str):
    """Test bulk file operations."""
    headers = {"Authorization": f"Bearer {test_user_token}"}
    file_ids = []
    
    # Upload multiple files
    for _ in range(3):
        filename, content = create_test_file()
        files = {
            "file": (filename, io.BytesIO(content), "application/octet-stream")
        }
        response = client.post("/api/files/upload", headers=headers, files=files)
        file_ids.append(response.json()["id"])
    
    # Bulk delete
    response = client.post(
        "/api/files/bulk-delete",
        headers=headers,
        json={"file_ids": file_ids}
    )
    assert response.status_code == 204
    
    # Verify all files are deleted
    for file_id in file_ids:
        response = client.get(f"/api/files/{file_id}", headers=headers)
        assert response.status_code == 404

def test_file_search(client: TestClient, test_user_token: str):
    """Test file search functionality."""
    headers = {"Authorization": f"Bearer {test_user_token}"}
    
    # Upload files with specific names
    filenames = ["document1.txt", "image1.jpg", "document2.txt"]
    for filename in filenames:
        files = {
            "file": (filename, io.BytesIO(b"test"), "application/octet-stream")
        }
        client.post("/api/files/upload", headers=headers, files=files)
    
    # Search by name pattern
    response = client.get("/api/files/search?q=document", headers=headers)
    assert response.status_code == 200
    results = response.json()
    assert len(results) == 2
    assert all("document" in file["filename"] for file in results)
    
    # Search by file type
    response = client.get("/api/files/search?type=txt", headers=headers)
    assert response.status_code == 200
    results = response.json()
    assert len(results) == 2
    assert all(file["filename"].endswith(".txt") for file in results)