# backend/app/models/user.py
from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from pydantic.functional_serializers import PlainSerializer
from typing import Annotated

DateTimeStr = Annotated[datetime, PlainSerializer(lambda dt: dt.isoformat(), return_type=str)]

class UserRole(str, Enum):
    OWNER = "Owner"
    EDITOR = "Editor"
    VIEWER = "Viewer"

class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)
    full_name: str
    role: UserRole = UserRole.VIEWER

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: str = Field(..., alias="_id")
    email: EmailStr
    full_name: str
    role: UserRole
    created_at: datetime

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class TokenPayload(BaseModel):
    sub: str
    role: str
    exp: int
