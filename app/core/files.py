from minio import Minio
from minio.error import S3Error
from app.core.config import settings
import os
import tempfile
import clamd
import re
import magic
from typing import Optional, List, Tuple
from datetime import timedelta
from pathlib import Path

# Initialize MinIO client
minio_client = Minio(
    settings.MINIO_ENDPOINT,
    access_key=settings.MINIO_ACCESS_KEY.get_secret_value(),
    secret_key=settings.MINIO_SECRET_KEY.get_secret_value(),
    secure=False  # Set to True in production with TLS
)

# Initialize ClamAV client
clamd_client = clamd.ClamdNetworkSocket()

def sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent path traversal and directory attacks."""
    # Get file extension
    ext = os.path.splitext(filename)[1].lower()
    
    # Create safe filename
    safe_name = re.sub(r'[^a-zA-Z0-9._-]', '_', filename)
    safe_name = safe_name.replace('..', '_')
    
    # Ensure extension is allowed
    if ext[1:] not in settings.ALLOWED_FILE_TYPES:
        raise ValueError(f"File type {ext} is not allowed")
    
    return safe_name

def scan_file(file_path: str) -> Tuple[bool, Optional[str]]:
    """Scan file for viruses using ClamAV."""
    try:
        scan_result = clamd_client.scan(file_path)
        file_status = scan_result.get(file_path, ('ERROR', 'Unknown error'))
        
        if file_status[0] == "OK":
            return True, None
        else:
            return False, file_status[1]
    except Exception as e:
        return False, str(e)

def check_file_type(file_path: str, expected_type: str) -> bool:
    """Verify file's actual MIME type matches expected type."""
    mime = magic.Magic(mime=True)
    actual_type = mime.from_file(file_path)
    return actual_type.startswith(expected_type)

async def upload_file(
    file_content: bytes,
    filename: str,
    user_id: int,
    expected_type: Optional[str] = None
) -> Tuple[bool, str]:
    """Upload file with virus scanning and type verification."""
    try:
        # Sanitize filename
        safe_filename = sanitize_filename(filename)
        
        # Create temporary file for scanning
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_file.write(file_content)
            temp_file_path = temp_file.name
        
        try:
            # Scan for viruses
            is_clean, scan_message = scan_file(temp_file_path)
            if not is_clean:
                return False, f"File failed security scan: {scan_message}"
            
            # Verify file type if specified
            if expected_type and not check_file_type(temp_file_path, expected_type):
                return False, "File type verification failed"
            
            # Generate object path
            object_name = f"user_{user_id}/{safe_filename}"
            
            # Ensure bucket exists
            if not minio_client.bucket_exists(settings.MINIO_BUCKET):
                minio_client.make_bucket(settings.MINIO_BUCKET)
            
            # Upload to MinIO
            minio_client.put_object(
                settings.MINIO_BUCKET,
                object_name,
                temp_file_path,
                os.path.getsize(temp_file_path)
            )
            
            return True, object_name
            
        finally:
            # Clean up temporary file
            os.unlink(temp_file_path)
            
    except S3Error as e:
        return False, f"Storage error: {str(e)}"
    except Exception as e:
        return False, f"Upload failed: {str(e)}"

def get_download_url(object_name: str, expires_minutes: int = 60) -> str:
    """Generate temporary download URL for file."""
    try:
        url = minio_client.presigned_get_object(
            settings.MINIO_BUCKET,
            object_name,
            expires=timedelta(minutes=expires_minutes)
        )
        return url
    except S3Error as e:
        raise ValueError(f"Error generating download URL: {str(e)}")

def delete_file(object_name: str) -> bool:
    """Delete file from storage."""
    try:
        minio_client.remove_object(settings.MINIO_BUCKET, object_name)
        return True
    except S3Error:
        return False

def list_user_files(user_id: int) -> List[dict]:
    """List all files uploaded by a user."""
    try:
        prefix = f"user_{user_id}/"
        objects = minio_client.list_objects(settings.MINIO_BUCKET, prefix=prefix)
        
        files = []
        for obj in objects:
            filename = Path(obj.object_name).name
            files.append({
                "name": filename,
                "size": obj.size,
                "last_modified": obj.last_modified,
                "object_name": obj.object_name
            })
        
        return files
    except S3Error:
        return []