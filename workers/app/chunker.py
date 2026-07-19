# workers/app/chunker.py
import re
import numpy as np
from typing import List, Dict
import structlog
from langchain_google_genai import GoogleGenAIEmbeddings

from app.config import settings

logger = structlog.get_logger("chunker")

def split_into_sentences(text: str) -> List[Dict]:
    """
    Splits markdown/text into sentences while tracking the active page number
    defined by HTML comment tags (e.g., <!-- PAGE_NUM: 3 -->).
    """
    page_tag_pattern = re.compile(r'<!-- PAGE_NUM: (\d+) -->')
    raw_blocks = text.split('\n\n')
    current_page = 1
    sentences = []
    
    for block in raw_blocks:
        # Check if block contains a page number tag
        match = page_tag_pattern.search(block)
        if match:
            current_page = int(match.group(1))
            
        # Clean block text
        clean_block = page_tag_pattern.sub('', block).strip()
        if not clean_block:
            continue
            
        # Split sentences based on punctuation boundary lookbehinds
        raw_sentences = re.split(r'(?<=[.!?])\s+', clean_block)
        for s in raw_sentences:
            s_clean = s.strip()
            if len(s_clean) > 10: # Filter out noise
                sentences.append({"text": s_clean, "page": current_page})
                
    return sentences

def cosine_similarity(v1, v2):
    dot_product = np.dot(v1, v2)
    norm_v1 = np.linalg.norm(v1)
    norm_v2 = np.linalg.norm(v2)
    if norm_v1 == 0 or norm_v2 == 0:
        return 0.0
    return dot_product / (norm_v1 * norm_v2)

async def semantic_chunk_text(text: str, google_api_key: str, similarity_threshold: float = 0.70) -> List[Dict]:
    """
    Computes sentence-level embeddings using Google Gemini API,
    finds semantic similarity drop boundaries, and returns grouped text chunks.
    """
    sentences = split_into_sentences(text)
    if not sentences:
        return []
        
    if len(sentences) == 1:
        return [{"text": sentences[0]["text"], "page_number": sentences[0]["page"]}]

    # 1. Fetch embeddings for all sentences in a single batch
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
        sentence_texts = [s["text"] for s in sentences]
        # Generate embeddings
        embeddings = await embeddings_model.aembed_documents(sentence_texts)
    except Exception as e:
        logger.error("sentence_embeddings_failed_falling_back_to_window_chunks", error=str(e))
        # Fallback to simple sliding window chunking if API fails
        return fallback_window_chunking(sentences)

    # 2. Compute similarity between consecutive sentences
    chunks = []
    current_chunk_sentences = [sentences[0]]
    
    for i in range(len(sentences) - 1):
        sim = cosine_similarity(embeddings[i], embeddings[i+1])
        
        # If semantic gap is wider than threshold or chunk is getting too big, split
        if sim < similarity_threshold or len(current_chunk_sentences) >= 8:
            # Build current chunk
            chunk_text = " ".join([s["text"] for s in current_chunk_sentences])
            # Assign to the primary page number representing this block
            primary_page = current_chunk_sentences[0]["page"]
            chunks.append({"text": chunk_text, "page_number": primary_page})
            # Reset
            current_chunk_sentences = [sentences[i+1]]
        else:
            current_chunk_sentences.append(sentences[i+1])
            
    # Add final chunk
    if current_chunk_sentences:
        chunk_text = " ".join([s["text"] for s in current_chunk_sentences])
        primary_page = current_chunk_sentences[0]["page"]
        chunks.append({"text": chunk_text, "page_number": primary_page})
        
    logger.info("semantic_chunking_completed", total_sentences=len(sentences), total_chunks=len(chunks))
    return chunks

def fallback_window_chunking(sentences: List[Dict], window_size: int = 4) -> List[Dict]:
    """
    Fallback method that chunks sentences by a fixed window size.
    """
    chunks = []
    for i in range(0, len(sentences), window_size):
        group = sentences[i : i + window_size]
        chunk_text = " ".join([s["text"] for s in group])
        chunks.append({"text": chunk_text, "page_number": group[0]["page"]})
    return chunks
