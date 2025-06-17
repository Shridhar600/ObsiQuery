from src.utils import config, setup_logger
import importlib.util

log = setup_logger(__name__)

class LLMInitializationError(Exception):
    """Custom exception for LLM initialization errors"""
    pass

class LLMFactory:
    @staticmethod
    def get_llm():
        """
        Returns an instance of the LLM class.
        This method can be extended to return different LLM implementations based on configuration.

        Returns:
            An instance of the configured LLM.

        Raises:
            LLMInitializationError: If there's an error during LLM initialization
            ValueError: If required configuration is missing
            ImportError: If required LLM package is not installed
        """

        try:
            if config.LLM_PROVIDER == "ollama":
                if not importlib.util.find_spec("langchain_ollama"):
                    raise ImportError("langchain_ollama package is not installed. Please install it first.")
                
                from langchain_ollama import ChatOllama
                if not config.OLLAMA_MODEL_NAME:
                    raise ValueError("OLLAMA_MODEL_NAME must be set in the environment variables")
                
                try:
                    log.info(f"Initializing OLLAMA model: {config.OLLAMA_MODEL_NAME}")
                    return ChatOllama(model=config.OLLAMA_MODEL_NAME)
                except Exception as e:
                    raise LLMInitializationError(f"Failed to initialize Ollama model: {str(e)}")

            elif config.LLM_PROVIDER == "gemini":
                if not importlib.util.find_spec("langchain_google_genai"):
                    raise ImportError("langchain_google_genai package is not installed. Please install it first.")
                
                from langchain_google_genai import ChatGoogleGenerativeAI
                if not config.GEMINI_API_KEY:
                    raise ValueError("GEMINI_API_KEY must be set in the environment variables")
                if not config.GEMINI_MODEL:
                    raise ValueError("GEMINI_MODEL must be set in the environment variables")
                
                try:
                    log.info(f"Initializing GEMINI model: {config.GEMINI_MODEL}")
                    return ChatGoogleGenerativeAI(
                        model=config.GEMINI_MODEL,
                        api_key=config.GEMINI_API_KEY
                    )
                except Exception as e:
                    raise LLMInitializationError(f"Failed to initialize Gemini model: {str(e)}")
            
            else:
                raise ValueError(f"Unsupported LLM provider: {config.LLM_PROVIDER}")

        except ImportError as e:
            log.error(f"Package import error: {e}")
            raise
        except ValueError as e:
            log.error(f"Configuration error: {e}")
            raise
        except LLMInitializationError as e:
            log.error(f"LLM initialization error: {e}")
            raise
        except Exception as e:
            log.error(f"Unexpected error during LLM initialization: {e}")
            raise LLMInitializationError(f"Unexpected error: {str(e)}")

llm_instance = LLMFactory.get_llm()

def test_llm_instance(llm_instance):
    """
    Test function to verify the LLM instance.
    
    Args:
        llm_instance: The LLM instance to test.
    
    Raises:
        Exception: If there's an error during the test.
    """
    try:
        log.info("Testing LLM instance...")
        response = llm_instance.invoke("What is the capital of France?")
        log.info(f"LLM response: {response}")
    except Exception as e:
        log.error(f"Error testing LLM instance: {str(e)}")
        raise e