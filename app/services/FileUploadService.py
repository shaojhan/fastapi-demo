import json
import uuid
from pathlib import Path

import boto3
from botocore.exceptions import ClientError
from fastapi import UploadFile
from loguru import logger

from app.config import get_settings


# Allowed image extensions
ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

CONTENT_TYPE_MAP = {
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.png': 'image/png',
    '.gif': 'image/gif',
    '.webp': 'image/webp',
}


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
    """Service for handling file uploads to S3-compatible storage (MinIO)."""

    def __init__(self):
        settings = get_settings()
        self._bucket = settings.S3_BUCKET_NAME
        self._public_url = settings.S3_PUBLIC_URL.rstrip('/')
        self._s3 = boto3.client(
            's3',
            endpoint_url=settings.S3_ENDPOINT_URL,
            aws_access_key_id=settings.S3_ACCESS_KEY,
            aws_secret_access_key=settings.S3_SECRET_KEY,
        )
        self._ensure_bucket()

    def _ensure_bucket(self) -> None:
        """Create the bucket if it doesn't exist, and set public read policy."""
        try:
            self._s3.head_bucket(Bucket=self._bucket)
        except ClientError:
            self._s3.create_bucket(Bucket=self._bucket)
            policy = {
                "Version": "2012-10-17",
                "Statement": [{
                    "Effect": "Allow",
                    "Principal": "*",
                    "Action": "s3:GetObject",
                    "Resource": f"arn:aws:s3:::{self._bucket}/*",
                }],
            }
            self._s3.put_bucket_policy(
                Bucket=self._bucket,
                Policy=json.dumps(policy),
            )

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
        Upload a user avatar to S3.

        Args:
            user_id: The user's UUID
            file: The uploaded file

        Returns:
            The public URL to the uploaded avatar

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

        # Delete old avatars for this user
        self._delete_old_avatars(user_id)

        # Generate unique filename and upload
        filename = f"{user_id}_{uuid.uuid4().hex[:8]}{ext}"
        key = f"avatars/{filename}"
        content_type = CONTENT_TYPE_MAP.get(ext, 'application/octet-stream')

        self._s3.put_object(
            Bucket=self._bucket,
            Key=key,
            Body=content,
            ContentType=content_type,
        )

        return f"{self._public_url}/{self._bucket}/{key}"

    def _delete_old_avatars(self, user_id: str) -> None:
        """Delete existing avatars for a user from S3."""
        prefix = f"avatars/{user_id}_"
        try:
            response = self._s3.list_objects_v2(
                Bucket=self._bucket,
                Prefix=prefix,
            )
            for obj in response.get('Contents', []):
                self._s3.delete_object(Bucket=self._bucket, Key=obj['Key'])
        except ClientError as e:
            logger.warning(f"Failed to delete old avatars for {user_id}: {e}")

    def delete_avatar(self, avatar_url: str) -> bool:
        """
        Delete an avatar file from S3.

        Args:
            avatar_url: The avatar URL

        Returns:
            True if deleted, False otherwise
        """
        if not avatar_url:
            return False

        try:
            bucket_prefix = f"{self._public_url}/{self._bucket}/"
            if avatar_url.startswith(bucket_prefix):
                key = avatar_url[len(bucket_prefix):]
            else:
                key = f"avatars/{Path(avatar_url).name}"

            self._s3.delete_object(Bucket=self._bucket, Key=key)
            return True
        except ClientError as e:
            logger.warning(f"Failed to delete avatar {avatar_url}: {e}")
            return False
