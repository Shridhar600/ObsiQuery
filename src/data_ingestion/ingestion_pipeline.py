import os
from pathlib import Path
from typing import List
from datetime import datetime

from numpy import long
from src.utils import setup_logger
from src.data_ingestion import SQLiteDB
from src.utils.common_utils import is_valid_metadata

log = setup_logger(__name__)

from src.models import FileMetadata

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
                    name=file_path.name,
                    absolute_path=str(file_path.resolve()),
                    size=stat.st_size,
                    mtime=stat.st_mtime,  # Last modified time as a Unix timestamp
                )
                
                if not is_valid_metadata(metadata):
                    log.warning(f"Invalid metadata for file: {file_path}. Skipping.")
                    continue
                log.debug(f"Collected metadata for file: {metadata.name}")
                markdown_files_metadata.append(metadata)

    return markdown_files_metadata


def log_file_metadata(dir:str) -> None:

    with SQLiteDB() as db:
        db.upsert_files_metadata(collect_markdown_metadata(dir))