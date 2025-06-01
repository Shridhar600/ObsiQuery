from dataclasses import dataclass
from typing import Optional
import sqlite3
from src.utils import setup_logger

log = setup_logger(__name__)

@dataclass
class FileMetadata:
    id: int
    file_name: str
    file_path: str
    file_hash: Optional[str]  # Optional, can be used for deduplication
    file_size: int
    last_modified: float  # Last modified time as a Unix timestamp
    last_ingested: Optional[float]  # Last ingested time as a Unix timestamp, can be used to track when the file was last processed
    num_chunks: Optional[int]
    status: str  # Status of the file (e.g., PENDING, IN_PROGRESS, COMPLETED, FAILED)
    error_message: Optional[str]  # Optional error message if processing failed
    metadata_json: Optional[str]  # JSON string to store additional metadata if needed
    created_at: float
    is_enabled: bool

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "FileMetadata":
        try:
            metadata = cls(
                id=row["id"],
                file_name=row["file_name"],
                file_path=row["file_path"],
                file_hash=row["file_hash"],
                file_size=row["file_size"],
                last_modified=row["last_modified"],
                last_ingested=row["last_ingested"],
                num_chunks=row["num_chunks"],
                status=row["status"],
                error_message=row["error_message"],
                metadata_json=row["metadata_json"],
                created_at=row["created_at"],
                is_enabled=row["is_enabled"]
            )
            log.debug(f"Successfully created FileMetadata from row: {row}")
            return metadata
        except Exception as e:
            log.error(f"Error creating FileMetadata from row: {row}. Error: {e}")
            raise
