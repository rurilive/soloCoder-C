import os
from dotenv import load_dotenv


load_dotenv()


def get_env_bool(key: str, default: bool = False) -> bool:
    value = os.getenv(key)
    if value is None:
        return default
    return value.lower() in ("true", "1", "yes", "t", "y")


def get_env_float(key: str, default: float = 0.0) -> float:
    value = os.getenv(key)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default


def get_env_int(key: str, default: int = 0) -> int:
    value = os.getenv(key)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


class Config:
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    OPENAI_EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
    EMBEDDING_DIMENSIONS = get_env_int("EMBEDDING_DIMENSIONS", 1536)
    
    VECTOR_SEARCH_ENABLED = bool(OPENAI_API_KEY)
    VECTOR_SEARCH_TOP_K = get_env_int("VECTOR_SEARCH_TOP_K", 20)
    VECTOR_SEARCH_SIMILARITY_THRESHOLD = get_env_float("VECTOR_SEARCH_SIMILARITY_THRESHOLD", 0.0)
    
    PAGE_SIZE = get_env_int("PAGE_SIZE", 12)
    UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploads")
    LOG_DIR = os.getenv("LOG_DIR", "logs")
    
    INITIAL_TOKEN = os.getenv("INITIAL_TOKEN", "aaaa")


config = Config()
