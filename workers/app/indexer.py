# workers/app/indexer.py
import uuid
from typing import List, Dict, Any
import structlog
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import PointStruct
from app.config import settings

logger = structlog.get_logger("indexer")

async def index_chunks_to_qdrant(
    chunks: List[Dict[str, Any]],
    workspace_id: str,
    document_id: str,
    filename: str,
    qdrant_client: AsyncQdrantClient
):
    """
    Formulates Qdrant points with vectors and payloads,
    and performs a batch upload to the vector store.
    """
    if not chunks:
        logger.warn("no_chunks_to_index", document_id=document_id)
        return

    points = []
    for chunk in chunks:
        point_id = str(uuid.uuid4())
        point = PointStruct(
            id=point_id,
            vector=chunk["vector"],
            payload={
                "workspace_id": workspace_id,
                "document_id": document_id,
                "filename": filename,
                "text": chunk["text"],
                "page_number": chunk["page_number"]
            }
        )
        points.append(point)

    logger.info("upserting_vectors_to_qdrant", count=len(points), document_id=document_id)
    
    try:
        await qdrant_client.upsert(
            collection_name=settings.QDRANT_COLLECTION_NAME,
            points=points
        )
        logger.info("indexing_to_qdrant_success", document_id=document_id)
    except Exception as e:
        logger.error("indexing_to_qdrant_failed", error=str(e), document_id=document_id)
        raise e
