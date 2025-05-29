from ollama import embed
from src import embedding
from src.utils import config
from langchain_ollama import OllamaEmbeddings
from src.utils.logger import setup_logger

log = setup_logger(__name__)

class EmbeddingModel:
    """Class to handle embedding model initialization."""
    
    def __init__(self):
        """Initializes the embedding model based on the configuration."""
        self.embedding_model = OllamaEmbeddings(model=config.OLLAMA_EMBEDDING_MODEL) # type: ignore

    def get_embedding_model(self):
        """Returns the initialized embedding model."""
        log.info(f"Using OLLAMA embedding model: {config.OLLAMA_EMBEDDING_MODEL}")
        return self.embedding_model

# Singleton instance of the embedding model.
embedding_model_instance = EmbeddingModel().get_embedding_model()

def test_embedding_model(embedding_model_instance):
    """Test function to verify the embedding model."""
    try:
        log.info("Testing embedding model...")
        embedded_query = embedding_model_instance.embed_query("What was the name mentioned in the conversation?")
        log.info(f"Embedding result: {embedded_query[:5]}")
    except Exception as e:
        log.error(f"Error testing embedding model: {str(e)}")
        raise e