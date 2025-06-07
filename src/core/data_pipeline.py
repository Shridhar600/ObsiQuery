from src.data_ingestion.ingestion_logging import log_file_metadata,get_files_for_ingestion_from_log_table
from src.data_ingestion.ingestion_pipeline import ingest_md_files_to_Vector_database
from src.utils import config, setup_logger

def run_ingestion_test():
    
    # use this function to log metadata of Markdown files in a directory to the SQLite database.
    log_file_metadata(config.OBSIDIAN_VAULT_PATH) # type: ignore

    #query the database for files that are pending ingestion
    files_to_ingest = get_files_for_ingestion_from_log_table()

    #send these files to the ingestion pipeline to be processed and ingested into the vector database
    ingest_md_files_to_Vector_database(files_to_ingest)