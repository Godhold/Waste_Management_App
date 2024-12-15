import os
from fastapi import UploadFile, HTTPException, status
from datetime import datetime
import logging
from typing import List, Optional
import shutil

logger = logging.getLogger(__name__)

# Constants
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
ALLOWED_IMAGE_TYPES = ["image/jpeg", "image/png", "image/jpg"]
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")

# Ensure upload directory exists
os.makedirs(UPLOAD_DIR, exist_ok=True)

def validate_file_size(file_size: int) -> bool:
    """Validate if file size is within limits"""
    return file_size <= MAX_FILE_SIZE

def validate_file_type(content_type: str) -> bool:
    """Validate if file type is allowed"""
    return content_type in ALLOWED_IMAGE_TYPES

async def save_upload_file(
    upload_file: UploadFile,
    folder: str,
    filename: Optional[str] = None
) -> str:
    """
    Save an uploaded file to the specified folder
    Returns the file path relative to the upload directory
    """
    try:
        # Validate file size
        file_size = 0
        chunk_size = 1024 * 1024  # 1MB chunks
        
        # Read file in chunks to validate size
        while chunk := await upload_file.read(chunk_size):
            file_size += len(chunk)
            if not validate_file_size(file_size):
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"File size exceeds maximum limit of {MAX_FILE_SIZE/1024/1024}MB"
                )
            
        # Reset file position
        await upload_file.seek(0)
        
        # Validate file type
        if not validate_file_type(upload_file.content_type):
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail=f"File type {upload_file.content_type} not allowed. Allowed types: {ALLOWED_IMAGE_TYPES}"
            )
        
        # Create folder if it doesn't exist
        folder_path = os.path.join(UPLOAD_DIR, folder)
        os.makedirs(folder_path, exist_ok=True)
        
        # Generate filename if not provided
        if not filename:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            original_filename = upload_file.filename
            extension = os.path.splitext(original_filename)[1]
            filename = f"{timestamp}{extension}"
        
        # Full path for the file
        file_path = os.path.join(folder_path, filename)
        
        # Save file using shutil
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(upload_file.file, buffer)
        
        # Return relative path
        return os.path.relpath(file_path, UPLOAD_DIR)
    
    except Exception as e:
        logger.error(f"Error saving file: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error saving file: {str(e)}"
        )

def delete_file(file_path: str) -> bool:
    """Delete a file from the upload directory"""
    try:
        full_path = os.path.join(UPLOAD_DIR, file_path)
        if os.path.exists(full_path):
            os.remove(full_path)
            return True
        return False
    except Exception as e:
        logger.error(f"Error deleting file: {str(e)}")
        return False
