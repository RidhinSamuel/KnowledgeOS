# backend/app/models/workspace.py
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field

class WorkspaceMember(BaseModel):
    user_id: str
    role: str # Owner, Editor, Viewer

class WorkspaceCreate(BaseModel):
    name: str = Field(..., min_length=3, max_length=50)
    description: Optional[str] = None

class WorkspaceResponse(BaseModel):
    id: str = Field(..., alias="_id")
    name: str
    description: Optional[str] = None
    owner_id: str
    members: List[WorkspaceMember] = []
    created_at: datetime

    class Config:
        populate_by_name = True
        json_encoders = {
            datetime: lambda dt: dt.isoformat()
        }
