import csv
import io
from typing import Set


class FileReader:
    """Utility for reading and parsing uploaded files."""

    @staticmethod
    def read_csv(content: bytes, required_headers: Set[str]) -> list[dict]:
        """
        Parse raw bytes as a CSV file and validate headers.

        Args:
            content: Raw file bytes (UTF-8 or UTF-8-BOM encoded)
            required_headers: Set of column names that must be present

        Returns:
            List of row dicts parsed by csv.DictReader

        Raises:
            ValueError: If encoding, headers, or data is invalid
        """
        try:
            text = content.decode('utf-8-sig')
        except UnicodeDecodeError:
            raise ValueError('File must be UTF-8 encoded')

        reader = csv.DictReader(io.StringIO(text))
        if not reader.fieldnames:
            raise ValueError('CSV file is empty or has no headers')

        actual_headers = {h.strip() for h in reader.fieldnames}
        missing = required_headers - actual_headers
        if missing:
            raise ValueError(f'Missing required CSV headers: {", ".join(sorted(missing))}')

        rows = list(reader)
        if not rows:
            raise ValueError('CSV file contains no data rows')

        return rows
