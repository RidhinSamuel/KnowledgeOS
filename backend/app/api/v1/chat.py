# backend/app/api/v1/chat.py
from datetime import datetime, timezone
import json
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue
from langchain_google_genai import ChatGoogleGenAI, GoogleGenAIEmbeddings
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

from app.core.database import get_db, get_qdrant
from app.core.config import settings
from app.core.security import get_current_user_token
from app.models.chat import ChatSessionCreate, ChatSessionResponse, MessageResponse, ChatPrompt

router = APIRouter()

@router.post("/session", response_model=ChatSessionResponse, status_code=status.HTTP_201_CREATED)
async def create_chat_session(
    workspace_id: str,
    session_in: ChatSessionCreate,
    db: AsyncIOMotorDatabase = Depends(get_db),
    token_payload: dict = Depends(get_current_user_token)
):
    user_id = token_payload.get("sub")
    
    # Verify workspace membership
    workspace = await db.workspaces.find_one({"_id": ObjectId(workspace_id)})
    if not workspace or not any(m["user_id"] == user_id for m in workspace["members"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this workspace"
        )
        
    session_doc = {
        "workspace_id": workspace_id,
        "user_id": user_id,
        "title": session_in.title,
        "created_at": datetime.now(timezone.utc)
    }
    
    result = await db.chat_sessions.insert_one(session_doc)
    session_doc["_id"] = str(result.inserted_id)
    return session_doc

@router.get("/session/workspace/{workspace_id}", response_model=List[ChatSessionResponse])
async def list_chat_sessions(
    workspace_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    token_payload: dict = Depends(get_current_user_token)
):
    user_id = token_payload.get("sub")
    
    # Verify workspace membership
    workspace = await db.workspaces.find_one({"_id": ObjectId(workspace_id)})
    if not workspace or not any(m["user_id"] == user_id for m in workspace["members"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to workspace chat sessions"
        )
        
    cursor = db.chat_sessions.find({"workspace_id": workspace_id, "user_id": user_id})
    sessions = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        sessions.append(doc)
    return sessions

@router.get("/session/{session_id}/messages", response_model=List[MessageResponse])
async def get_chat_messages(
    session_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    token_payload: dict = Depends(get_current_user_token)
):
    user_id = token_payload.get("sub")
    
    # Verify session ownership
    session = await db.chat_sessions.find_one({"_id": ObjectId(session_id)})
    if not session or session["user_id"] != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this session"
        )
        
    cursor = db.messages.find({"session_id": session_id}).sort("created_at", 1)
    messages = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        messages.append(doc)
    return messages

@router.post("/session/{session_id}/stream")
async def stream_chat_response(
    session_id: str,
    prompt_in: ChatPrompt,
    db: AsyncIOMotorDatabase = Depends(get_db),
    qdrant: AsyncQdrantClient = Depends(get_qdrant),
    token_payload: dict = Depends(get_current_user_token)
):
    user_id = token_payload.get("sub")
    
    # 1. Verify session exists and belongs to user
    session = await db.chat_sessions.find_one({"_id": ObjectId(session_id)})
    if not session or session["user_id"] != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this session"
        )
        
    workspace_id = session["workspace_id"]
    user_prompt = prompt_in.prompt
    
    # 2. Retrieve vector embeddings for the prompt via dynamic Provider selection
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
                google_api_key=settings.GEMINI_API_KEY
            )
        query_vector = await embeddings_model.aembed_query(user_prompt)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate query embeddings: {str(e)}"
        )
        
    # 3. Retrieve matching context chunks from Qdrant with tenant payload filtering
    try:
        search_results = await qdrant.search(
            collection_name=settings.QDRANT_COLLECTION_NAME,
            query_vector=query_vector,
            query_filter=Filter(
                must=[
                    FieldCondition(key="workspace_id", match=MatchValue(value=workspace_id))
                ]
            ),
            limit=5
        )
    except Exception as e:
        search_results = []
        # If vector database fails, we proceed without context fallback, letting the system run log warnings
        
    # Compile retrieved texts
    retrieved_context = ""
    sources = []
    for res in search_results:
        payload = res.payload or {}
        text = payload.get("text", "")
        filename = payload.get("filename", "Unknown file")
        page = payload.get("page_number", 1)
        score = res.score
        
        sources.append({"filename": filename, "page": page, "score": score})
        retrieved_context += f"--- Source File: {filename} (Page {page}) ---\n{text}\n\n"
        
    # 4. Fetch chat history (last 10 messages)
    history_cursor = db.messages.find({"session_id": session_id}).sort("created_at", 1).limit(10)
    chat_history = []
    async for msg in history_cursor:
        chat_history.append(msg)
        
    # 5. Build prompt with context and history
    system_prompt = (
        "You are KnowledgeOS, a premium AI search assistant. "
        "Answer the user's prompt based solely on the retrieved documents context below. "
        "Always cite the source files and page numbers where your facts come from. "
        "If you cannot answer using the context provided, politely state that the information "
        "is not available in the workspace documents. Do not hallucinate or make up facts.\n\n"
        f"--- Retrieved Context ---\n{retrieved_context}"
    )
    
    messages = [SystemMessage(content=system_prompt)]
    for msg in chat_history:
        if msg["sender"] == "user":
            messages.append(HumanMessage(content=msg["content"]))
        else:
            messages.append(AIMessage(content=msg["content"]))
            
    messages.append(HumanMessage(content=user_prompt))
    
    # 6. Stream tokens via SSE async generator
    async def sse_event_generator():
        # Save User Message to Mongo
        await db.messages.insert_one({
            "session_id": session_id,
            "sender": "user",
            "content": user_prompt,
            "created_at": datetime.now(timezone.utc)
        })
        
        # Yield metadata sources first
        yield f"data: {json.dumps({'event': 'sources', 'data': sources})}\n\n"
        
        full_response = ""
        try:
            if settings.LLM_PROVIDER == "huggingface":
                from langchain_community.llms import HuggingFaceHub
                llm = HuggingFaceHub(
                    repo_id="mistralai/Mistral-7B-Instruct-v0.3",
                    huggingfacehub_api_token=settings.HUGGINGFACE_API_KEY,
                    model_kwargs={"temperature": 0.7, "max_new_tokens": 512}
                )
                
                # Format a text-based instruction prompt for the model
                prompt_text = ""
                for m in messages:
                    prompt_text += f"{m.content}\n"
                
                # Call endpoint asynchronously
                response_text = await llm.ainvoke(prompt_text)
                
                # Simulate smooth word streaming output
                words = response_text.split(" ")
                for word in words:
                    token = word + " "
                    full_response += token
                    yield f"data: {json.dumps({'event': 'token', 'data': token})}\n\n"
                    await asyncio.sleep(0.03) # Simulates text typing speed
            else:
                llm = ChatGoogleGenAI(
                    model="gemini-1.5-flash", 
                    google_api_key=settings.GEMINI_API_KEY, 
                    streaming=True
                )
                async for chunk in llm.astream(messages):
                    token = chunk.content
                    full_response += token
                    yield f"data: {json.dumps({'event': 'token', 'data': token})}\n\n"
        except Exception as e:
            error_msg = f"LLM error: {str(e)}"
            yield f"data: {json.dumps({'event': 'error', 'data': error_msg})}\n\n"
            full_response += f"\n[Error: {error_msg}]"
            
        # Save Assistant Message to Mongo
        await db.messages.insert_one({
            "session_id": session_id,
            "sender": "assistant",
            "content": full_response,
            "created_at": datetime.now(timezone.utc)
        })
        
        yield "data: [DONE]\n\n"
        
    return StreamingResponse(sse_event_generator(), media_type="text/event-stream")
