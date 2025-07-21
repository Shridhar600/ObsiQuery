from src.utils import config, setup_logger
from langchain_chroma import Chroma
from src.embedding import embedding_model_instance
from src.data_ingestion import SQLiteDB
from langchain_core.documents import Document
from src.models import VectorSearchOutputSchema

log = setup_logger(__name__)

class VectorStorage:
    """
    Base class for vector storage.
    """

    def __init__(self, embedding_model_instance):
        """
        Initializes the vector storage with the given embedding model instance.
        """
        if embedding_model_instance is None:
            raise ValueError("Embedding model instance must be provided.")
        self.vector_store = Chroma(
            collection_name=config.VECTOR_STORE_COLLECTION, # type: ignore
            embedding_function=embedding_model_instance,
            persist_directory="./data", # type: ignore
        )

    def get_vector_store(self):
        """
        Returns the vector store instance.
        """
        log.info(f"Using vector store: {config.VECTOR_STORE_COLLECTION}")
        return self.vector_store


vector_store_instance = VectorStorage(embedding_model_instance=embedding_model_instance).get_vector_store()


def upload_documents_to_vector_store(documents: list[Document], file_id: int):
    """
    Uploads documents to the vector store.
    """
    if not documents:
        raise ValueError("No documents provided for upload.")
    try:
        check_if_chunks_already_uploaded(file_id)
    except Exception as e:
        log.error(f"Skipping upload due to issue in clearing out previous chunks: {str(e)}")
        raise
    try:
        import uuid
        ids = [str(uuid.uuid4()) for _ in range(len(documents))] 
        # log.info(f"Uploading {len(documents)} chunks to vector store.")
        vector_store_instance.add_documents(documents=documents, ids=ids)
        with SQLiteDB() as db:
            db.update_chunk_log(
                file_id=file_id,
                chunk_id=ids,
            )
        log.info("Documents uploaded to vector store successfully.")
    except Exception as e:
        log.error(f"Failed to upload documents: {str(e)}")
        raise e


def check_if_chunks_already_uploaded(file_id: int):
    """
    Checks if chunks for the given file_id have already been uploaded to the vector store.
    Raises an exception if they have.
    """
    try:
        with SQLiteDB() as db:
            existing_chunks = db.is_file_id_already_chunked(file_id)
            if existing_chunks:
                log.info(f"Chunks for file_id {file_id} already exist in the vector store.")
                delete_existing_chunks(file_id)
    except Exception as e:
        log.error(f"Failed to check existing chunks: {str(e)}")
        raise e

def delete_existing_chunks(file_id: int):
    """
    Deletes existing chunks for the given file_id from the vector store and also from the SQLite database.
    """
    try:
        with SQLiteDB() as db:
            chunk_ids = db.fetch_and_delete_chunk_logs(file_id)
        vector_store_instance.delete(ids=chunk_ids)
        log.info(f"Deleted {len(chunk_ids)} chunks for file_id {file_id} from vector store.")
    except Exception as e:
        log.error(f"Failed to delete existing chunks: {str(e)}")
        raise e
    

def similarity_search( query_filter: VectorSearchOutputSchema) -> list[Document]:
    if not query_filter:
        raise ValueError("No Query filter received for similarity Search")
    
    filenames_to_filter = query_filter.filenames_filter

    filter = None
    if filenames_to_filter and len(filenames_to_filter) > 0:
        filter = {"file_name": {"$in": filenames_to_filter}}

    try: 
        response =  vector_store_instance.similarity_search(query=query_filter.refined_query_for_vector_search,k = 3, filter=filter)
        log.info(f" -- Retrieved {len(response)} documents from User's Notes.")
        return response
    except Exception as e:
        log.error(f"Error during similarity search: {str(e)}")
        return []


#test Run the test function to verify the vector store
def test_vector_store(vector_store_instance):
    """
    Test function to verify the vector store.
    """
    from langchain_core.documents import Document
    from uuid import uuid4
    try:
        log.info("Testing vector store...")
        document_1 = Document(
        page_content="I had chocolate chip pancakes and scrambled eggs for breakfast this morning.",
        metadata={"source": "tweet"},
        id=1,)

        documents = [document_1]
        uuids = [str(uuid4()) for _ in range(len(documents))]
        vector_store_instance.add_documents(documents=documents, ids=uuids)

    except Exception as e:
        log.error(f"Error testing vector store: {str(e)}")
        raise e
