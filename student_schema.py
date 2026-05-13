from pydantic import BaseModel, EmailStr, Field
from typing import Optional


class StudentCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    department: Optional[str] = None
    math: Optional[float] = Field(None, ge=0, le=100)
    programming: Optional[float] = Field(None, ge=0, le=100)
    database: Optional[float] = Field(None, ge=0, le=100)


class StudentUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    email: Optional[EmailStr] = None
    department: Optional[str] = None
    math: Optional[float] = Field(None, ge=0, le=100)
    programming: Optional[float] = Field(None, ge=0, le=100)
    database: Optional[float] = Field(None, ge=0, le=100)


class StudentOut(BaseModel):
    id: str
    name: str
    email: str
    department: Optional[str] = None
    math: Optional[float] = None
    programming: Optional[float] = None
    database: Optional[float] = None
    gpa: Optional[float] = None
    user_id: str


class StudentListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    students: list[StudentOut]
