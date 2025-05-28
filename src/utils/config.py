import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Configuration class to manage environment variables."""
    LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama")
    if not LLM_PROVIDER:
        raise ValueError("LLM_PROVIDER must be set in the environment variables.")

    OLLAMA_MODEL_NAME = os.getenv("OLLAMA_MODEL_NAME", None)

    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", None)
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
    
    OLLAMA_EMBEDDING_MODEL = os.getenv("OLLAMA_EMBEDDING_MODEL", None)
    if not OLLAMA_EMBEDDING_MODEL:
        raise ValueError("OLLAMA_EMBEDDING_MODEL must be set in the environment variables.")

    DEBUG = os.getenv("DEBUG", False) == True

config = Config()

