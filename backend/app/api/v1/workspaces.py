# backend/app/api/v1/workspaces.py
from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from app.core.database import get_db
from app.core.security import get_current_user_token
from app.models.workspace import WorkspaceCreate, WorkspaceResponse, WorkspaceMember

router = APIRouter()

@router.post("/", response_model=WorkspaceResponse, status_code=status.HTTP_201_CREATED)
async def create_workspace(
    workspace_in: WorkspaceCreate,
    db: AsyncIOMotorDatabase = Depends(get_db),
    token_payload: dict = Depends(get_current_user_token)
):
    user_id = token_payload.get("sub")
    
    # Prepare workspace document
    workspace_doc = {
        "name": workspace_in.name,
        "description": workspace_in.description,
        "owner_id": user_id,
        "members": [
            {"user_id": user_id, "role": "Owner"}
        ],
        "created_at": datetime.now(timezone.utc)
    }
    
    result = await db.workspaces.insert_one(workspace_doc)
    workspace_doc["_id"] = str(result.inserted_id)
    return workspace_doc

@router.get("/", response_model=List[WorkspaceResponse])
async def list_workspaces(
    db: AsyncIOMotorDatabase = Depends(get_db),
    token_payload: dict = Depends(get_current_user_token)
):
    user_id = token_payload.get("sub")
    
    # Find all workspaces where the user is a member
    cursor = db.workspaces.find({"members.user_id": user_id})
    workspaces = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        workspaces.append(doc)
    return workspaces

@router.get("/{workspace_id}", response_model=WorkspaceResponse)
async def get_workspace(
    workspace_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    token_payload: dict = Depends(get_current_user_token)
):
    user_id = token_payload.get("sub")
    
    # Find the workspace
    workspace = await db.workspaces.find_one({"_id": ObjectId(workspace_id)})
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found"
        )
    
    # Check if the user is a member
    is_member = any(m["user_id"] == user_id for m in workspace["members"])
    if not is_member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this workspace"
        )
    
    workspace["_id"] = str(workspace["_id"])
    return workspace

@router.delete("/{workspace_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workspace(
    workspace_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    token_payload: dict = Depends(get_current_user_token)
):
    user_id = token_payload.get("sub")
    
    workspace = await db.workspaces.find_one({"_id": ObjectId(workspace_id)})
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found"
        )
    
    # Only the Owner can delete the workspace
    if workspace["owner_id"] != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the workspace owner can delete it"
        )
    
    # Delete the workspace document
    await db.workspaces.delete_one({"_id": ObjectId(workspace_id)})
    
    # Cleanup: Delete all documents in this workspace from metadata
    await db.documents.delete_many({"workspace_id": workspace_id})
    
    # Note: Vector deletion from Qdrant is also needed. Let's import database manager here or handle it.
    from app.core.database import db_manager
    try:
        from qdrant_client.models import Filter, FieldCondition, MatchValue
        await db_manager.qdrant_client.delete(
            collection_name=settings.QDRANT_COLLECTION_NAME,
            points_selector=Filter(
                must=[
                    FieldCondition(key="workspace_id", match=MatchValue(value=workspace_id))
                ]
            )
        )
    except Exception as e:
        # Don't crash if Qdrant call fails, log it
        pass
    
    return None
