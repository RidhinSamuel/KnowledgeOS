# backend/app/models/chat.py
from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict

class MessageSender(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"

class ChatPrompt(BaseModel):
    prompt: str = Field(..., min_length=1)

class MessageResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: str = Field(..., alias="_id")
    session_id: str
    sender: MessageSender
    content: str
    created_at: datetime

class ChatSessionCreate(BaseModel):
    title: Optional[str] = "New Chat Session"

class ChatSessionResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: str = Field(..., alias="_id")
    workspace_id: str
    user_id: str
    title: str
    created_at: datetime
