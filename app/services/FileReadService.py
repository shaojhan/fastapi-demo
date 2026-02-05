from typing import Set

from fastapi import UploadFile

from app.utils.file_reader.file_reader import FileReader


class FileReadService:
    """Application service for reading and validating uploaded files."""

    def __init__(self):
        self._reader = FileReader()

    async def read_csv(self, file: UploadFile, required_headers: Set[str]) -> list[dict]:
        """
        Validate an uploaded file is CSV and parse its contents.

        Args:
            file: The uploaded file from FastAPI
            required_headers: Set of column names that must be present

        Returns:
            List of row dicts

        Raises:
            ValueError: If file type, encoding, headers, or data is invalid
        """
        if not file.filename or not file.filename.endswith('.csv'):
            raise ValueError('File must be a .csv file')

        content = await file.read()
        return self._reader.read_csv(content, required_headers)
