# workers/app/config.py
import os
from typing import Optional
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class WorkerSettings(BaseSettings):
    LOG_LEVEL: str = "INFO"
    MONGODB_URL: str
    MONGODB_DB_NAME: str = "knowledge_os"
    REDIS_URL: str
    QDRANT_URL: str
    GEMINI_API_KEY: Optional[str] = None
    HUGGINGFACE_API_KEY: Optional[str] = None
    LLAMAPARSE_API_KEY: Optional[str] = None
    QDRANT_COLLECTION_NAME: str = "knowledge_chunks"
    
    @model_validator(mode="after")
    def resolve_docker_vs_localhost(self):
        """
        Seamless Hybrid Execution:
        If running directly on local host (outside Docker), automatically map container service 
        names ('mongodb', 'valkey', 'qdrant') to 'localhost' so the worker connects cleanly.
        """
        is_in_docker = os.path.exists("/.dockerenv") or os.getenv("RUNNING_IN_DOCKER") == "true"
        if not is_in_docker:
            if hasattr(self, "MONGODB_URL") and self.MONGODB_URL:
                self.MONGODB_URL = self.MONGODB_URL.replace("mongodb://mongodb:", "mongodb://localhost:")
            if hasattr(self, "REDIS_URL") and self.REDIS_URL:
                self.REDIS_URL = self.REDIS_URL.replace("redis://valkey:", "redis://localhost:")
                self.REDIS_URL = self.REDIS_URL.replace("redis://redis:", "redis://localhost:")
            if hasattr(self, "QDRANT_URL") and self.QDRANT_URL:
                self.QDRANT_URL = self.QDRANT_URL.replace("http://qdrant:", "http://localhost:")
        return self

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = WorkerSettings()

