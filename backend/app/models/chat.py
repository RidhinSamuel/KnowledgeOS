# backend/app/models/chat.py
from datetime import datetime
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field

class MessageSender(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"

class ChatPrompt(BaseModel):
    prompt: str = Field(..., min_length=1)

class MessageResponse(BaseModel):
    id: str = Field(..., alias="_id")
    session_id: str
    sender: MessageSender
    content: str
    created_at: datetime

    class Config:
        populate_by_name = True
        json_encoders = {
            datetime: lambda dt: dt.isoformat()
        }

class ChatSessionCreate(BaseModel):
    title: Optional[str] = "New Chat Session"

class ChatSessionResponse(BaseModel):
    id: str = Field(..., alias="_id")
    workspace_id: str
    user_id: str
    title: str
    created_at: datetime

    class Config:
        populate_by_name = True
        json_encoders = {
            datetime: lambda dt: dt.isoformat()
        }
