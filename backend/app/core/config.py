# backend/app/core/config.py
import os
import logging
from pathlib import Path
from typing import Optional
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Locate .env file relative to config.py location
BASE_DIR = Path(__file__).resolve().parent.parent.parent # Root of project or backend

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
    HUGGINGFACE_API_KEY: Optional[str] = None
    LLAMAPARSE_API_KEY: Optional[str] = None

    # Vector Configurations
    EMBEDDING_MODEL_NAME: str = "all-MiniLM-L6-v2"
    QDRANT_COLLECTION_NAME: str = "knowledge_chunks"

    @model_validator(mode="after")
    def resolve_docker_vs_localhost(self):
        """
        Seamless Hybrid Execution:
        If running directly on local host (outside Docker), automatically map container service 
        names ('mongodb', 'valkey', 'qdrant') to 'localhost' so the app works seamlessly in both setups.
        """
        is_in_docker = os.path.exists("/.dockerenv") or os.getenv("RUNNING_IN_DOCKER") == "true"
        if not is_in_docker:
            self.MONGODB_URL = self.MONGODB_URL.replace("mongodb://mongodb:", "mongodb://localhost:")
            self.REDIS_URL = self.REDIS_URL.replace("redis://valkey:", "redis://localhost:")
            self.QDRANT_URL = self.QDRANT_URL.replace("http://qdrant:", "http://localhost:")
        return self

    # Load from root workspace .env, backend .env, or CWD .env
    model_config = SettingsConfigDict(
        env_file=(
            BASE_DIR / ".env",
            BASE_DIR.parent / ".env",
            ".env"
        ),
        extra="ignore"
    )

settings = Settings()
