# backend/app/core/database.py
import logging
import motor.motor_asyncio
import redis.asyncio as aioredis
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance, VectorParams
from app.core.config import settings

logger = logging.getLogger("database")

class DatabaseManager:
    def __init__(self):
        self.mongo_client: motor.motor_asyncio.AsyncIOMotorClient = None
        self.db = None
        self.redis_client: aioredis.Redis = None
        self.qdrant_client: AsyncQdrantClient = None

    async def connect(self):
        logger.info("Connecting to databases...")
        # MongoDB Setup
        self.mongo_client = motor.motor_asyncio.AsyncIOMotorClient(settings.MONGODB_URL)
        self.db = self.mongo_client[settings.MONGODB_DB_NAME]
        
        # Redis Stream Setup
        self.redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        
        # Qdrant Setup
        self.qdrant_client = AsyncQdrantClient(url=settings.QDRANT_URL)

        # Enforce schemas
        await self._ensure_qdrant_collection()

    async def disconnect(self):
        logger.info("Disconnecting from databases...")
        if self.mongo_client:
            self.mongo_client.close()
        if self.redis_client:
            await self.redis_client.close()
        if self.qdrant_client:
            await self.qdrant_client.close()

    async def _ensure_qdrant_collection(self):
        try:
            # Check if collection exists
            exists = await self.qdrant_client.collection_exists(settings.QDRANT_COLLECTION_NAME)
            if not exists:
                logger.info(f"Creating Qdrant collection: {settings.QDRANT_COLLECTION_NAME}")
                # We use 768 dimensions for Google Gemini text-embedding-004
                dimension = 768
                await self.qdrant_client.create_collection(
                    collection_name=settings.QDRANT_COLLECTION_NAME,
                    vectors_config=VectorParams(size=dimension, distance=Distance.COSINE)
                )
                
                # Create payload filter index on workspace_id for strict O(1) multi-tenancy isolation
                logger.info(f"Creating keyword index on workspace_id")
                await self.qdrant_client.create_payload_index(
                    collection_name=settings.QDRANT_COLLECTION_NAME,
                    field_name="workspace_id",
                    field_schema="keyword"
                )
        except Exception as e:
            logger.error(f"Error checking/creating Qdrant collection: {e}")

# Global db instance
db_manager = DatabaseManager()

# Dependency providers
def get_db():
    return db_manager.db

def get_redis():
    return db_manager.redis_client

def get_qdrant():
    return db_manager.qdrant_client
