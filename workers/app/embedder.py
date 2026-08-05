# workers/app/embedder.py
import sys
from pathlib import Path
workers_dir = Path(__file__).resolve().parent.parent
if str(workers_dir) not in sys.path:
    sys.path.insert(0, str(workers_dir))

import os
from typing import List, Dict, Any
import structlog
from langchain_huggingface import HuggingFaceEndpointEmbeddings

from app.config import settings

logger = structlog.get_logger("embedder")

async def generate_chunk_embeddings(chunks: List[Dict[str, Any]], google_api_key: str = None) -> List[Dict[str, Any]]:
    """
    Takes a list of chunks (containing text and page_number)
    and generates vector embeddings for each using HuggingFace Endpoint Embeddings.
    """
    if not chunks:
        return []
        
    try:
        hf_token = os.environ.get("HUGGINGFACE_API_KEY") or getattr(settings, "HUGGINGFACE_API_KEY", None)
        embeddings_model = HuggingFaceEndpointEmbeddings(
            model="sentence-transformers/all-MiniLM-L6-v2",
            task="feature-extraction",
            huggingfacehub_api_token=hf_token
        )
            
        texts = [c["text"] for c in chunks]
        
        # Call API
        vectors = await embeddings_model.aembed_documents(texts)
        
        # Merge back
        for i, chunk in enumerate(chunks):
            chunk["vector"] = vectors[i]
            
        logger.info("embeddings_generation_success", count=len(chunks))
        return chunks
    except Exception as e:
        logger.error("embeddings_generation_failed", error=str(e))
        raise e

