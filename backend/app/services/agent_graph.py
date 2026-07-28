# backend/app/services/agent_graph.py
"""
Agentic Corrective RAG (CRAG) Service built with LangGraph.
Stateful workflow:
1. Vector Search (Qdrant)
2. Grade Relevance
3. Rewrite Query (if relevance < 0.7, max 2 retries)
4. Generate Final Answer with Sources
"""
import logging
from typing import List, Dict, Any, TypedDict
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue
from langgraph.graph import StateGraph, END
from app.core.config import settings

logger = logging.getLogger("agent_graph")


class CRAGState(TypedDict):
    prompt: str
    current_query: str
    workspace_id: str
    search_results: List[Dict[str, Any]]
    relevance_score: float
    retry_count: int
    final_context: str
    sources: List[Dict[str, Any]]
    response_content: str


async def get_embeddings_model():
    """Dynamically initializes embeddings model based on configuration."""
    if settings.LLM_PROVIDER == "huggingface":
        from langchain_community.embeddings import HuggingFaceHubEmbeddings
        return HuggingFaceHubEmbeddings(
            repo_id="sentence-transformers/all-MiniLM-L6-v2",
            huggingfacehub_api_token=settings.HUGGINGFACE_API_KEY
        )
    else:
        from langchain_google_genai import GoogleGenerativeAIEmbeddings
        return GoogleGenerativeAIEmbeddings(
            model="models/text-embedding-004",
            google_api_key=settings.GEMINI_API_KEY
        )


async def get_chat_model():
    """Dynamically initializes LLM model based on configuration."""
    if settings.LLM_PROVIDER == "huggingface":
        from langchain_community.llms import HuggingFaceHub
        return HuggingFaceHub(
            repo_id="mistralai/Mistral-7B-Instruct-v0.2",
            huggingfacehub_api_token=settings.HUGGINGFACE_API_KEY
        )
    else:
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(
            model="gemini-1.5-flash",
            google_api_key=settings.GEMINI_API_KEY,
            temperature=0.2
        )


async def vector_search_node(state: CRAGState, qdrant: AsyncQdrantClient) -> Dict[str, Any]:
    """Node 1: Searches Qdrant vector DB using current query."""
    query = state.get("current_query") or state["prompt"]
    workspace_id = state["workspace_id"]
    
    try:
        embeddings_model = await get_embeddings_model()
        query_vector = await embeddings_model.aembed_query(query)
        
        search_results = await qdrant.search(
            collection_name=settings.QDRANT_COLLECTION_NAME,
            query_vector=query_vector,
            query_filter=Filter(
                must=[FieldCondition(key="workspace_id", match=MatchValue(value=workspace_id))]
            ),
            limit=5
        )
    except Exception as e:
        logger.error(f"vector_search_failed: {str(e)}")
        search_results = []

    retrieved_context = ""
    sources = []
    scores = []
    
    for res in search_results:
        payload = res.payload or {}
        text = payload.get("text", "")
        filename = payload.get("filename", "Unknown file")
        page = payload.get("page_number", 1)
        score = float(res.score)
        
        scores.append(score)
        sources.append({"filename": filename, "page": page, "score": score})
        retrieved_context += f"--- Source: {filename} (Page {page}) ---\n{text}\n\n"

    avg_score = (sum(scores) / len(scores)) if scores else 0.0

    return {
        "search_results": sources,
        "relevance_score": avg_score,
        "final_context": retrieved_context,
        "sources": sources
    }


async def grade_relevance_node(state: CRAGState) -> Dict[str, Any]:
    """Node 2: Evaluates relevance of retrieved context."""
    context = state.get("final_context", "")
    if not context or state.get("relevance_score", 0.0) < 0.3:
        grade = 0.2
    else:
        grade = state.get("relevance_score", 0.5)

    return {"relevance_score": grade}


async def rewrite_query_node(state: CRAGState) -> Dict[str, Any]:
    """Node 3: Rewrites query if search relevance is low (max 2 retries)."""
    current_retry = state.get("retry_count", 0) + 1
    original_prompt = state["prompt"]

    try:
        llm = await get_chat_model()
        rewrite_prompt = (
            f"You are a search query optimizer. Rewrite the following user question to make it "
            f"more specific and effective for technical document retrieval. Return ONLY the rewritten query text.\n\n"
            f"Original Question: {original_prompt}"
        )
        result = await llm.ainvoke(rewrite_prompt)
        new_query = result.content if hasattr(result, "content") else str(result)
        new_query = new_query.strip().strip('"')
    except Exception:
        new_query = f"{original_prompt} details explanation compliance"

    return {
        "current_query": new_query,
        "retry_count": current_retry
    }


async def generate_answer_node(state: CRAGState) -> Dict[str, Any]:
    """Node 4: Generates final response using LLM."""
    prompt = state["prompt"]
    context = state.get("final_context", "")
    
    try:
        llm = await get_chat_model()
        system_prompt = (
            "You are KnowledgeOS, an AI enterprise search assistant.\n"
            "Answer the question based strictly on the document context below.\n"
            "Cite source filenames and page numbers for facts.\n"
            "If the context does not contain the answer, state that clearly.\n\n"
            f"--- Context ---\n{context if context else 'No document context found.'}\n\n"
            f"User Question: {prompt}"
        )
        result = await llm.ainvoke(system_prompt)
        answer = result.content if hasattr(result, "content") else str(result)
    except Exception as e:
        answer = f"Error generating answer: {str(e)}"

    return {"response_content": answer}


def decide_to_rewrite(state: CRAGState) -> str:
    """Conditional edge router: decides whether to rewrite query or generate answer."""
    score = state.get("relevance_score", 0.0)
    retries = state.get("retry_count", 0)

    if score < 0.5 and retries < 2:
        return "rewrite_query"
    return "generate_answer"


def build_crag_graph(qdrant: AsyncQdrantClient):
    """Compiles the LangGraph StateGraph pipeline."""
    workflow = StateGraph(CRAGState)

    # Add nodes with closure for qdrant client dependency
    async def search_step(state: CRAGState):
        return await vector_search_node(state, qdrant)

    workflow.add_node("vector_search", search_step)
    workflow.add_node("grade_relevance", grade_relevance_node)
    workflow.add_node("rewrite_query", rewrite_query_node)
    workflow.add_node("generate_answer", generate_answer_node)

    # Set flow edges
    workflow.set_entry_point("vector_search")
    workflow.add_edge("vector_search", "grade_relevance")
    workflow.add_conditional_edges(
        "grade_relevance",
        decide_to_rewrite,
        {
            "rewrite_query": "rewrite_query",
            "generate_answer": "generate_answer"
        }
    )
    workflow.add_edge("rewrite_query", "vector_search")
    workflow.add_edge("generate_answer", END)

    return workflow.compile()
