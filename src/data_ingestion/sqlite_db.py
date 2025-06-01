import re
import sqlite3
import time
import json
from typing import Optional, List, Dict, Any

from numpy import insert
from src.utils import setup_logger,config,Status
from src.models.file_meta_data import FileMetadata

log = setup_logger(__name__)

class SQLiteDB:
    def __init__(self, db_file: str = config.SQLITE_DB_FILE): # type: ignore
        """
        Initializes the SQLiteDB connection.
        :param db_file: Path to the SQLite database file.
        """
        self.db_file = db_file
        self.connection = sqlite3.connect(self.db_file, detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES) # type: ignore
        # Set row_factory to sqlite3.Row to access columns by name
        self.connection.row_factory = sqlite3.Row
        self.cursor = self.connection.cursor()
        self.create_table_if_not_exists() # this will create the table if it doesn't exist
        log.info(f"Connected to SQLite database at {self.db_file}")

    def create_table_if_not_exists(self):
        """
        Creates the 'obq_log' table if it doesn't already exist.
        Uses Unix epoch timestamps for last_modified and last_ingested_timestamp. As it is easy to work with in Python and put in db or for comparison.
        """
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS obq_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_name TEXT NOT NULL,
                file_path TEXT NOT NULL UNIQUE,
                file_hash TEXT,
                file_size INTEGER,
                last_modified REAL NOT NULL,        -- OS file last modification timestamp (Unix epoch)
                last_ingested REAL,       -- Timestamp of last successful ingestion (Unix epoch), NULLABLE
                num_chunks INTEGER,                 -- Number of chunks generated, NULLABLE
                status TEXT NOT NULL CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
                error_message TEXT,                 -- Store error if status is 'failed'
                metadata_json TEXT,                 -- Store extracted metadata as JSON string, NULLABLE
                created_at REAL DEFAULT (STRFTIME('%s', 'now')), -- Unix epoch timestamp
                is_enabled BOOLEAN DEFAULT 1         -- Indicates if the file metadata is enabled
                )
            """
        )
        self.connection.commit()

    def upsert_files_metadata(self, metadata_list: List[FileMetadata]) -> None:
        """
        Upserts file metadata into the database.
        :param metadata_list: List of FileMetadata objects to upsert.
        """
        if not metadata_list:
            log.warning("No metadata to upsert. The list is empty.")
            return

        log.info(f"{len(metadata_list)} file entries received to be logged into the log table.")
        inserted_count = 0
        updated_count = 0
        try:
            with self.connection:
                for metadata in metadata_list:
                    existing = self._select_file_by_path(metadata.file_path) # check if file_log already exists
                    if not existing:# File does not exist, insert new entry
                        is_inserted = self._insert_file_entry(metadata)
                        if is_inserted:
                            inserted_count += 1
                    else: # File already exists, update if necessary based on last_modified
                        # log.info(f"File entry exists, checking for updates: {metadata.name} at {metadata.absolute_path}")
                        is_updated = self._update_file_if_modified(metadata, existing)
                        if is_updated:
                            updated_count += 1
        except Exception as e:
            log.error(f"Error during upsert in log table: {e}", exc_info=True)

        finally:
            log.info(f"Upsert completed: {inserted_count} inserted, {updated_count} updated in log table.")

    def _select_file_by_path(self, file_path: str) -> Optional[sqlite3.Row]: # private method might change in future if required. 
        try:
            self.cursor.execute("SELECT * FROM obq_log WHERE file_path = ?", (file_path,))
            return self.cursor.fetchone()
        except Exception as e:
            log.error(f"Failed to query file path {file_path}: {e}", exc_info=True)
            return None

    def _insert_file_entry(self, metadata: FileMetadata): # as of now, this is a single file insert, but can be extended to batch inserts if needed.
        try:
            self.cursor.execute(
                """
                INSERT INTO obq_log (
                    file_name, file_path, file_size, last_modified, status
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    metadata.file_name,
                    metadata.file_path,
                    metadata.file_size,
                    metadata.last_modified,  # Convert datetime to float (Unix epoch)
                    Status.PENDING.value,
                ),
            )
            log.debug(f"Inserted new file record: {metadata.file_name}")
            return True
        except Exception as e:
            log.error(f"Failed to insert metadata for {metadata.file_name}: {e}", exc_info=True)
            return False

    def _update_file_if_modified(self, metadata: FileMetadata, existing: sqlite3.Row):
        try:
            existing_mtime = float(existing["last_modified"])
            new_mtime = metadata.last_modified
            # log.info(f"Checking modification for {metadata.name}: existing={existing_mtime}, new={new_mtime}")
            if existing_mtime != new_mtime:
                self.cursor.execute(
                    """
                    UPDATE obq_log
                    SET file_size = ?, last_modified = ?, status = ?, file_hash = NULL, num_chunks = NULL
                    WHERE file_path = ? and is_enabled = 1
                    """,
                    (
                        metadata.file_size,
                        new_mtime,
                        Status.PENDING.value,
                        metadata.file_path,
                    ),
                )
                if self.cursor.rowcount == 0:
                    log.info(f"Log not updated for {metadata.file_name}. It may have been deleted or is invalid.")
                    return False
                else:
                    log.debug(f"Updated modified file: {metadata.file_name}")
                    return True
            else:
                log.debug(f"No update needed for: {metadata.file_name}")
                return False
        
        except Exception as e:
            log.error(f"Failed to update metadata for {metadata.file_name}: {e}", exc_info=True)
            return False

    def get_files_by_status(self, status1: str, status2: str) -> List[sqlite3.Row]:
        """
        Retrieves all file log entries with a specific status.
        """
        self.cursor.execute("SELECT * FROM obq_log WHERE status in (?,?) and is_enabled = 1", (status1, status2,))
        rows = self.cursor.fetchall()
        # log.info(f"Retrieved {len(rows)} files with status '{status1}' or '{status2}'")
        return rows

    def get_all_tracked_files(self) -> Dict[str, sqlite3.Row]:
        """
        Retrieves all file paths and their log entries currently tracked in the database.
        Returns a dictionary mapping file_path to its sqlite3.Row object.
        """
        self.cursor.execute("SELECT * FROM obq_log")
        return {row['file_path']: row for row in self.cursor.fetchall()}

    def file_exists(self, file_path: str) -> bool:
        """
        Checks if a file_path is already in the log.
        """
        self.cursor.execute("SELECT 1 FROM obq_log WHERE file_path = ?", (file_path,))
        return self.cursor.fetchone() is not None

    def delete_file_log_entry(self, file_path: str) -> bool:
        """
        Deletes a file log entry by its path.
        Useful if a file is deleted from the filesystem.
        """
        if not self.file_exists(file_path):
            print(f"Cannot delete: File {file_path} not found in log.")
            return False
        try:
            self.cursor.execute("DELETE FROM obq_log WHERE file_path = ?", (file_path,))
            self.connection.commit()
            return True
        except Exception as e:
            print(f"Error deleting file {file_path}: {e}")
            self.connection.rollback()
            return False

    def close_connection(self):
        """
        Closes the database connection.
        """
        if self.connection:
            self.connection.close()
            print("Database connection closed.")

    def __enter__(self): # Context manager support with statement
        """        Allows using SQLiteDB in a with statement.
        """
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Ensures the database connection is closed when exiting the context manager.
        """
        self.close_connection()
