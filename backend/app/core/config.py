# backend/app/core/config.py
import logging
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # App Settings
    PROJECT_NAME: str = "KnowledgeOS"
    API_V1_STR: str = "/api/v1"
    LOG_LEVEL: str = "INFO"

    # Security
    JWT_SECRET: str
    JWT_REFRESH_SECRET: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 # 1 hour
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Databases
    MONGODB_URL: str
    MONGODB_DB_NAME: str = "knowledge_os"
    REDIS_URL: str
    QDRANT_URL: str

    # Cloud APIs
    LLM_PROVIDER: str = "gemini"
    GEMINI_API_KEY: str
    OPENAI_API_KEY: Optional[str] = None
    HUGGINGFACE_API_KEY: Optional[str] = None
    LLAMAPARSE_API_KEY: Optional[str] = None

    # Vector Configurations
    EMBEDDING_MODEL_NAME: str = "all-MiniLM-L6-v2"
    QDRANT_COLLECTION_NAME: str = "knowledge_chunks"

    # Load from env file
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
