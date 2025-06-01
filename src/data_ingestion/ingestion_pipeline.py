from typing import List
from src.utils import setup_logger
from src.utils import is_valid_metadata
from src.models import FileMetadata
from langchain_core.documents import Document
from src.models import FileMetadata
from src.data_ingestion.md_file_processor import load_markdown_file, chunk_documents

log = setup_logger(__name__)

def ingest_md_files_to_Vector_database(files: List[FileMetadata]):
    """
    Ingests a list of Markdown files from log table by loading, chunking, and uploading them to the vector DB.
    Skips files with invalid metadata or ingestion issues, but continues processing others.
    """
    if not files:
        raise ValueError("No files available for ingestion. Please check logs.")

    log.info(f"Starting ingestion of {len(files)} markdown files.")

    for file in files:
        try:
            process_single_file(file)
        except Exception as e:
            log.error(f"Failed to process file {file.file_path}. Continuing with next. Error: {e}", exc_info=True)

    log.info("Ingestion pipeline completed.")


def process_single_file(file: FileMetadata):
    """
    Full ingestion pipeline for a single file: validation → load → chunk → vector upload.
    """
    if not is_valid_metadata(file):
        log.warning(f"Skipping invalid file metadata: {file.file_path}")
        return Exception("Invalid file metadata, skipping ingestion.")
    
    log.debug(f"Processing file: {file.file_path}")

    documents = load_markdown_file(file)
    if not documents:
        log.warning(f"No documents loaded from file: {file.file_path}")
        return
    # log.info(f" content = {documents[0].page_content}... with metadata: {documents[0].metadata}")
    chunks = chunk_documents(documents)
    if not chunks:
        log.warning(f"No chunks formed from file: {file.file_path}")
        return
    log.info(f"Formed {len(chunks)} chunks from file: {file.file_path}")

    return
    # for chunk in chunks: 
    #     log.info(f"Chunk content: {chunk.page_content}... with metadata: {chunk.metadata}") 
    # upload_chunks_to_vector_db(chunks, file)
    # log.info(f"Completed ingestion for: {file.file_path}")

def upload_chunks_to_vector_db(chunks: List[Document], file: FileMetadata):
    pass