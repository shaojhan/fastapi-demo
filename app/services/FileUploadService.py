import os
import uuid
from pathlib import Path
from fastapi import UploadFile

from app.config import get_settings


# Allowed image extensions
ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB


class FileUploadError(Exception):
    """File upload error."""
    pass


class InvalidFileTypeError(FileUploadError):
    """Invalid file type error."""
    pass


class FileTooLargeError(FileUploadError):
    """File too large error."""
    pass


class FileUploadService:
    """Service for handling file uploads."""

    def __init__(self):
        settings = get_settings()
        self.upload_dir = Path(settings.UPLOAD_DIR if hasattr(settings, 'UPLOAD_DIR') else 'uploads')
        self.avatar_dir = self.upload_dir / 'avatars'
        self._ensure_directories()

    def _ensure_directories(self) -> None:
        """Create upload directories if they don't exist."""
        self.avatar_dir.mkdir(parents=True, exist_ok=True)

    def _validate_image(self, file: UploadFile) -> str:
        """
        Validate the uploaded image file.

        Args:
            file: The uploaded file

        Returns:
            The file extension

        Raises:
            InvalidFileTypeError: If file type is not allowed
        """
        if not file.filename:
            raise InvalidFileTypeError("No filename provided")

        ext = Path(file.filename).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise InvalidFileTypeError(
                f"File type '{ext}' is not allowed. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"
            )

        return ext

    async def upload_avatar(self, user_id: str, file: UploadFile) -> str:
        """
        Upload a user avatar.

        Args:
            user_id: The user's UUID
            file: The uploaded file

        Returns:
            The relative URL path to the uploaded avatar

        Raises:
            InvalidFileTypeError: If file type is not allowed
            FileTooLargeError: If file is too large
        """
        ext = self._validate_image(file)

        # Read file content
        content = await file.read()

        # Check file size
        if len(content) > MAX_FILE_SIZE:
            raise FileTooLargeError(f"File size exceeds {MAX_FILE_SIZE // 1024 // 1024}MB limit")

        # Generate unique filename
        filename = f"{user_id}_{uuid.uuid4().hex[:8]}{ext}"
        file_path = self.avatar_dir / filename

        # Delete old avatar if exists
        self._delete_old_avatars(user_id)

        # Save file
        with open(file_path, 'wb') as f:
            f.write(content)

        # Return relative URL
        return f"/uploads/avatars/{filename}"

    def _delete_old_avatars(self, user_id: str) -> None:
        """Delete existing avatars for a user."""
        for file in self.avatar_dir.glob(f"{user_id}_*"):
            try:
                file.unlink()
            except OSError:
                pass

    def delete_avatar(self, avatar_url: str) -> bool:
        """
        Delete an avatar file.

        Args:
            avatar_url: The avatar URL/path

        Returns:
            True if deleted, False otherwise
        """
        if not avatar_url:
            return False

        # Extract filename from URL
        filename = Path(avatar_url).name
        file_path = self.avatar_dir / filename

        try:
            if file_path.exists():
                file_path.unlink()
                return True
        except OSError:
            pass

        return False
