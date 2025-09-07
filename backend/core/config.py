import os
from pathlib import Path
from typing import Optional, List
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Settings(BaseSettings):
    """Application settings"""
    
    # API Keys
    google_ai_api_key: Optional[str] = os.getenv("GOOGLE_AI_API_KEY")
    huggingface_api_key: Optional[str] = os.getenv("HUGGINGFACE_API_KEY")
    together_api_key: Optional[str] = os.getenv("TOGETHER_API_KEY")
    deepseek_api_key: Optional[str] = os.getenv("DEEPSEEK_API_KEY")
    brave_api_key: Optional[str] = os.getenv("BRAVE_API_KEY")
    
    # Storage
    sqlite_db_path: str = os.getenv("SQLITE_DB_PATH", "data/research_cache.db")
    sqlite_memory_cache: bool = os.getenv("SQLITE_MEMORY_CACHE", "true").lower() == "true"
    chroma_persist_dir: str = os.getenv("CHROMA_PERSIST_DIR", "data/chroma_db")
    
    # Performance
    max_concurrent_extractions: int = int(os.getenv("MAX_CONCURRENT_EXTRACTIONS", "5"))
    max_search_results: int = int(os.getenv("MAX_SEARCH_RESULTS", "10"))
    cache_ttl: int = int(os.getenv("CACHE_TTL", "3600"))
    extraction_timeout: int = int(os.getenv("EXTRACTION_TIMEOUT", "30"))
    llm_timeout: int = int(os.getenv("LLM_TIMEOUT", "60"))
    
    # App
    app_host: str = os.getenv("APP_HOST", "0.0.0.0")
    app_port: int = int(os.getenv("APP_PORT", "8000"))
    debug: bool = os.getenv("DEBUG", "false").lower() == "true"
    
    class Config:
        env_file = ".env"
        case_sensitive = False

# Create settings instance
settings = Settings()

# Create data directories
Path(settings.sqlite_db_path).parent.mkdir(parents=True, exist_ok=True)
Path(settings.chroma_persist_dir).mkdir(parents=True, exist_ok=True)