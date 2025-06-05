import os
from pathlib import Path
from typing import List
from src.data_ingestion import SQLiteDB
from src.utils import setup_logger,Status
from src.models import FileMetadata
from src.utils import is_valid_metadata
log = setup_logger(__name__)

# Function to log metadata of Markdown files in a directory to the SQLite database.
def log_file_metadata(dir:str) -> None:

    with SQLiteDB() as db:
        try:
            files_metadata = collect_markdown_metadata(dir)
            log.info(f"Collected {len(files_metadata)} files from {dir}")
            db.upsert_files_metadata(files_metadata)
        except Exception as e:
            log.error(f"Error logging file metadata: {e}", exc_info=True)

# Function to retrieve files for ingestion from the database.
def get_files_for_ingestion_from_log_table() -> List[FileMetadata]:
    """Retrieves a list of files that are pending ingestion from the database.
    Returns:
        List[FileMetadata]: A list of FileMetadata objects representing files to be processed.
    """
    files_to_process: List[FileMetadata] = []
    with SQLiteDB() as db:
        try:
            rows = db.get_files_by_status(Status.PENDING.value, Status.FAILED.value)
            files_to_process = [FileMetadata.from_row(row) for row in rows]
            log.info(f"Retrieved {len(files_to_process)} files for ingestion.")
        except Exception as e:
            log.error(f"Error converting row to FileMetadata: {e}", exc_info=True)

    return files_to_process

# Function to walk over a directory and collect metadata of Markdown files.
def collect_markdown_metadata(directory: str) -> List[FileMetadata]:
    """
    Recursively walks a directory and collects metadata from all Markdown (.md) files.

    Args:
        directory (str): The root directory to start scanning.

    Returns:
        List[FileMetadata]: A list of metadata records for each .md file found.
    """
    dir_path = Path(directory).resolve()

    if not dir_path.exists() or not dir_path.is_dir():
        raise ValueError(f"Provided path '{directory}' is not a valid directory.")

    markdown_files_metadata: List[FileMetadata] = []

    for root, _, files in os.walk(dir_path): # ROOT = root directory, _ = subdirectories, files = files in the current directory
        for filename in files:
            if filename.lower().endswith('.md'):
                file_path = Path(root) / filename
                stat = file_path.stat()

                metadata = FileMetadata(
                    id=None,# type: ignore
                    file_name=file_path.name,
                    file_path=str(file_path.resolve()),
                    file_size=stat.st_size,
                    last_modified=stat.st_mtime,  # Last modified time as a Unix timestamp
                    file_hash=None,# type: ignore
                    last_ingested=None,# type: ignore
                    num_chunks=None, # type: ignore
                    status=Status.PENDING.value, 
                    error_message=None,# type: ignore
                    metadata_json=None, # type: ignore
                    created_at=None, # type: ignore
                    is_enabled=None # type: ignore
                )

                if not is_valid_metadata(metadata):
                    log.warning(f"Invalid metadata for file: {file_path}. Skipping.")
                    continue
                log.debug(f"Collected metadata for file: {metadata.file_name}")
                markdown_files_metadata.append(metadata)

    return markdown_files_metadata
