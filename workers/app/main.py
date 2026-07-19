# workers/app/main.py
import asyncio
import os
import signal
import socket
from datetime import datetime, timezone
import structlog
from bson import ObjectId
import motor.motor_asyncio
import redis.asyncio as aioredis
from qdrant_client import AsyncQdrantClient

from app.config import settings
from app.parser import parse_document
from app.chunker import semantic_chunk_text
from app.embedder import generate_chunk_embeddings
from app.indexer import index_chunks_to_qdrant
from app.graphify_runner import run_graphify_on_chunks, is_graphify_installed

# Configure structlog
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer() if settings.LOG_LEVEL == "INFO" else structlog.dev.ConsoleRenderer()
    ],
    logger_factory=structlog.PrintLoggerFactory(),
)
logger = structlog.get_logger("worker")

# Define global clients
mongo_client = None
db = None
redis_client = None
qdrant_client = None

# Worker identifier
worker_name = f"worker-{socket.gethostname()}-{os.getpid()}"
keep_running = True

# Max Ingestion Retries
MAX_RETRIES = 3

async def init_services():
    global mongo_client, db, redis_client, qdrant_client
    logger.info("initializing_worker_services")
    
    # DB Connect
    mongo_client = motor.motor_asyncio.AsyncIOMotorClient(settings.MONGODB_URL)
    db = mongo_client[settings.MONGODB_DB_NAME]
    
    # Redis Connection
    redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    
    # Qdrant client connection
    qdrant_client = AsyncQdrantClient(url=settings.QDRANT_URL)
    
    # Ensure Stream and Consumer Group exist
    try:
        await redis_client.xgroup_create(
            name="stream:document_ingestion",
            groupname="group:ingestion_workers",
            id="0",
            mkstream=True
        )
        logger.info("redis_consumer_group_created")
    except Exception:
        # Stream group already exists
        logger.debug("redis_consumer_group_already_exists")

async def close_services():
    global mongo_client, redis_client, qdrant_client
    logger.info("closing_worker_services")
    if mongo_client:
        mongo_client.close()
    if redis_client:
        await redis_client.close()
    if qdrant_client:
        await qdrant_client.close()

async def process_task(task_id: str, fields: dict):
    """
    Core document ingestion orchestration.
    Loads PDF bytes, parses layout, computes semantic chunks, embeds, and indexes.
    """
    doc_id = fields.get("document_id")
    workspace_id = fields.get("workspace_id")
    gridfs_id = fields.get("gridfs_id")
    retry_count = int(fields.get("retry_count", 0))
    
    logger.info("processing_document_task_started", doc_id=doc_id, retry=retry_count)

    # 1. Fetch document record and transition state to PROCESSING
    doc_record = await db.documents.find_one({"_id": ObjectId(doc_id)})
    if not doc_record:
        logger.error("document_record_not_found_aborting", doc_id=doc_id)
        return True # Return true to ACK so it's cleared
        
    await db.documents.update_one(
        {"_id": ObjectId(doc_id)},
        {"$set": {"status": "PROCESSING", "updated_at": datetime.now(timezone.utc)}}
    )

    try:
        # 2. Download file bytes from MongoDB GridFS
        fs = motor.motor_asyncio.AsyncIOMotorGridFSBucket(db)
        grid_out = await fs.open_download_stream(ObjectId(gridfs_id))
        file_bytes = await grid_out.read()
        filename = doc_record["filename"]

        # 3. Parse PDF layout and extract text
        parsed_text = await parse_document(file_bytes, filename)
        
        # 4. Generate semantic chunks
        chunks = await semantic_chunk_text(parsed_text, settings.GEMINI_API_KEY)
        
        # 5. Generate vector embeddings for the chunks
        chunks_with_vectors = await generate_chunk_embeddings(chunks, settings.GEMINI_API_KEY)
        
        # 6. Index chunks into Qdrant vector database
        await index_chunks_to_qdrant(
            chunks=chunks_with_vectors,
            workspace_id=workspace_id,
            document_id=doc_id,
            filename=filename,
            qdrant_client=qdrant_client,
            db=db
        )

        # 7. Update document state to COMPLETED
        await db.documents.update_one(
            {"_id": ObjectId(doc_id)},
            {"$set": {"status": "COMPLETED", "updated_at": datetime.now(timezone.utc)}}
        )
        logger.info("document_processing_success", doc_id=doc_id)

        # 8. Build Knowledge Graph via Graphify CLI (primary) or Gemini extractor (fallback)
        # ─────────────────────────────────────────────────────────────────────────────────
        # Graphify delivers 71.5x token reduction per query vs raw chunk retrieval.
        # Runs as a non-blocking subprocess — ingestion is already committed above.
        if await is_graphify_installed():
            logger.info("graphify_available_using_graphify_cli", doc_id=doc_id)
            graphify_success = await run_graphify_on_chunks(
                chunks=chunks_with_vectors,
                workspace_id=workspace_id,
                document_id=doc_id,
                filename=filename,
                db=db
            )
            if not graphify_success:
                logger.warn("graphify_failed_skipping_graph_for_doc", doc_id=doc_id)
        else:
            logger.info("graphify_not_found_graph_extraction_skipped",
                        hint="Run: pip install graphifyy && graphify install")

        return True

    except Exception as e:
        logger.error("document_processing_failed", doc_id=doc_id, error=str(e))
        new_retry = retry_count + 1
        
        if new_retry >= MAX_RETRIES:
            logger.error("max_retries_reached_moving_to_dlq", doc_id=doc_id)
            # Update Mongo status to FAILED
            await db.documents.update_one(
                {"_id": ObjectId(doc_id)},
                {"$set": {
                    "status": "FAILED", 
                    "error_message": f"Ingestion error: {str(e)}",
                    "updated_at": datetime.now(timezone.utc)
                }}
            )
            # Route payload to Dead Letter Queue (DLQ)
            dlq_payload = {
                "document_id": doc_id,
                "workspace_id": workspace_id,
                "gridfs_id": gridfs_id,
                "failed_at": datetime.now(timezone.utc).isoformat(),
                "error": str(e)
            }
            await redis_client.xadd("stream:dlq", dlq_payload, id="*")
        else:
            logger.warn("requeueing_task_for_retry", doc_id=doc_id, next_retry=new_retry)
            # Requeue with incremented retry count
            retry_payload = {
                "document_id": doc_id,
                "workspace_id": workspace_id,
                "gridfs_id": gridfs_id,
                "retry_count": str(new_retry)
            }
            # Put back in queue and ACK original
            await redis_client.xadd("stream:document_ingestion", retry_payload, id="*")
            
        return False

async def worker_loop():
    global keep_running
    logger.info("worker_listener_loop_started", worker=worker_name)
    
    while keep_running:
        try:
            # Poll consumer group for new messages
            # BLOCK for 2000ms. '>' reads new messages that were not processed by other consumers
            response = await redis_client.xreadgroup(
                groupname="group:ingestion_workers",
                consumername=worker_name,
                streams={"stream:document_ingestion": ">"},
                count=1,
                block=2000
            )
            
            if not response:
                continue

            for stream_name, messages in response:
                for msg_id, fields in messages:
                    # Process message
                    success = await process_task(msg_id, fields)
                    
                    # Always acknowledge the message to remove it from the Pending Entries List (PEL)
                    # For retries, we already added a new message to the stream
                    await redis_client.xack("stream:document_ingestion", "group:ingestion_workers", msg_id)
                    logger.debug("message_acknowledged", message_id=msg_id)
                    
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error("worker_loop_exception", error=str(e))
            await asyncio.sleep(2) # Sleep to avoid spamming CPU on error

def handle_shutdown(signum, frame):
    global keep_running
    logger.info("received_shutdown_signal_initiating_graceful_exit")
    keep_running = False

async def main():
    # Register shutdown signals
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop = asyncio.get_running_loop()
            loop.add_signal_handler(sig, lambda: asyncio.create_task(shutdown_wrapper()))
        except NotImplementedError:
            # add_signal_handler not implemented on Windows. Fallback.
            signal.signal(sig, handle_shutdown)
            
    await init_services()
    await worker_loop()
    await close_services()

async def shutdown_wrapper():
    global keep_running
    logger.info("received_shutdown_signal_initiating_graceful_exit")
    keep_running = False

if __name__ == "__main__":
    asyncio.run(main())
