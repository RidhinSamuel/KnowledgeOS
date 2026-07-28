# backend/app/api/v1/chat.py
import asyncio
from datetime import datetime, timezone
import json
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from qdrant_client import AsyncQdrantClient
import redis.asyncio as aioredis

from app.core.database import get_db, get_qdrant, get_redis
from app.core.config import settings
from app.core.security import get_current_user_token
from app.models.chat import ChatSessionCreate, ChatSessionResponse, MessageResponse, ChatPrompt
from app.services.cache_service import get_cached_query_response, set_cached_query_response
from app.services.agent_graph import build_crag_graph

router = APIRouter()

@router.post("/session", response_model=ChatSessionResponse, status_code=status.HTTP_201_CREATED)
async def create_chat_session(
    workspace_id: str,
    session_in: ChatSessionCreate,
    db: AsyncIOMotorDatabase = Depends(get_db),
    token_payload: dict = Depends(get_current_user_token)
):
    user_id = token_payload.get("sub")
    
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
    redis_client: aioredis.Redis = Depends(get_redis),
    token_payload: dict = Depends(get_current_user_token)
):
    user_id = token_payload.get("sub")
    
    session = await db.chat_sessions.find_one({"_id": ObjectId(session_id)})
    if not session or session["user_id"] != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this session"
        )
        
    workspace_id = session["workspace_id"]
    user_prompt = prompt_in.prompt
    
    async def sse_event_generator():
        # Save User Message to Mongo
        await db.messages.insert_one({
            "session_id": session_id,
            "sender": "user",
            "content": user_prompt,
            "created_at": datetime.now(timezone.utc)
        })

        # 1. Check Redis Cache first (0ms latency & 0 tokens for identical questions)
        cached_payload = await get_cached_query_response(workspace_id, user_prompt, redis_client)
        if cached_payload:
            sources = cached_payload.get("sources", [])
            content = cached_payload.get("content", "")
            
            yield f"data: {json.dumps({'event': 'sources', 'data': sources})}\n\n"
            
            # Stream cached words
            words = content.split(" ")
            for word in words:
                token = word + " "
                yield f"data: {json.dumps({'event': 'token', 'data': token})}\n\n"
                await asyncio.sleep(0.01)

            # Save Assistant Message to Mongo
            await db.messages.insert_one({
                "session_id": session_id,
                "sender": "assistant",
                "content": content,
                "created_at": datetime.now(timezone.utc)
            })
            yield "data: [DONE]\n\n"
            return

        # 2. Cache Miss -> Run LangGraph CRAG pipeline
        full_response = ""
        sources = []
        try:
            crag_graph = build_crag_graph(qdrant)
            initial_state = {
                "prompt": user_prompt,
                "current_query": user_prompt,
                "workspace_id": workspace_id,
                "search_results": [],
                "relevance_score": 0.0,
                "retry_count": 0,
                "final_context": "",
                "sources": [],
                "response_content": ""
            }
            
            final_state = await crag_graph.ainvoke(initial_state)
            sources = final_state.get("sources", [])
            full_response = final_state.get("response_content", "")
            
            yield f"data: {json.dumps({'event': 'sources', 'data': sources})}\n\n"

            # Stream generated tokens
            words = full_response.split(" ")
            for word in words:
                token = word + " "
                yield f"data: {json.dumps({'event': 'token', 'data': token})}\n\n"
                await asyncio.sleep(0.02)

            # 3. Store response in Redis cache for subsequent hits
            await set_cached_query_response(
                workspace_id=workspace_id,
                prompt=user_prompt,
                content=full_response,
                sources=sources,
                redis_client=redis_client
            )

        except Exception as e:
            error_msg = f"LangGraph CRAG Error: {str(e)}"
            yield f"data: {json.dumps({'event': 'error', 'data': error_msg})}\n\n"
            full_response = f"Error processing query: {str(e)}"

        # Save Assistant Message to Mongo
        await db.messages.insert_one({
            "session_id": session_id,
            "sender": "assistant",
            "content": full_response,
            "created_at": datetime.now(timezone.utc)
        })

        yield "data: [DONE]\n\n"

    return StreamingResponse(sse_event_generator(), media_type="text/event-stream")
