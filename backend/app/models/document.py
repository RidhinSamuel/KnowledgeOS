# backend/app/models/document.py
from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field

class DocumentStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class DocumentResponse(BaseModel):
    id: str = Field(..., alias="_id")
    workspace_id: str
    filename: str
    content_type: str
    size_bytes: int
    status: DocumentStatus
    gridfs_id: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        populate_by_name = True
        json_encoders = {
            datetime: lambda dt: dt.isoformat()
        }
