# backend/app/api/v1/documents.py
from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorGridFSBucket
from bson import ObjectId
import redis.asyncio as aioredis
from app.core.database import get_db, get_redis
from app.core.security import get_current_user_token
from app.models.document import DocumentResponse, DocumentStatus

router = APIRouter()

@router.post("/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    workspace_id: str,
    file: UploadFile = File(...),
    db: AsyncIOMotorDatabase = Depends(get_db),
    redis_client: aioredis.Redis = Depends(get_redis),
    token_payload: dict = Depends(get_current_user_token)
):
    user_id = token_payload.get("sub")
    
    # 1. Verify workspace exists and user has access
    workspace = await db.workspaces.find_one({"_id": ObjectId(workspace_id)})
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found"
        )
    
    is_member = any(m["user_id"] == user_id for m in workspace["members"])
    if not is_member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this workspace"
        )
    
    # Check if the file is a PDF
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF file uploads are currently supported"
        )
        
    # Read file content for size checking and storage
    file_bytes = await file.read()
    size_bytes = len(file_bytes)
    
    # Restrict to 50MB
    if size_bytes > 50 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File size exceeds the 50MB maximum limit"
        )
    
    # 2. Upload PDF binary to MongoDB GridFS
    fs = AsyncIOMotorGridFSBucket(db)
    grid_in = await fs.open_upload_stream(
        filename=file.filename,
        metadata={"content_type": file.content_type, "workspace_id": workspace_id}
    )
    await grid_in.write(file_bytes)
    await grid_in.close()
    gridfs_id = str(grid_in._id)
    
    # 3. Create document record in database
    doc_record = {
        "workspace_id": workspace_id,
        "filename": file.filename,
        "content_type": file.content_type,
        "size_bytes": size_bytes,
        "status": DocumentStatus.PENDING.value,
        "gridfs_id": gridfs_id,
        "error_message": None,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    }
    
    result = await db.documents.insert_one(doc_record)
    doc_id = str(result.inserted_id)
    doc_record["_id"] = doc_id
    
    # 4. Schedule processing task by writing to Valkey Redis Stream
    try:
        task_payload = {
            "document_id": doc_id,
            "workspace_id": workspace_id,
            "gridfs_id": gridfs_id,
            "retry_count": "0"
        }
        await redis_client.xadd(
            name="stream:document_ingestion",
            fields=task_payload,
            id="*"
        )
    except Exception as e:
        # If task scheduling fails, mark document as failed
        await db.documents.update_one(
            {"_id": ObjectId(doc_id)},
            {"$set": {"status": DocumentStatus.FAILED.value, "error_message": f"Scheduling error: {str(e)}"}}
        )
        doc_record["status"] = DocumentStatus.FAILED.value
        doc_record["error_message"] = f"Scheduling error: {str(e)}"
        
    return doc_record

@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document_status(
    document_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    token_payload: dict = Depends(get_current_user_token)
):
    user_id = token_payload.get("sub")
    
    # Get document
    doc = await db.documents.find_one({"_id": ObjectId(document_id)})
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
        
    # Get workspace to verify access permissions
    workspace = await db.workspaces.find_one({"_id": ObjectId(doc["workspace_id"])})
    if not workspace or not any(m["user_id"] == user_id for m in workspace["members"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this document"
        )
        
    doc["_id"] = str(doc["_id"])
    return doc

@router.get("/workspace/{workspace_id}", response_model=List[DocumentResponse])
async def list_workspace_documents(
    workspace_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    token_payload: dict = Depends(get_current_user_token)
):
    user_id = token_payload.get("sub")
    
    # Verify access to workspace
    workspace = await db.workspaces.find_one({"_id": ObjectId(workspace_id)})
    if not workspace or not any(m["user_id"] == user_id for m in workspace["members"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to workspace documents"
        )
        
    cursor = db.documents.find({"workspace_id": workspace_id})
    documents = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        documents.append(doc)
    return documents

@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    token_payload: dict = Depends(get_current_user_token)
):
    user_id = token_payload.get("sub")
    
    doc = await db.documents.find_one({"_id": ObjectId(document_id)})
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
        
    workspace = await db.workspaces.find_one({"_id": ObjectId(doc["workspace_id"])})
    if not workspace:
         raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found"
        )
         
    # Only Owner or Editor roles can delete files
    user_member = next((m for m in workspace["members"] if m["user_id"] == user_id), None)
    if not user_member or user_member["role"] not in ["Owner", "Editor"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions to delete this document"
        )
        
    # 1. Delete binary from GridFS
    if doc.get("gridfs_id"):
        fs = AsyncIOMotorGridFSBucket(db)
        try:
            await fs.delete(ObjectId(doc["gridfs_id"]))
        except Exception:
            pass # Ignore if not found
            
    # 2. Delete vectors from Qdrant
    from app.core.database import db_manager
    from app.core.config import settings
    try:
        from qdrant_client.models import Filter, FieldCondition, MatchValue
        await db_manager.qdrant_client.delete(
            collection_name=settings.QDRANT_COLLECTION_NAME,
            points_selector=Filter(
                must=[
                    FieldCondition(key="document_id", match=MatchValue(value=document_id))
                ]
            )
        )
    except Exception:
        pass
        
    # 3. Delete metadata document
    await db.documents.delete_one({"_id": ObjectId(document_id)})
    return None
