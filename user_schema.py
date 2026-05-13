from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from enum import Enum


class Role(str, Enum):
    admin = "admin"
    student = "student"


class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)
    name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    department: Optional[str] = None


class UserOut(BaseModel):
    id: str
    username: str
    role: Role

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    username: str
