# workers/app/embedder.py
from typing import List, Dict, Any
import structlog
from langchain_google_genai import GoogleGenAIEmbeddings

from app.config import settings

logger = structlog.get_logger("embedder")

async def generate_chunk_embeddings(chunks: List[Dict[str, Any]], google_api_key: str) -> List[Dict[str, Any]]:
    """
    Takes a list of chunks (containing text and page_number)
    and generates vector embeddings for each using Google Gemini API.
    """
    if not chunks:
        return []
        
    try:
        if settings.LLM_PROVIDER == "huggingface":
            from langchain_community.embeddings import HuggingFaceHubEmbeddings
            embeddings_model = HuggingFaceHubEmbeddings(
                repo_id="sentence-transformers/all-MiniLM-L6-v2",
                huggingfacehub_api_token=settings.HUGGINGFACE_API_KEY
            )
        else:
            embeddings_model = GoogleGenAIEmbeddings(
                model="models/text-embedding-004", 
                google_api_key=google_api_key
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
