import sqlite3
import time
import json
from typing import Optional, List, Dict, Any, Tuple

class SQLiteDB:
    def __init__(self, db_file: str):
        """
        Initializes the SQLiteDB connection.
        :param db_file: Path to the SQLite database file.
        """
        self.db_file ='./data/Obsiquery.db'
        self.connection = sqlite3.connect(db_file, detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
        # Set row_factory to sqlite3.Row to access columns by name
        self.connection.row_factory = sqlite3.Row
        self.cursor = self.connection.cursor()
        self.create_table_if_not_exists() 

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
                last_ingested_timestamp REAL,       -- Timestamp of last successful ingestion (Unix epoch), NULLABLE
                num_chunks INTEGER,                 -- Number of chunks generated, NULLABLE
                status TEXT NOT NULL CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
                error_message TEXT,                 -- Store error if status is 'failed'
                metadata_json TEXT,                 -- Store extracted metadata as JSON string, NULLABLE
                created_at REAL DEFAULT (STRFTIME('%s', 'now')) -- Unix epoch timestamp
            )
            """
        )
        self.connection.commit()

    def add_file_log_entry(self,
                           file_name: str,
                           file_path: str,
                           file_size: int,
                           last_modified: float,
                           status: str = 'pending',
                           file_hash: Optional[str] = None, # Typically added after processing
                           metadata_json: Optional[Dict[Any, Any]] = None
                           ) -> Optional[int]:
        """
        Adds a new file entry to the log.
        Returns the id of the newly inserted row, or None if insertion failed (e.g. UNIQUE constraint).
        """
        try:
            metadata_string = json.dumps(metadata_json) if metadata_json else None
            self.cursor.execute(
                """
                INSERT INTO obq_log (file_name, file_path, file_hash, file_size, last_modified, status, metadata_json, last_ingested_timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, NULL) 
                """,
                (file_name, file_path, file_hash, file_size, last_modified, status, metadata_string)
            )
            self.connection.commit()
            return self.cursor.lastrowid
        except sqlite3.IntegrityError as e:
            # This typically means the file_path UNIQUE constraint was violated
            print(f"Error adding file {file_path}: {e}. It might already exist.")
            return None
        except Exception as e:
            print(f"An unexpected error occurred while adding file {file_path}: {e}")
            return None

    def get_file_log_entry(self, file_path: str) -> Optional[sqlite3.Row]:
        """
        Retrieves a file log entry by its path.
        Returns a sqlite3.Row object or None if not found.
        """
        self.cursor.execute("SELECT * FROM obq_log WHERE file_path = ?", (file_path,))
        return self.cursor.fetchone()

    def update_file_log_entry(self,
                              file_path: str,
                              status: Optional[str] = None,
                              file_hash: Optional[str] = None,
                              file_size: Optional[int] = None,
                              last_modified: Optional[float] = None,
                              num_chunks: Optional[int] = None,
                              error_message: Optional[str] = None,
                              clear_error: bool = False, # Flag to explicitly clear error_message
                              metadata_json: Optional[Dict[Any, Any]] = None
                             ) -> bool:
        """
        Updates an existing file log entry.
        Only updates fields that are not None.
        Sets last_ingested_timestamp to current time if status is 'completed'.
        """
        entry = self.get_file_log_entry(file_path) # Check if the file exists in the log
        # If the entry does not exist, we cannot update it
        if not entry:
            print(f"Error updating: File {file_path} not found in log.")
            return False

        updates = []
        params = []

        current_time = time.time()

        if status is not None:
            updates.append("status = ?")
            params.append(status)
            if status == 'completed':
                updates.append("last_ingested_timestamp = ?")
                params.append(current_time)
                # If completing, clear any previous error message unless a new one is provided
                if error_message is None and not clear_error:
                    updates.append("error_message = NULL")
            elif status == 'failed' and error_message is None:
                 print(f"Warning: Setting status to 'failed' for {file_path} without providing an error_message.")


        if file_hash is not None:
            updates.append("file_hash = ?")
            params.append(file_hash)
        if file_size is not None:
            updates.append("file_size = ?")
            params.append(file_size)
        if last_modified is not None: # OS last modified
            updates.append("last_modified = ?")
            params.append(last_modified)
        if num_chunks is not None:
            updates.append("num_chunks = ?")
            params.append(num_chunks)
        if error_message is not None:
            updates.append("error_message = ?")
            params.append(error_message)
        elif clear_error: # Explicitly clear error message
            updates.append("error_message = NULL")
        if metadata_json is not None:
            updates.append("metadata_json = ?")
            params.append(json.dumps(metadata_json))


        if not updates:
            print(f"No updates specified for file {file_path}.")
            return True # No changes, but not an error

        query = f"UPDATE obq_log SET {', '.join(updates)} WHERE file_path = ?"
        params.append(file_path)

        try:
            self.cursor.execute(query, tuple(params))
            self.connection.commit()
            return True
        except Exception as e:
            print(f"Error updating file {file_path}: {e}")
            self.connection.rollback() # Rollback on error
            return False

    def get_files_by_status(self, status: str) -> List[sqlite3.Row]:
        """
        Retrieves all file log entries with a specific status.
        """
        self.cursor.execute("SELECT * FROM obq_log WHERE status = ?", (status,))
        return self.cursor.fetchall()

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

# Example Usage (for testing this file directly):
if __name__ == '__main__':
    # Create a dummy data directory if it doesn't exist
    import os
    data_dir = './data'
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
    
    db_path = os.path.join(data_dir, 'test_obsiquery.db')
    # Clean up old DB for fresh test run
    if os.path.exists(db_path):
        os.remove(db_path)

    print(f"Using database: {db_path}")

    with SQLiteDB(db_path) as db: # Using context manager
        print("Database initialized and table created (if not exists).")

        # Test add_file_log_entry
        print("\n--- Testing add_file_log_entry ---")
        ts = time.time()
        added_id1 = db.add_file_log_entry(
            file_name="note1.md",
            file_path="/vault/note1.md",
            file_size=1024,
            last_modified=ts - 3600, # 1 hour ago
            status='pending',
            metadata_json={"tags": ["projectA", "research"]}
        )
        print(f"Added note1.md, ID: {added_id1}")

        added_id2 = db.add_file_log_entry(
            file_name="note2.md",
            file_path="/vault/note2.md",
            file_size=2048,
            last_modified=ts - 7200, # 2 hours ago
            status='pending'
        )
        print(f"Added note2.md, ID: {added_id2}")

        # Test duplicate add (should fail gracefully)
        db.add_file_log_entry(
            file_name="note1.md", # Same path
            file_path="/vault/note1.md",
            file_size=1025,
            last_modified=ts - 3500
        )

        # Test get_file_log_entry
        print("\n--- Testing get_file_log_entry ---")
        entry1 = db.get_file_log_entry("/vault/note1.md")
        if entry1:
            print(f"Retrieved note1.md: Name='{entry1['file_name']}', Status='{entry1['status']}', Metadata='{entry1['metadata_json']}'")
            if entry1['metadata_json']:
                print(f"  Parsed metadata: {json.loads(entry1['metadata_json'])}")


        # Test file_exists
        print("\n--- Testing file_exists ---")
        print(f"Exists /vault/note1.md: {db.file_exists('/vault/note1.md')}")
        print(f"Exists /vault/nonexistent.md: {db.file_exists('/vault/nonexistent.md')}")

        # Test update_file_log_entry
        print("\n--- Testing update_file_log_entry ---")
        db.update_file_log_entry(
            file_path="/vault/note1.md",
            status='processing'
        )
        entry1_updated = db.get_file_log_entry("/vault/note1.md")
        print(f"note1.md after 'processing' update: Status='{entry1_updated['status']}'") # type: ignore

        db.update_file_log_entry(
            file_path="/vault/note1.md",
            status='completed',
            file_hash="abc123hash",
            num_chunks=5,
            clear_error=True # Ensure error_message is NULL
        )
        entry1_completed = db.get_file_log_entry("/vault/note1.md")
        print(f"note1.md after 'completed' update: Status='{entry1_completed['status']}', Hash='{entry1_completed['file_hash']}', Chunks='{entry1_completed['num_chunks']}', IngestedTS='{entry1_completed['last_ingested_timestamp']}'")

        db.update_file_log_entry(
            file_path="/vault/note2.md",
            status='failed',
            error_message="Parsing error: invalid frontmatter"
        )
        entry2_failed = db.get_file_log_entry("/vault/note2.md")
        print(f"note2.md after 'failed' update: Status='{entry2_failed['status']}', Error='{entry2_failed['error_message']}'")
        
        # Test updating with clear_error
        db.update_file_log_entry(
            file_path="/vault/note2.md",
            status='pending', # Re-queueing it perhaps
            clear_error=True # Clear the previous error
        )
        entry2_requeued = db.get_file_log_entry("/vault/note2.md")
        print(f"note2.md after re-queueing and clearing error: Status='{entry2_requeued['status']}', Error='{entry2_requeued['error_message']}'")


        # Test get_files_by_status
        print("\n--- Testing get_files_by_status ---")
        pending_files = db.get_files_by_status('pending')
        print(f"Pending files ({len(pending_files)}):")
        for row in pending_files:
            print(f"  - {row['file_name']} (Path: {row['file_path']})")

        completed_files = db.get_files_by_status('completed')
        print(f"Completed files ({len(completed_files)}):")
        for row in completed_files:
            print(f"  - {row['file_name']} (Last Ingested: {time.ctime(row['last_ingested_timestamp']) if row['last_ingested_timestamp'] else 'N/A'})")

        # Test get_all_tracked_files
        print("\n--- Testing get_all_tracked_files ---")
        all_files = db.get_all_tracked_files()
        print(f"Total tracked files: {len(all_files)}")
        for path, data in all_files.items():
            print(f"  - Path: {path}, Status: {data['status']}")

        # Test delete_file_log_entry
        print("\n--- Testing delete_file_log_entry ---")
        db.delete_file_log_entry("/vault/note1.md")
        print(f"Exists /vault/note1.md after delete: {db.file_exists('/vault/note1.md')}")
        
        # Test delete non-existent
        db.delete_file_log_entry("/vault/nonexistent.md")

    print("\nExample usage finished. Database connection closed by context manager.")