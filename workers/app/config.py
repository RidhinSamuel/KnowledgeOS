# workers/app/config.py
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

class WorkerSettings(BaseSettings):
    LOG_LEVEL: str = "INFO"
    MONGODB_URL: str
    MONGODB_DB_NAME: str = "knowledge_os"
    REDIS_URL: str
    QDRANT_URL: str
    GEMINI_API_KEY: str
    LLAMAPARSE_API_KEY: Optional[str] = None
    QDRANT_COLLECTION_NAME: str = "knowledge_chunks"
    
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = WorkerSettings()
