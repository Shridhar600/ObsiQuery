from typing import List
from src.utils import setup_logger,is_valid_metadata,Status
from src.models import FileMetadata
from src.data_ingestion.md_file_processor import load_markdown_file, chunk_documents
from src.vector_store import upload_documents_to_vector_store
from src.data_ingestion import SQLiteDB

log = setup_logger(__name__)

def ingest_md_files_to_vector_database(files: List[FileMetadata]):
    """
    Ingests a list of Markdown files from log table by loading, chunking, and uploading them to the vector DB.
    Skips files with invalid metadata or ingestion issues, but continues processing others.
    """
    if not files:
        log.warning("No files available for ingestion. Please check logs.")
        return 

    log.info(f" -----  Starting ingestion of {len(files)} markdown files. ----- ")
    # need to think about implementing batch processing.

    for file in files:
        log.info(f"Processing file: {file.file_path}")
        # sqlite db to be updated with status started.
        try:
            with SQLiteDB() as db:
                db.update_file_status(file.id, Status.PROCESSING.value)
            process_single_file(file)
        except Exception as e:
            with SQLiteDB() as db:
                db.update_file_status(file.id, Status.FAILED.value, error_message=str(e))
            log.error(f"Failed to process file {file.file_path}. Continuing with next. Error: {e}", exc_info=True)

    log.info("Ingestion pipeline completed.")


def process_single_file(file: FileMetadata):
    """
    Full ingestion pipeline for a single file: validation → load → chunk → vector upload.
    """
    if not is_valid_metadata(file):
        log.warning(f"Skipping invalid file metadata: {file.file_path}")
        return
    
    log.debug(f"Processing file: {file.file_path}")

    try: 
        documents = load_markdown_file(file)    
        if not documents:
            log.warning(f"No documents loaded from file: {file.file_path}")
            return
        # log.info(f"Loaded {len(documents)} documents from file: {file.file_path}")
        
        chunks = chunk_documents(documents, file)
        if not chunks:
            log.warning(f"No chunks formed from file: {file.file_path}")
            return
        log.info(f"Formed {len(chunks)} chunks from file: {file.file_path}")

        upload_documents_to_vector_store(chunks,file.id)

        with SQLiteDB() as db:
            db.update_final_ingestion_status(file.id, len(chunks), Status.COMPLETED.value)
        log.info(f"Successfully processed and uploaded chunks for file: {file.file_path}")

    except Exception as e:
        log.error(f"Error processing file {file.file_path}: {e}", exc_info=True)
        with SQLiteDB() as db:
            db.update_final_ingestion_status(file.id, 0, Status.FAILED.value, error_message=str(e))
        raise 

