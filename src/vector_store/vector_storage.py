from src.utils import config, setup_logger
from langchain_chroma import Chroma
from src.embedding import embedding_model_instance


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