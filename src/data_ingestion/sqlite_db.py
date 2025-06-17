import sqlite3
import time
from typing import Optional, List, Dict

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
        self.create_file_log_table_if_not_exists() # this will create the table if it doesn't exist
        self.create_chunk_log_table_if_not_exists() # this will create the chunk log table if it doesn't exist
        log.info(f"Connected to SQLite database at {self.db_file}")


    def create_chunk_log_table_if_not_exists(self):
        """
        Creates the 'obq_chunk_log' table if it doesn't already exist.
        This table is used to log the chunks generated from files.
        """
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS obq_chunk_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_id INTEGER NOT NULL, -- Foreign key to obq_log.id
                chunk_id TEXT NOT NULL,
                created_at REAL DEFAULT (STRFTIME('%s', 'now')), -- Unix epoch timestamp
                FOREIGN KEY (file_id) REFERENCES obq_log(id)
            )
            """
        )
        self.connection.commit()

# TODO: Might have to make the table name configurable in future if required.
    def create_file_log_table_if_not_exists(self):
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
                    existing = self._select_file_by_path(metadata.file_path) # check if file_log already exists todo: need to add a logic that when it goes to fetch log and sees an entry but it is disabled. then it should skip that file.
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

    def _insert_file_entry(self, metadata: FileMetadata): # as of now, this is a single file insert, but can be extended to batch inserts if needed.dekhte hain 
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
                    WHERE file_path = ?
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
        
    def update_file_status(self, id: int, status: str, error_message: Optional[str] = None):
        """
        Updates the status of a file log entry by its ID.
        :param id: The ID of the file log entry to update.
        :param status: The new status to set (e.g., 'pending', 'processing', 'completed', 'failed').
        :param error_message: Optional error message if the status is 'failed'.
        """
        try:
            last_ingested = time.time()  # Current time as Unix epoch timestamp
            self.cursor.execute(
                """
                UPDATE obq_log
                SET status = ?, error_message = ?, last_ingested = ?
                WHERE id = ?
                """,
                (status, error_message, last_ingested, id)
            )
            self.connection.commit()
            # log.info(f"Updated file log entry {id} to status '{status}'")
        except Exception as e:
            log.error(f"Failed to update file log entry {id}: {e}", exc_info=True)
            self.connection.rollback()

    # i know dono same hai but last_ingestion update ni krna mereko baar baar.
    def update_final_ingestion_status(self, id: int, num_chunks: int, status: str, error_message: Optional[str] = None):
        """
        Updates the final ingestion status of a file log entry by its ID.
        :param id: The ID of the file log entry to update.
        :param num_chunks: The number of chunks generated during ingestion.
        :param last_ingested: The timestamp of the last successful ingestion (Unix epoch).
        """
        try:
        
            self.cursor.execute(
                """
                UPDATE obq_log
                SET status = ?, num_chunks = ?, error_message = ?
                WHERE id = ?
                """,
                (status, num_chunks, error_message, id)
            )
            self.connection.commit()
            # log.info(f"Updated file log entry {id} to completed with {num_chunks} chunks")
        except Exception as e:
            log.error(f"Failed to update final ingestion status for file log entry {id}: {e}", exc_info=True)
            self.connection.rollback()

    def update_chunk_log(self, file_id: int, chunk_id: list[str]):
        """
        Inserts or updates chunk log entries for a file.
        :param file_id: List of file IDs to associate with the chunks.
        :param chunk_id: List of chunk IDs to log.
        """
        try:
            with self.connection:
                for cid in chunk_id:
                    self.cursor.execute(
                        """
                        INSERT INTO obq_chunk_log (file_id, chunk_id)
                        VALUES (?, ?)
                        """,
                        (file_id, cid)
                    )
            log.info(f"Inserted {len(chunk_id)} chunk log entries for file ID(s): {file_id}")
        except Exception as e:
            log.error(f"Failed to insert chunk log entries: {e}", exc_info=True)

    def is_file_id_already_chunked(self, file_id: int) -> bool:
        """
        Checks if a file ID has already been chunked by querying the obq_chunk_log table.
        :param file_id: The ID of the file to check.
        :return: True if the file ID exists in the chunk log, False otherwise.
        """
        try:
            self.cursor.execute("SELECT 1 FROM obq_chunk_log WHERE file_id = ?", (file_id,))
            return self.cursor.fetchone() is not None
        except Exception as e:
            log.error(f"Failed to check if file ID {file_id} is already chunked: {e}", exc_info=True)
            return False
        

    def fetch_and_delete_chunk_logs(self, file_id: int) -> List[str]:
        """
        Fetches and deletes chunk log entries for a specific file ID.
        :param file_id: The ID of the file to fetch and delete chunk logs for.
        :return: A list of chunk IDs that were deleted.
        """
        chunk_ids = []
        try:
            self.cursor.execute("SELECT chunk_id FROM obq_chunk_log WHERE file_id = ?", (file_id,))
            chunk_ids = [row[0] for row in self.cursor.fetchall()]
            if chunk_ids:
                self.cursor.execute("DELETE FROM obq_chunk_log WHERE file_id = ?", (file_id,))
            self.connection.commit()
            log.info(f"Deleted chunk logs for file_id {file_id}: {chunk_ids}")
        except Exception as e:
            log.error(f"Failed to fetch and delete chunk logs for file_id {file_id}: {e}", exc_info=True)
            self.connection.rollback()
            raise e
        return chunk_ids

    def get_files_by_status(self, status1: str, status2: str) -> List[sqlite3.Row]:
        """
        Retrieves all file log entries with a specific status.
        """
        self.cursor.execute("SELECT * FROM obq_log WHERE status in (?,?) and is_enabled = 1", (status1, status2,))
        rows = self.cursor.fetchall()
        # log.info(f"Retrieved {len(rows)} files with status '{status1}' or '{status2}'")
        return rows

    def get_enabled_completed_filenames(self):
        try:

            self.cursor.execute(
                "SELECT file_name FROM obq_log WHERE is_enabled = 1 AND status = 'completed'"
            )
            filenames = [row[0] for row in self.cursor.fetchall()]
            return filenames
        except Exception as e:
            log.error(f"Failed to fetch enabled and completed filenames: {e}", exc_info=True)
            return []

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
